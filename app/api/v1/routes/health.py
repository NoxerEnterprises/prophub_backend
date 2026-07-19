from fastapi import APIRouter

from app.core.config import settings
from app.db.session import check_database_connection
from app.schemas.common import APIResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=APIResponse[dict])
async def health_check() -> APIResponse[dict]:
    database_ok = False
    details = None
    try:
        database_ok = await check_database_connection()
    except Exception as exc:
        details = repr(exc) if settings.DEBUG else None
    return APIResponse(message="API is running", data={"status": "ok", "database": "ok" if database_ok else "down", "database_details": details})


@router.get("/status", response_model=APIResponse[dict])
async def api_status() -> APIResponse[dict]:
    database_ok = False
    details = None
    try:
        database_ok = await check_database_connection()
    except Exception as exc:
        details = repr(exc) if settings.DEBUG else None
    return APIResponse(message="Service status", data={"api": "ok", "version": settings.APP_VERSION, "database": "ok" if database_ok else "down", "database_details": details})
