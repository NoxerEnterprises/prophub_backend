from fastapi import APIRouter

from app.core.config import settings
from app.schemas.response import success_response

router = APIRouter()


@router.get("/status")
def api_status():
    return success_response(
        message="API status retrieved.",
        data={
            "service": settings.PROJECT_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "api_prefix": settings.API_V1_PREFIX,
        },
    )
