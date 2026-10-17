from fastapi import Request
from slowapi import Limiter


def get_real_client_ip(request: Request) -> str:
    """Extrae la IP real del cliente, considerando proxies y balanceadores (AWS / Nginx)."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    if request.client and request.client.host:
        return request.client.host

    return "127.0.0.1"


from infrastructure.config import settings

# Factor VI (Processes - Stateless): Soporta almacenamiento compartido (Redis)
# si REDIS_URL está presente, permitiendo múltiples réplicas del backend sin compartir memoria local.
_storage_uri = settings.redis_url if settings.redis_url else "memory://"
limiter = Limiter(key_func=get_real_client_ip, storage_uri=_storage_uri)
