from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.team_member import TeamMember
from app.repos.base import BaseRepository
from app.schemas.team_member import TeamMemberCreate, TeamMemberUpdate


class TeamMemberRepo(BaseRepository[TeamMember, TeamMemberCreate, TeamMemberUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, TeamMember)

    async def get_by_jira_account_id(self, jira_account_id: str) -> TeamMember | None:
        """Get a team member by their Jira account ID."""
        stmt = select(TeamMember).where(TeamMember.jira_account_id == jira_account_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_labels(self, labels: list[str]) -> list[TeamMember]:
        """Get team members that have any of the specified labels.

        Since labels are stored as JSON, we filter in Python after fetching.
        For SQLite JSON support, this is the most portable approach.
        """
        all_members = await self.get_all(limit=1000)
        return [m for m in all_members if m.labels and any(label in m.labels for label in labels)]

    async def get_all_with_labels(self) -> list[TeamMember]:
        """Get all team members that have at least one label assigned."""
        all_members = await self.get_all(limit=1000)
        return [m for m in all_members if m.labels]

    async def upsert(
        self,
        schema: TeamMemberCreate,
        *,
        auto_commit: bool = True,
    ) -> TeamMember:
        """Create or update a team member by Jira account ID."""
        existing = await self.get_by_jira_account_id(schema.jira_account_id)
        if existing:
            update_data = TeamMemberUpdate(
                display_name=schema.display_name,
                email=schema.email,
                avatar_url=schema.avatar_url,
            )
            for key, value in update_data.model_dump(exclude_none=True).items():
                setattr(existing, key, value)
            if auto_commit:
                await self.session.commit()
                await self.session.refresh(existing)
            return existing
        return await self.create_one(schema, auto_commit=auto_commit)
