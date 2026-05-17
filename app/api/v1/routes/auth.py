from fastapi import APIRouter, Request, status

from app.api.dependencies import CurrentUserDep, SessionDep
from app.schemas.auth import (
    AuthResponse,
    LogoutRequest,
    MeResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    PasswordResetRequestResponse,
    PasswordResetVerifyRequest,
    PasswordResetVerifyResponse,
    RefreshTokenRequest,
    TokenPair,
)
from app.schemas.common import APIResponse
from app.schemas.user import LoginRequest, RegisterRequest
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=APIResponse[AuthResponse])
async def register(payload: RegisterRequest, request: Request, session: SessionDep) -> APIResponse[AuthResponse]:
    data = await AuthService(session).register(
        payload,
        ip=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return APIResponse(message="Registration successful", data=data)


@router.post("/login", response_model=APIResponse[AuthResponse])
async def login(payload: LoginRequest, request: Request, session: SessionDep) -> APIResponse[AuthResponse]:
    data = await AuthService(session).login(
        payload.email,
        payload.password,
        ip=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return APIResponse(message="Login successful", data=data)


@router.post("/refresh", response_model=APIResponse[TokenPair])
async def refresh_token(payload: RefreshTokenRequest, request: Request, session: SessionDep) -> APIResponse[TokenPair]:
    data = await AuthService(session).refresh(
        payload.refresh_token,
        ip=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return APIResponse(message="Token refreshed", data=data)


@router.post("/logout", response_model=APIResponse[dict])
async def logout(payload: LogoutRequest, session: SessionDep) -> APIResponse[dict]:
    await AuthService(session).logout(payload.refresh_token)
    return APIResponse(message="Logout successful", data={"logged_out": True})


@router.get("/me", response_model=APIResponse[MeResponse])
async def me(current_user: CurrentUserDep) -> APIResponse[MeResponse]:
    data = MeResponse.model_validate(
        {
            **current_user.__dict__,
            "agent_status": current_user.agent_profile.status if current_user.agent_profile else None,
            "is_super_admin": bool(current_user.admin_profile and current_user.admin_profile.is_super_admin),
        }
    )
    return APIResponse(message="Current user", data=data)


@router.post("/request-reset", response_model=APIResponse[PasswordResetRequestResponse])
async def request_password_reset(payload: PasswordResetRequest, request: Request, session: SessionDep) -> APIResponse[PasswordResetRequestResponse]:
    data = await AuthService(session).request_password_reset(payload.email, ip=_client_ip(request))
    return APIResponse(message="Password reset requested", data=data)


@router.post("/verify-reset", response_model=APIResponse[PasswordResetVerifyResponse])
async def verify_password_reset(payload: PasswordResetVerifyRequest, session: SessionDep) -> APIResponse[PasswordResetVerifyResponse]:
    valid = await AuthService(session).verify_password_reset(payload.reset_token, payload.otp_code)
    return APIResponse(message="Reset token verified", data=PasswordResetVerifyResponse(valid=valid))


@router.post("/reset-password", response_model=APIResponse[dict])
async def reset_password(payload: PasswordResetConfirmRequest, session: SessionDep) -> APIResponse[dict]:
    await AuthService(session).reset_password(payload.reset_token, payload.otp_code, payload.new_password)
    return APIResponse(message="Password reset successful", data={"reset": True})


