import os
import mercadopago
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/pagos", tags=["pagos"])

# Configuramos el SDK con nuestro Access Token
# Se puede usar una variable de entorno en producción (os.getenv("MP_ACCESS_TOKEN"))
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN", "TEST-7254881140306354-100220-db98eb7b8434771cbbfd2e68c683b5f4-123456789")
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
async def mercadopago_webhook(data: dict):
    """
    Webhook para recibir las notificaciones de pagos exitosos de Mercado Pago.
    Aquí activarías el plan PRO de la empresa en la base de datos.
    """
    # 1. Obtener el id del pago y buscarlo en la API de Mercado Pago
    # 2. Si el status == 'approved', leer el external_reference (empresa_id)
    # 3. Actualizar la base de datos para darle a la empresa beneficios PRO
    print(f"Webhook recibido: {data}")
    return {"status": "ok"}
