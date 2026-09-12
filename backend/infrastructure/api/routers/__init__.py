from infrastructure.api.routers.auth import router as auth_router
from infrastructure.api.routers.health import router as health_router
from infrastructure.api.routers.postulaciones import router as postulaciones_router
from infrastructure.api.routers.profiles import router as profiles_router
from infrastructure.api.routers.vacantes import router as vacantes_router

__all__ = ["auth_router", "health_router", "postulaciones_router", "profiles_router", "vacantes_router"]

