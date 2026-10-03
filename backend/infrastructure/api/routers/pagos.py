import os
import mercadopago
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from infrastructure.api.dependencies import get_db_session
from infrastructure.adapters.persistence.user_repository import SqlAlchemyUserRepository

router = APIRouter(prefix="/pagos", tags=["pagos"])

# Configuramos el SDK con nuestro Access Token
# Se puede usar una variable de entorno en producción (os.getenv("MP_ACCESS_TOKEN"))
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN", "APP_USR-2359765611894441-100221-3aaf4343fb9546c1ce1dcb0716f0a166-3735144816")
sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

class PlanProRequest(BaseModel):
    empresa_id: str
    email: str

@router.post("/crear-preferencia-pro")
async def crear_preferencia_pro(request: PlanProRequest):
    """
    Crea una preferencia de pago en Mercado Pago para la suscripción PRO.
    Retorna el init_point (URL) a la que el Frontend redirigirá al usuario.
    """
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
            "success": "https://miproyecto.com/success",
            "failure": "https://miproyecto.com/failure",
            "pending": "https://miproyecto.com/pending"
        },
        "auto_return": "approved",
        "external_reference": request.empresa_id # Identificador de la empresa que paga
    }

    try:
        preference_response = sdk.preference().create(preference_data)
        preference = preference_response["response"]
        
        return {
            "id": preference["id"],
            "init_point": preference["init_point"] # Url de pago para redirigir
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al crear la preferencia de pago: {str(e)}")

@router.post("/webhook")
async def mercadopago_webhook(request: Request, db: AsyncSession = Depends(get_db_session)):
    """
    Webhook para recibir las notificaciones de pagos exitosos de Mercado Pago.
    Aquí activarías el plan PRO de la empresa en la base de datos.
    """
    try:
        data = await request.json()
        print(f"Webhook recibido: {data}")
        
        # Mercado Pago envía notificaciones de distintos tipos. Nos interesa payment.
        action = data.get("action")
        type_ = data.get("type")
        
        if action == "payment.created" or type_ == "payment":
            # El ID del pago puede venir en data['data']['id']
            payment_id = data.get("data", {}).get("id")
            
            if payment_id:
                payment_info = sdk.payment().get(payment_id)
                payment = payment_info.get("response", {})
                
                if payment.get("status") == "approved":
                    empresa_id_str = payment.get("external_reference")
                    if empresa_id_str:
                        empresa_id = UUID(empresa_id_str)
                        user_repo = SqlAlchemyUserRepository(db)
                        
                        await user_repo.mark_user_as_premium(empresa_id)
                        await db.commit()
                        print(f"¡Éxito! Empresa {empresa_id} marcada como PRO.")
    except Exception as e:
        print(f"Error procesando webhook de Mercado Pago: {e}")

    # Siempre devolver 200 OK para que MP no reintente
    return {"status": "ok"}
