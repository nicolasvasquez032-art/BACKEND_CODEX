from fastapi import FastAPI

from infrastructure.api.routers import auth_router, health_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="TalentMatch Backend",
        version="0.1.0",
        description="Transactional API for TalentMatch.",
    )
    app.include_router(health_router)
    app.include_router(auth_router)
    return app

