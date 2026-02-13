from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ignored_ticket import IgnoredTicket
from app.repos.base import BaseRepository
from app.schemas.settings import IgnoredTicketCreate


class IgnoredTicketRepo(BaseRepository[IgnoredTicket, IgnoredTicketCreate, IgnoredTicketCreate]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, IgnoredTicket)

    async def get_by_user(self, user_id: int) -> list[IgnoredTicket]:
        """Get all ignored tickets for a user."""
        stmt = select(IgnoredTicket).where(IgnoredTicket.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def is_ignored(self, user_id: int, ticket_key: str) -> bool:
        """Check if a ticket is ignored by a user."""
        stmt = select(IgnoredTicket).where(
            IgnoredTicket.user_id == user_id,
            IgnoredTicket.ticket_key == ticket_key,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_ignored_keys(self, user_id: int) -> set[str]:
        """Get the set of ignored ticket keys for a user."""
        tickets = await self.get_by_user(user_id)
        return {t.ticket_key for t in tickets}

    async def unignore(self, user_id: int, ticket_key: str, *, auto_commit: bool = True) -> bool:
        """Remove a ticket from the ignored list."""
        stmt = delete(IgnoredTicket).where(
            IgnoredTicket.user_id == user_id,
            IgnoredTicket.ticket_key == ticket_key,
        )
        result = await self.session.execute(stmt)
        if auto_commit:
            await self.session.commit()
        return result.rowcount > 0  # type: ignore
