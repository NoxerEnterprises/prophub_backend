from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums import AgentStatus, TokenType, UserRole, UserType
from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, UnauthorizedError
from app.core.security import create_jwt_token, decode_jwt_token, generate_numeric_otp, generate_opaque_token_urlsafe, hash_password, now_utc, password_needs_rehash, sha256_hash, verify_password
from app.models.email_verification_token import EmailVerificationToken
from app.models.password_reset_token import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.email_verification_repository import EmailVerificationRepository
from app.repositories.token_repository import TokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AuthResponse, PasswordResetRequestResponse, ResendEmailVerificationResponse, TokenPair
from app.schemas.user import RegisterRequest, UserPublic
from app.services.email_service import EmailService


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.tokens = TokenRepository(session)
        self.email_tokens = EmailVerificationRepository(session)

    async def register(self, payload: RegisterRequest, *, ip: str | None = None, user_agent: str | None = None) -> AuthResponse:
        if await self.users.get_by_email(payload.email):
            raise ConflictError("Email is already registered")
        if payload.phone and await self.users.get_by_phone(payload.phone):
            raise ConflictError("Phone number is already registered")
        user = User(
            email=payload.email,
            phone=payload.phone,
            full_name=payload.full_name.strip(),
            hashed_password=hash_password(payload.password),
            role=UserRole.USER.value,
            user_type=UserType.CUSTOMER.value,
            is_active=True,
            is_email_verified=False,
        )
        await self.users.add(user)
        verification_token, otp_code = await self._create_email_verification(user=user, ip=ip)
        await self.session.commit()
        await self.session.refresh(user)
        await EmailService().send_email_verification(to_email=user.email, full_name=user.full_name, otp_code=otp_code, verification_token=verification_token)
        return AuthResponse(
            user=UserPublic.model_validate(user),
            tokens=None,
            email_verification_required=True,
            is_email_verified=False,
            debug_verification_token=verification_token if settings.ENVIRONMENT != "production" else None,
            debug_otp_code=otp_code if settings.ENVIRONMENT != "production" else None,
        )

    async def login(self, email: str, password: str, *, ip: str | None = None, user_agent: str | None = None) -> AuthResponse:
        user = await self.users.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Invalid email or password")
        if not user.is_active:
            raise ForbiddenError("This account is inactive")
        if user.role == UserRole.AGENT.value and user.agent_profile and user.agent_profile.status == AgentStatus.DISABLED.value:
            raise ForbiddenError("This agent account is disabled")
        if not user.is_email_verified:
            latest = await self.email_tokens.get_latest_active_for_user(user.id)
            debug_token = None
            if not latest:
                verification_token, otp_code = await self._create_email_verification(user=user, ip=ip)
                await self.session.commit()
                await EmailService().send_email_verification(to_email=user.email, full_name=user.full_name, otp_code=otp_code, verification_token=verification_token)
                debug_token = verification_token
                debug_otp = otp_code
            else:
                debug_otp = None
            return AuthResponse(
                user=UserPublic.model_validate(user),
                tokens=None,
                email_verification_required=True,
                is_email_verified=False,
                debug_verification_token=debug_token if settings.ENVIRONMENT != "production" else None,
                debug_otp_code=debug_otp if settings.ENVIRONMENT != "production" else None,
            )
        if password_needs_rehash(user.hashed_password):
            user.hashed_password = hash_password(password)
        user.last_login_at = now_utc()
        token_pair = await self._issue_token_pair(user, ip=ip, user_agent=user_agent)
        await self.session.commit()
        await self.session.refresh(user)
        return AuthResponse(user=UserPublic.model_validate(user), tokens=token_pair, email_verification_required=False, is_email_verified=True)

    async def verify_email(self, *, email: str, verification_token: str | None, otp_code: str, ip: str | None = None, user_agent: str | None = None):
        user = await self.users.get_by_email(email)
        if not user:
            raise BadRequestError("Invalid verification request")
        if user.is_email_verified:
            token_pair = await self._issue_token_pair(user, ip=ip, user_agent=user_agent)
            await self.session.commit()
            return user, token_pair
        record = None
        if verification_token:
            record = await self.email_tokens.get_active_by_token_hash(sha256_hash(verification_token))
        if not record:
            record = await self.email_tokens.get_latest_active_for_user(user.id)
        if not record or record.user_id != user.id:
            raise BadRequestError("Invalid or expired verification token")
        if record.attempt_count >= record.max_attempts:
            raise BadRequestError("Verification attempt limit exceeded")
        record.attempt_count += 1
        if record.otp_hash != sha256_hash(otp_code):
            await self.session.commit()
            raise BadRequestError("Invalid verification code")
        record.used_at = now_utc()
        user.is_email_verified = True
        user.email_verified_at = now_utc()
        user.last_login_at = now_utc()
        token_pair = await self._issue_token_pair(user, ip=ip, user_agent=user_agent)
        await self.session.commit()
        await self.session.refresh(user)
        return user, token_pair

    async def resend_email_verification(self, *, email: str, ip: str | None = None) -> ResendEmailVerificationResponse:
        user = await self.users.get_by_email(email)
        if not user:
            return ResendEmailVerificationResponse(email=email, email_verification_required=True)
        if user.is_email_verified:
            return ResendEmailVerificationResponse(email=user.email, email_verification_required=False)
        verification_token, otp_code = await self._create_email_verification(user=user, ip=ip)
        await self.session.commit()
        await EmailService().send_email_verification(to_email=user.email, full_name=user.full_name, otp_code=otp_code, verification_token=verification_token)
        return ResendEmailVerificationResponse(
            email=user.email,
            email_verification_required=True,
            debug_verification_token=verification_token if settings.ENVIRONMENT != "production" else None,
            debug_otp_code=otp_code if settings.ENVIRONMENT != "production" else None,
        )

    async def refresh(self, refresh_token: str, *, ip: str | None = None, user_agent: str | None = None) -> TokenPair:
        try:
            payload = decode_jwt_token(refresh_token, expected_type=TokenType.REFRESH)
        except ValueError as exc:
            raise UnauthorizedError(str(exc)) from exc
        user_id = uuid.UUID(str(payload.get("sub")))
        jti = str(payload.get("jti"))
        stored_token = await self.tokens.get_active_refresh_token(sha256_hash(refresh_token), jti)
        if not stored_token:
            raise UnauthorizedError("Refresh token is invalid, expired, or revoked")
        user = await self.users.get_by_id(user_id)
        if not user or not user.is_active:
            raise UnauthorizedError("User not found or inactive")
        if not user.is_email_verified:
            raise ForbiddenError("Email verification required")
        new_pair = await self._issue_token_pair(user, ip=ip, user_agent=user_agent)
        new_token_record = await self.tokens.get_active_refresh_token(sha256_hash(new_pair.refresh_token), self._decode_jti(new_pair.refresh_token))
        await self.tokens.revoke_refresh_token(stored_token, replaced_by_token_id=new_token_record.id if new_token_record else None)
        await self.session.commit()
        return new_pair

    async def logout(self, refresh_token: str) -> None:
        try:
            payload = decode_jwt_token(refresh_token, expected_type=TokenType.REFRESH)
        except ValueError:
            return
        stored_token = await self.tokens.get_active_refresh_token(sha256_hash(refresh_token), str(payload.get("jti")))
        if stored_token:
            await self.tokens.revoke_refresh_token(stored_token)
            await self.session.commit()

    async def request_password_reset(self, email: str, *, ip: str | None = None) -> PasswordResetRequestResponse:
        user = await self.users.get_by_email(email)
        neutral = "If this email exists, password reset instructions have been generated."
        if not user:
            return PasswordResetRequestResponse(message=neutral)
        reset_token = generate_opaque_token_urlsafe()
        otp_code = generate_numeric_otp(settings.PASSWORD_RESET_OTP_LENGTH)
        expires_at = now_utc() + timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES)
        await self.tokens.mark_all_user_reset_tokens_used(user.id)
        await self.tokens.add_password_reset_token(PasswordResetToken(user_id=user.id, token_hash=sha256_hash(reset_token), otp_hash=sha256_hash(otp_code), expires_at=expires_at, created_at=now_utc(), requested_ip=ip))
        await self.session.commit()
        return PasswordResetRequestResponse(message=neutral, debug_reset_token=reset_token if settings.ENVIRONMENT != "production" else None, debug_otp_code=otp_code if settings.ENVIRONMENT != "production" else None)

    async def verify_password_reset(self, reset_token: str, otp_code: str) -> bool:
        record = await self.tokens.get_active_password_reset_token(sha256_hash(reset_token))
        if not record:
            raise BadRequestError("Invalid or expired reset token")
        if record.attempt_count >= record.max_attempts:
            raise BadRequestError("Reset token attempt limit exceeded")
        record.attempt_count += 1
        valid = record.otp_hash == sha256_hash(otp_code)
        await self.session.commit()
        if not valid:
            raise BadRequestError("Invalid reset OTP code")
        return True

    async def reset_password(self, reset_token: str, otp_code: str, new_password: str) -> None:
        record = await self.tokens.get_active_password_reset_token(sha256_hash(reset_token))
        if not record:
            raise BadRequestError("Invalid or expired reset token")
        if record.attempt_count >= record.max_attempts:
            raise BadRequestError("Reset token attempt limit exceeded")
        record.attempt_count += 1
        if record.otp_hash != sha256_hash(otp_code):
            await self.session.commit()
            raise BadRequestError("Invalid reset OTP code")
        user = await self.users.get_by_id(record.user_id)
        if not user:
            raise BadRequestError("User account no longer exists")
        user.hashed_password = hash_password(new_password)
        await self.tokens.mark_reset_token_used(record)
        await self.tokens.revoke_all_user_refresh_tokens(user.id)
        await self.session.commit()

    async def _create_email_verification(self, *, user: User, ip: str | None) -> tuple[str, str]:
        verification_token = generate_opaque_token_urlsafe()
        otp_code = generate_numeric_otp(settings.EMAIL_VERIFICATION_OTP_LENGTH)
        await self.email_tokens.mark_all_user_tokens_used(user.id)
        record = EmailVerificationToken(user_id=user.id, token_hash=sha256_hash(verification_token), otp_hash=sha256_hash(otp_code), expires_at=now_utc() + timedelta(minutes=settings.EMAIL_VERIFICATION_EXPIRE_MINUTES), created_at=now_utc(), requested_ip=ip)
        await self.email_tokens.add(record)
        return verification_token, otp_code

    async def _issue_token_pair(self, user: User, *, ip: str | None = None, user_agent: str | None = None) -> TokenPair:
        access_token, _access_jti, access_expires_at = create_jwt_token(subject=str(user.id), token_type=TokenType.ACCESS, role=user.role, expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
        refresh_token, refresh_jti, refresh_expires_at = create_jwt_token(subject=str(user.id), token_type=TokenType.REFRESH, expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))
        await self.tokens.add_refresh_token(RefreshToken(user_id=user.id, token_hash=sha256_hash(refresh_token), jti=refresh_jti, expires_at=refresh_expires_at, created_at=now_utc(), created_by_ip=ip, user_agent=user_agent))
        return TokenPair(access_token=access_token, refresh_token=refresh_token, expires_at=access_expires_at)

    def _decode_jti(self, token: str) -> str:
        payload = decode_jwt_token(token, expected_type=TokenType.REFRESH)
        return str(payload.get("jti"))
