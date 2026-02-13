from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session
from app.repos.base import BaseRepository
from app.schemas.session import SessionCreate


class SessionRepo(BaseRepository[Session, SessionCreate, SessionCreate]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Session)

    async def get_valid_by_token(self, token: str) -> Session | None:
        """Get a session by token if it hasn't expired."""
        stmt = select(Session).where(
            Session.token == token,
            Session.expires_at > datetime.now(timezone.utc),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_by_token(self, token: str, *, auto_commit: bool = True) -> bool:
        """Delete a session by its token."""
        stmt = delete(Session).where(Session.token == token)
        result = await self.session.execute(stmt)
        if auto_commit:
            await self.session.commit()
        return result.rowcount > 0  # type: ignore

    async def delete_user_sessions(self, user_id: int, *, auto_commit: bool = True) -> int:
        """Delete all sessions for a user."""
        stmt = delete(Session).where(Session.user_id == user_id)
        result = await self.session.execute(stmt)
        if auto_commit:
            await self.session.commit()
        return result.rowcount  # type: ignore

    async def cleanup_expired(self, *, auto_commit: bool = True) -> int:
        """Delete all expired sessions. Returns count deleted."""
        stmt = delete(Session).where(Session.expires_at <= datetime.now(timezone.utc))
        result = await self.session.execute(stmt)
        if auto_commit:
            await self.session.commit()
        return result.rowcount  # type: ignore
