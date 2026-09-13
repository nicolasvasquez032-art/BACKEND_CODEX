from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from infrastructure.api.routers import (
    auth_router,
    health_router,
    notificaciones_router,
    postulaciones_router,
    profiles_router,
    recomendaciones_router,
    vacantes_router,
    admin_router,
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="TalentMatch Backend",
        version="0.2.0",
        description="Transactional API for TalentMatch — Sprint 2.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
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
    app.include_router(admin_router)
    return app
