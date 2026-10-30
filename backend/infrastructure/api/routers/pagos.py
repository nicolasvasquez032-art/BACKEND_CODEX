import hashlib
import hmac
from uuid import UUID

import mercadopago
from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.adapters.persistence.database import get_session
from infrastructure.adapters.persistence.user_repository import SqlAlchemyUserRepository
from infrastructure.config import settings

router = APIRouter(prefix="/pagos", tags=["pagos"])


def verify_mp_signature(
    x_signature: str | None,
    x_request_id: str | None,
    data_id: str | None,
    secret: str,
) -> bool:
    """Valida la firma criptográfica HMAC-SHA256 del webhook de Mercado Pago (OWASP Top 10 - Integridad)."""
    if not secret:
        return True
    if not x_signature or not data_id:
        return False

    try:
        parts: dict[str, str] = {}
        for item in x_signature.split(","):
            if "=" in item:
                k, v = item.strip().split("=", 1)
                parts[k] = v
        ts = parts.get("ts")
        v1 = parts.get("v1")
        if not ts or not v1:
            return False

        manifest = f"id:{data_id};request-id:{x_request_id or ''};ts:{ts};"
        expected = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(v1, expected)
    except Exception as e:
        logger.error(f"Error verificando firma de webhook MP: {e}")
        return False


def _get_mp_sdk() -> mercadopago.SDK:
    """Devuelve el SDK de Mercado Pago configurado con el token de entorno.

    Lanza un error claro si MP_ACCESS_TOKEN no está configurado,
    en lugar de usar un valor hardcodeado inseguro.
    """
    if not settings.mp_access_token:
        raise HTTPException(
            status_code=503,
            detail="El servicio de pagos no está configurado. Contacta al administrador.",
        )
    return mercadopago.SDK(settings.mp_access_token)


class PlanProRequest(BaseModel):
    empresa_id: str
    email: str


@router.post("/crear-preferencia-pro")
async def crear_preferencia_pro(request: PlanProRequest):
    """Crea una preferencia de pago en Mercado Pago para la suscripción PRO.

    Retorna el init_point (URL) a la que el Frontend redirigirá al usuario.
    """
    sdk = _get_mp_sdk()

    base_url = settings.mp_back_url_base.rstrip("/")
    preference_data = {
        "items": [
            {
                "title": "Suscripción TalentMatch PRO (1 mes)",
                "quantity": 1,
                "unit_price": 49.00,
                "currency_id": "USD",
            }
        ],
        "payer": {
            "email": request.email,
        },
        "back_urls": {
            "success": f"{base_url}/pagos/success",
            "failure": f"{base_url}/pagos/failure",
            "pending": f"{base_url}/pagos/pending",
        },
        "auto_return": "approved",
        "external_reference": request.empresa_id,  # Identificador de la empresa que paga
    }

    try:
        preference_response = sdk.preference().create(preference_data)
        preference = preference_response["response"]

        return {
            "id": preference["id"],
            "init_point": preference["init_point"],  # URL de pago para redirigir
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al crear la preferencia de pago: {e!s}"
        )


@router.post("/webhook")
async def mercadopago_webhook(
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    """Webhook para recibir las notificaciones de pagos exitosos de Mercado Pago.

    Valida firma criptográfica HMAC-SHA256 (x-signature) para evitar suplantaciones.
    Mercado Pago reintenta si no recibe 200 OK, por eso retornamos 200 tras procesar.
    """
    try:
        data = await request.json()
        logger.info(f"Webhook recibido: {data}")

        action = data.get("action")
        type_ = data.get("type")

        if action == "payment.created" or type_ == "payment":
            raw_payment_id = data.get("data", {}).get("id") or request.query_params.get("data.id")
            payment_id = str(raw_payment_id) if raw_payment_id else None

            # Validación de firma x-signature si el secret está configurado
            if settings.mp_webhook_secret and payment_id:
                x_signature = request.headers.get("x-signature")
                x_request_id = request.headers.get("x-request-id")
                is_valid = verify_mp_signature(
                    x_signature=x_signature,
                    x_request_id=x_request_id,
                    data_id=payment_id,
                    secret=settings.mp_webhook_secret,
                )
                if not is_valid:
                    logger.warning(f"Firma de webhook Mercado Pago inválida para payment_id: {payment_id}")
                    return {"status": "ignored", "reason": "invalid_signature"}

            if payment_id:
                sdk = _get_mp_sdk()
                payment_info = sdk.payment().get(payment_id)
                payment = payment_info.get("response", {})

                if payment.get("status") == "approved":
                    empresa_id_str = payment.get("external_reference")
                    if empresa_id_str:
                        empresa_id = UUID(empresa_id_str)
                        user_repo = SqlAlchemyUserRepository(db)
                        await user_repo.mark_user_as_premium(empresa_id)
                        await db.commit()
                        logger.info(f"¡Éxito! Empresa {empresa_id} marcada como PRO.")

    except HTTPException:
        pass  # Token no configurado — no procesar
    except Exception as e:
        logger.error(f"Error procesando webhook de Mercado Pago: {e}")

    # Siempre devolver 200 OK para que MP no reintente
    return {"status": "ok"}
