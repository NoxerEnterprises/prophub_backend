from fastapi import APIRouter, Request, status

from app.api.dependencies import CurrentUserDep, SessionDep
from app.schemas.auth import AuthResponse, EmailVerificationRequest, EmailVerificationResponse, LogoutRequest, MeResponse, PasswordResetConfirmRequest, PasswordResetRequest, PasswordResetRequestResponse, PasswordResetVerifyRequest, PasswordResetVerifyResponse, RefreshTokenRequest, ResendEmailVerificationRequest, ResendEmailVerificationResponse, TokenPair
from app.schemas.common import APIResponse
from app.schemas.user import LoginRequest, RegisterRequest, UserPublic
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=APIResponse[AuthResponse])
async def register(payload: RegisterRequest, request: Request, session: SessionDep) -> APIResponse[AuthResponse]:
    data = await AuthService(session).register(payload, ip=_client_ip(request), user_agent=request.headers.get("user-agent"))
    return APIResponse(message="Registration successful. Please verify your email.", data=data)


@router.post("/verify-email", response_model=APIResponse[EmailVerificationResponse])
async def verify_email(payload: EmailVerificationRequest, request: Request, session: SessionDep) -> APIResponse[EmailVerificationResponse]:
    user, tokens = await AuthService(session).verify_email(email=str(payload.email), verification_token=payload.verification_token, otp_code=payload.otp_code, ip=_client_ip(request), user_agent=request.headers.get("user-agent"))
    return APIResponse(message="Email verified successfully", data=EmailVerificationResponse(verified=True, user=UserPublic.model_validate(user), tokens=tokens))


@router.post("/resend-verification", response_model=APIResponse[ResendEmailVerificationResponse])
async def resend_verification(payload: ResendEmailVerificationRequest, request: Request, session: SessionDep) -> APIResponse[ResendEmailVerificationResponse]:
    data = await AuthService(session).resend_email_verification(email=str(payload.email), ip=_client_ip(request))
    return APIResponse(message="Verification email processed", data=data)


@router.post("/login", response_model=APIResponse[AuthResponse])
async def login(payload: LoginRequest, request: Request, session: SessionDep) -> APIResponse[AuthResponse]:
    data = await AuthService(session).login(payload.email, payload.password, ip=_client_ip(request), user_agent=request.headers.get("user-agent"))
    message = "Email verification required" if data.email_verification_required else "Login successful"
    return APIResponse(message=message, data=data)


@router.post("/refresh", response_model=APIResponse[TokenPair])
async def refresh_token(payload: RefreshTokenRequest, request: Request, session: SessionDep) -> APIResponse[TokenPair]:
    data = await AuthService(session).refresh(payload.refresh_token, ip=_client_ip(request), user_agent=request.headers.get("user-agent"))
    return APIResponse(message="Token refreshed", data=data)


@router.post("/logout", response_model=APIResponse[dict])
async def logout(payload: LogoutRequest, session: SessionDep) -> APIResponse[dict]:
    await AuthService(session).logout(payload.refresh_token)
    return APIResponse(message="Logout successful", data={"logged_out": True})


@router.get("/me", response_model=APIResponse[MeResponse])
async def me(current_user: CurrentUserDep) -> APIResponse[MeResponse]:
    agent = current_user.agent_profile
    data = MeResponse.model_validate({**current_user.__dict__, "agent_status": agent.status if agent else None, "agent_operating_mode": agent.operating_mode if agent else None, "subscription_status": agent.subscription_status if agent else None, "subscription_expires_at": agent.subscription_expires_at if agent else None, "email_verification_required": not current_user.is_email_verified, "is_super_admin": bool(current_user.admin_profile and current_user.admin_profile.is_super_admin)})
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
