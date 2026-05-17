from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.v1.dependencies.auth import get_current_user, require_admin, require_agent, require_super_admin
from app.models.user import User
from app.schemas.response import success_response

router = APIRouter(prefix="/debug/roles", tags=["Debug - Role Guards"])


@router.get("/protected")
def protected_route(current_user: User = Depends(get_current_user)):
    return success_response(
        message="Authenticated access granted.",
        data={"user_id": str(current_user.id), "role": current_user.role.value},
    )


@router.get("/agent")
def agent_only(current_user: User = Depends(require_agent)):
    return success_response(
        message="Agent access granted.",
        data={"user_id": str(current_user.id), "role": current_user.role.value},
    )


@router.get("/admin")
def admin_only(current_user: User = Depends(require_admin)):
    return success_response(
        message="Admin access granted.",
        data={"user_id": str(current_user.id), "role": current_user.role.value},
    )


@router.get("/super-admin")
def super_admin_only(current_user: User = Depends(require_super_admin)):
    return success_response(
        message="Super admin access granted.",
        data={"user_id": str(current_user.id), "role": current_user.role.value},
    )
