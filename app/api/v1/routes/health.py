from fastapi import APIRouter

from app.db.session import check_database_connection
from app.schemas.common import APIResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=APIResponse[dict])
async def health_check() -> APIResponse[dict]:
    return APIResponse(message="API is running", data={"status": "ok"})


@router.get("/status", response_model=APIResponse[dict])
async def api_status() -> APIResponse[dict]:
    database_ok = await check_database_connection()
    return APIResponse(message="Service status", data={"api": "ok", "database": "ok" if database_ok else "down"})
