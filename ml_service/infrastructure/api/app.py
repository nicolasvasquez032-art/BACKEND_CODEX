from fastapi import FastAPI

from infrastructure.api.routers import embedding_router, health_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="TalentMatch ML Service",
        version="0.1.0",
        description="Internal service for embeddings and recommendations.",
    )
    app.include_router(health_router)
    app.include_router(embedding_router)
    return app

