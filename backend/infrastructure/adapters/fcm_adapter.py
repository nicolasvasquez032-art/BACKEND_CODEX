import logging
import os
import firebase_admin
from firebase_admin import credentials, messaging

from application.ports.notificacion_ports import PushNotificationPort

logger = logging.getLogger(__name__)

# Intentar inicializar Firebase Admin SDK vía variable de entorno (Factor III) o archivo local.
try:
    if not firebase_admin._apps:
        import json
        creds_env = os.environ.get("FIREBASE_CREDENTIALS_JSON")
        if creds_env:
            cred_dict = json.loads(creds_env)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            logger.info("[FCM] Firebase Admin SDK inicializado desde variable de entorno (Factor III).")
        else:
            firebase_cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "firebase-adminsdk.json")
            if os.path.exists(firebase_cred_path):
                cred = credentials.Certificate(firebase_cred_path)
                firebase_admin.initialize_app(cred)
                logger.info("[FCM] Firebase Admin SDK inicializado desde archivo local.")
            else:
                logger.warning("[FCM] Advertencia: No se detectaron credenciales de Firebase. Notificaciones push simuladas.")
except Exception as e:
    logger.warning(f"[FCM] Advertencia: No se pudo inicializar Firebase Admin SDK ({e}). Las notificaciones fallarán.")

class RealFcmAdapter(PushNotificationPort):
    async def send_notification(self, token: str, title: str, body: str, data: dict[str, str] | None = None) -> bool:
        """
        Real implementation of PushNotificationPort.
        Calls Firebase Cloud Messaging to send the notification to the device.
        """
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data or {},
                token=token,
            )
            response = messaging.send(message)
            logger.info(f"[FCM] Mensaje enviado a {token}. Response: {response}")
            return True
        except Exception as e:
            logger.error(f"[FCM ERROR] Fallo al enviar push notification a {token}: {e}")
            return False
