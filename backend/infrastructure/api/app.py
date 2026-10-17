from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from slowapi.errors import RateLimitExceeded

from application.services.i18n_service import I18nService
from infrastructure.adapters.persistence.database import engine

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manejo de ciclo de vida de la aplicación.
    
    Factor IX (Disposability): Asegura inicio rápido y apagado elegante (graceful shutdown)
    liberando pools de conexión a la base de datos ante señales SIGTERM/SIGINT.
    """
    logger.info("TalentMatch API inicializada correctamente.")
    yield
    logger.info("Cerrando pools de conexiones y liberando recursos (Graceful Shutdown)...")
    await engine.dispose()
    try:
        from infrastructure.adapters.cache.redis_cache_service import RedisCacheService
        await RedisCacheService.get_instance().close()
    except Exception:
        pass


def create_app() -> FastAPI:
    setup_logging()

    # Inicialización de Sentry para Monitoreo y Reporte de Errores en Producción
    if settings.sentry_dsn:
        try:
            import sentry_sdk
            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                environment=settings.sentry_environment,
                traces_sample_rate=settings.sentry_traces_sample_rate,
                send_default_pii=False,
            )
            logger.info(
                f"Sentry SDK inicializado exitosamente en entorno: {settings.sentry_environment}"
            )
        except Exception as e:
            logger.error(f"Error al inicializar Sentry SDK: {e}")

    is_prod = settings.environment.lower() == "production"
    app = FastAPI(
        title="TalentMatch Backend",
        version="0.2.0",
        description="Transactional API for TalentMatch — Sprint 2.",
        docs_url=None if is_prod else "/docs",
        redoc_url=None if is_prod else "/redoc",
        openapi_url=None if is_prod else "/openapi.json",
        lifespan=lifespan,
    )
    
    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        client_ip = request.headers.get("x-forwarded-for") or (
            request.client.host if request.client else "desconocida"
        )
        logger.warning(
            f"Rate limit excedido en {request.method} {request.url.path} desde IP: {client_ip} - Límite: {exc.detail}"
        )
        lang = request.headers.get("accept-language")
        detail = "Demasiados intentos. Por favor, espera un momento antes de reintentar."
        detail = I18nService.translate_error(detail, lang=lang)
        response = JSONResponse(
            status_code=429,
            content={
                "detail": detail,
                "error": f"Rate limit exceeded: {exc.detail}",
            },
        )
        limiter_instance = getattr(request.app.state, "limiter", None)
        view_rate_limit = getattr(request.state, "view_rate_limit", None)
        if limiter_instance and view_rate_limit:
            response = limiter_instance._inject_headers(response, view_rate_limit)
        return response
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        lang = request.headers.get("accept-language")
        detail = exc.detail
        if isinstance(detail, str):
            detail = I18nService.translate_error(detail, lang=lang)
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": detail},
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(f"Excepción no controlada en {request.method} {request.url.path}")
        if settings.sentry_dsn:
            try:
                import sentry_sdk
                sentry_sdk.capture_exception(exc)
            except Exception:
                pass
        lang = request.headers.get("accept-language")
        detail = "Ha ocurrido un error interno en el servidor. El equipo técnico ha sido notificado."
        detail = I18nService.translate_error(detail, lang=lang)
        return JSONResponse(
            status_code=500,
            content={"detail": detail},
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
