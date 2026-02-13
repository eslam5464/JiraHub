from datetime import datetime, timedelta, timezone

from loguru import logger

from app.core.config import get_settings
from app.core.constants import UserRole, UserStatus
from app.core.exceptions.domain import (
    AuthenticationError,
    AuthorizationError,
    DuplicateResourceError,
    ResourceNotFoundError,
    ValidationError,
)
from app.core.security import (
    decrypt_token,
    encrypt_token,
    generate_session_token,
    hash_password,
    verify_password,
)
from app.models.db import get_session_direct
from app.repos.session import SessionRepo
from app.repos.user import UserRepo
from app.schemas.session import SessionCreate
from app.schemas.user import UserCreate, UserRegister, UserResponse, UserUpdate


class AuthService:
    """Handles registration, login, session management, and Jira token storage."""

    @staticmethod
    async def register(data: UserRegister) -> UserResponse:
        """Register a new user. Auto-approves admin if email matches ADMIN_EMAIL."""
        settings = get_settings()
        session = await get_session_direct()

        try:
            user_repo = UserRepo(session)

            # Check for duplicate email
            existing = await user_repo.get_by_email(data.email)
            if existing:
                raise DuplicateResourceError("User", data.email)

            # Determine role and status
            is_admin = data.email.lower() == settings.admin_email.lower()
            role = UserRole.ADMIN if is_admin else UserRole.USER
            status = UserStatus.APPROVED if is_admin else UserStatus.PENDING

            # Create user
            create_data = UserCreate(
                email=data.email.lower(),
                password_hash=hash_password(data.password.get_secret_value()),
                role=role,
                status=status,
            )
            user = await user_repo.create_one(create_data)

            logger.info(f"User registered: {user.email} (role={role}, status={status})")
            return UserResponse.model_validate(user)

        finally:
            await session.close()

    @staticmethod
    async def login(email: str, password: str) -> tuple[UserResponse, str]:
        """Login a user. Returns (user_response, session_token).

        Raises:
            AuthenticationError: If credentials are invalid.
            AuthorizationError: If user account is not approved.
        """
        settings = get_settings()
        session = await get_session_direct()

        try:
            user_repo = UserRepo(session)
            session_repo = SessionRepo(session)

            # Find user
            user = await user_repo.get_by_email(email.lower())
            if not user:
                raise AuthenticationError("Invalid email or password")

            # Verify password
            if not verify_password(password, user.password_hash):
                raise AuthenticationError("Invalid email or password")

            # Check approval status
            if user.status == UserStatus.PENDING:
                raise AuthorizationError("Your account is pending admin approval")
            if user.status == UserStatus.REJECTED:
                raise AuthorizationError("Your account has been rejected")

            # Create session
            token = generate_session_token()
            session_data = SessionCreate(
                token=token,
                user_id=user.id,
                expires_at=datetime.now(timezone.utc)
                + timedelta(hours=settings.session_expiry_hours),
            )
            await session_repo.create_one(session_data)

            logger.info(f"User logged in: {user.email}")
            return UserResponse.model_validate(user), token

        finally:
            await session.close()

    @staticmethod
    async def restore_session(token: str) -> UserResponse | None:
        """Restore a session from a cookie token. Returns user if valid, None if expired/invalid."""
        session = await get_session_direct()

        try:
            session_repo = SessionRepo(session)
            user_repo = UserRepo(session)

            # Find valid session
            db_session = await session_repo.get_valid_by_token(token)
            if not db_session:
                return None

            # Find user
            user = await user_repo.get_by_id(db_session.user_id)
            if not user or user.status != UserStatus.APPROVED:
                return None

            return UserResponse.model_validate(user)

        finally:
            await session.close()

    @staticmethod
    async def logout(token: str) -> None:
        """Delete a session (logout)."""
        session = await get_session_direct()

        try:
            session_repo = SessionRepo(session)
            await session_repo.delete_by_token(token)
            logger.info("User logged out")
        finally:
            await session.close()

    @staticmethod
    async def connect_jira(
        user_id: int, jira_url: str, jira_email: str, jira_token: str
    ) -> UserResponse:
        """Store encrypted Jira credentials for a user.

        The caller should validate the token against Jira API before calling this.
        """
        session = await get_session_direct()

        try:
            user_repo = UserRepo(session)
            user = await user_repo.get_by_id(user_id)
            if not user:
                raise ResourceNotFoundError("User", str(user_id))

            encrypted = encrypt_token(jira_token)
            update_data = UserUpdate(
                jira_url=jira_url.rstrip("/"),
                jira_email=jira_email,
                encrypted_jira_token=encrypted,
            )
            updated = await user_repo.update_by_id(user_id, update_data)
            if not updated:
                raise ResourceNotFoundError("User", str(user_id))

            logger.info(f"Jira connected for user: {user.email}")
            return UserResponse.model_validate(updated)

        finally:
            await session.close()

    @staticmethod
    async def update_jira_profile(user_id: int, display_name: str, account_id: str) -> None:
        """Update user's Jira profile info (display name, account ID)."""
        session = await get_session_direct()

        try:
            user_repo = UserRepo(session)
            update_data = UserUpdate(
                jira_display_name=display_name,
                jira_account_id=account_id,
            )
            await user_repo.update_by_id(user_id, update_data)
        finally:
            await session.close()

    @staticmethod
    async def get_jira_token(user_id: int) -> tuple[str, str, str]:
        """Get decrypted Jira token, URL and email for a user. Returns (jira_url, jira_email, token)."""
        session = await get_session_direct()

        try:
            user_repo = UserRepo(session)
            user = await user_repo.get_by_id(user_id)
            if not user:
                raise ResourceNotFoundError("User", str(user_id))
            if not user.encrypted_jira_token or not user.jira_url:
                raise ValidationError(
                    "Jira credentials not configured - please connect your Jira account"
                )

            token = decrypt_token(user.encrypted_jira_token)
            jira_email = user.jira_email or user.email
            logger.debug(
                f"get_jira_token: user_id={user_id}, jira_url={user.jira_url}, "
                f"jira_email={jira_email} (from db: {user.jira_email}), "
                f"token_length={len(token)}"
            )
            return user.jira_url, jira_email, token

        finally:
            await session.close()

    @staticmethod
    async def get_pending_users() -> list[UserResponse]:
        """Get all pending users (admin function)."""
        session = await get_session_direct()

        try:
            user_repo = UserRepo(session)
            users = await user_repo.get_pending_users()
            return [UserResponse.model_validate(u) for u in users]
        finally:
            await session.close()

    @staticmethod
    async def get_all_users() -> list[UserResponse]:
        """Get all users (admin function)."""
        session = await get_session_direct()

        try:
            user_repo = UserRepo(session)
            users = await user_repo.get_all(limit=1000)
            return [UserResponse.model_validate(u) for u in users]
        finally:
            await session.close()

    @staticmethod
    async def approve_user(user_id: int) -> UserResponse:
        """Approve a pending user (admin function)."""
        session = await get_session_direct()

        try:
            user_repo = UserRepo(session)
            user = await user_repo.approve_user(user_id)
            if not user:
                raise ResourceNotFoundError("User", str(user_id))
            logger.info(f"User approved: {user.email}")
            return UserResponse.model_validate(user)
        finally:
            await session.close()

    @staticmethod
    async def reject_user(user_id: int) -> UserResponse:
        """Reject a pending user (admin function)."""
        session = await get_session_direct()

        try:
            user_repo = UserRepo(session)
            user = await user_repo.reject_user(user_id)
            if not user:
                raise ResourceNotFoundError("User", str(user_id))
            logger.info(f"User rejected: {user.email}")
            return UserResponse.model_validate(user)
        finally:
            await session.close()

    @staticmethod
    async def delete_user(user_id: int) -> bool:
        """Delete a user (admin function)."""
        session = await get_session_direct()

        try:
            user_repo = UserRepo(session)
            deleted = await user_repo.delete_by_id(user_id)
            if deleted:
                logger.info(f"User deleted: id={user_id}")
            return deleted
        finally:
            await session.close()

    @staticmethod
    async def cleanup_sessions() -> int:
        """Delete expired sessions. Returns count deleted."""
        session = await get_session_direct()

        try:
            session_repo = SessionRepo(session)
            count = await session_repo.cleanup_expired()
            if count:
                logger.info(f"Cleaned up {count} expired sessions")
            return count
        finally:
            await session.close()
