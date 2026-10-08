from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from infrastructure.api.routers import (
    admin_router,
    auth_router,
    chat_router,
    health_router,
    notificaciones_router,
    pagos_router,
    postulaciones_router,
    profiles_router,
    recomendaciones_router,
    vacantes_router,
)
from infrastructure.api.rate_limiter import limiter
from infrastructure.config import settings
from infrastructure.logger import setup_logging


def create_app() -> FastAPI:
    setup_logging()
    is_prod = settings.environment.lower() == "production"
    app = FastAPI(
        title="TalentMatch Backend",
        version="0.2.0",
        description="Transactional API for TalentMatch — Sprint 2.",
        docs_url=None if is_prod else "/docs",
        redoc_url=None if is_prod else "/redoc",
        openapi_url=None if is_prod else "/openapi.json",
    )
    
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(f"Excepción no controlada en {request.method} {request.url.path}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Ha ocurrido un error interno en el servidor. El equipo técnico ha sido notificado."},
        )
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(profiles_router)
    app.include_router(vacantes_router)
    app.include_router(postulaciones_router)
    app.include_router(recomendaciones_router)
    app.include_router(notificaciones_router)
    app.include_router(pagos_router)
    app.include_router(admin_router)
    app.include_router(chat_router)
    return app
