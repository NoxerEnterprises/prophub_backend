from fastapi import APIRouter

from app.db.session import check_database_connection
from app.schemas.response import success_response

router = APIRouter()


@router.get("/health")
def health_check():
    db_status = check_database_connection()
    app_ok = True
    db_ok = db_status.get("ok", False)

    return success_response(
        message="Health check completed.",
        data={
            "app": "ok" if app_ok else "error",
            "database": "ok" if db_ok else "not_configured_or_unavailable",
            "database_details": db_status,
        },
    )
