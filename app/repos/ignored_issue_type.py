from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ignored_issue_type import IgnoredIssueType
from app.repos.base import BaseRepository
from app.schemas.settings import IgnoredIssueTypeCreate


class IgnoredIssueTypeRepo(
    BaseRepository[IgnoredIssueType, IgnoredIssueTypeCreate, IgnoredIssueTypeCreate]
):
    def __init__(self, session: AsyncSession):
        super().__init__(session, IgnoredIssueType)

    async def get_by_user(self, user_id: int) -> list[IgnoredIssueType]:
        """Get all ignored issue types for a user."""
        stmt = select(IgnoredIssueType).where(IgnoredIssueType.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_ignored_types(self, user_id: int) -> set[str]:
        """Get the set of ignored issue type names for a user."""
        types = await self.get_by_user(user_id)
        return {t.issue_type for t in types}

    async def set_ignored_types(
        self,
        user_id: int,
        issue_types: list[str],
        *,
        auto_commit: bool = True,
    ) -> list[IgnoredIssueType]:
        """Replace all ignored issue types for a user."""
        # Delete existing
        stmt = delete(IgnoredIssueType).where(IgnoredIssueType.user_id == user_id)
        await self.session.execute(stmt)

        # Create new
        instances = []
        for it in issue_types:
            schema = IgnoredIssueTypeCreate(user_id=user_id, issue_type=it)
            instance = await self.create_one(schema, auto_commit=False)
            instances.append(instance)

        if auto_commit:
            await self.session.commit()
        return instances
