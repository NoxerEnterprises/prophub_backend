from fastapi import FastAPI

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.cors import setup_cors
from app.core.exception_handlers import register_exception_handlers
from app.schemas.response import success_response


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    )

    setup_cors(app)
    register_exception_handlers(app)

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/", tags=["Root"])
    def root():
        return success_response(
            message="Property Backend API is running.",
            data={
                "project": settings.PROJECT_NAME,
                "version": settings.APP_VERSION,
                "environment": settings.ENVIRONMENT,
                "docs": "/docs",
                "api_prefix": settings.API_V1_PREFIX,
            },
        )

    @app.get("/health", tags=["Health"])
    def root_health():
        return success_response(
            message="Application health check passed.",
            data={
                "app": "ok",
                "environment": settings.ENVIRONMENT,
            },
        )

    return app


app = create_app()
