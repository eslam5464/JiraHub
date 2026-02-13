from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import UserRole, UserStatus
from app.models.user import User
from app.repos.base import BaseRepository
from app.schemas.user import UserCreate, UserUpdate


class UserRepo(BaseRepository[User, UserCreate, UserUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_email(self, email: str) -> User | None:
        """Get a user by email (case-insensitive)."""
        stmt = select(User).where(User.email == email.lower())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_pending_users(self) -> list[User]:
        """Get all users with pending status."""
        stmt = select(User).where(User.status == UserStatus.PENDING)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_approved_users(self) -> list[User]:
        """Get all approved users."""
        stmt = select(User).where(User.status == UserStatus.APPROVED)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def approve_user(self, user_id: int) -> User | None:
        """Approve a pending user."""
        return await self.update_by_id(
            user_id,
            UserUpdate(status=UserStatus.APPROVED),
        )

    async def reject_user(self, user_id: int) -> User | None:
        """Reject a pending user."""
        return await self.update_by_id(
            user_id,
            UserUpdate(status=UserStatus.REJECTED),
        )

    async def get_admins(self) -> list[User]:
        """Get all admin users."""
        stmt = select(User).where(User.role == UserRole.ADMIN)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
