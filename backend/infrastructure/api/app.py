from fastapi import FastAPI

from infrastructure.api.routers import (
    auth_router,
    health_router,
    postulaciones_router,
    profiles_router,
    vacantes_router,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="TalentMatch Backend",
        version="0.2.0",
        description="Transactional API for TalentMatch — Sprint 2.",
    )
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(profiles_router)
    app.include_router(vacantes_router)
    app.include_router(postulaciones_router)
    return app
