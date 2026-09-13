import logging

from application.ports.notificacion_ports import PushNotificationPort

logger = logging.getLogger(__name__)


class MockFcmAdapter(PushNotificationPort):
    async def send_notification(self, token: str, title: str, body: str, data: dict[str, str] | None = None) -> bool:
        """
        Mock implementation of PushNotificationPort.
        Instead of calling Firebase, it prints to the log.
        """
        logger.info(f"[FCM MOCK] Sending push notification to token {token}")
        logger.info(f"   Title: {title}")
        logger.info(f"   Body: {body}")
        if data:
            logger.info(f"   Data: {data}")
            
        return True
