from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_project import UserProject
from app.repos.base import BaseRepository
from app.schemas.user_project import UserProjectCreate, UserProjectUpdate


class UserProjectRepo(BaseRepository[UserProject, UserProjectCreate, UserProjectUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, UserProject)

    async def get_active_projects(self, user_id: int) -> list[UserProject]:
        """Get all active projects for a user."""
        stmt = (
            select(UserProject)
            .where(UserProject.user_id == user_id, UserProject.is_active.is_(True))
            .order_by(UserProject.project_key)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_user_projects(self, user_id: int) -> list[UserProject]:
        """Get all projects (active and inactive) for a user."""
        stmt = (
            select(UserProject)
            .where(UserProject.user_id == user_id)
            .order_by(UserProject.project_key)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_user_and_key(self, user_id: int, project_key: str) -> UserProject | None:
        """Get a specific user-project mapping."""
        stmt = select(UserProject).where(
            UserProject.user_id == user_id,
            UserProject.project_key == project_key,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def set_active_projects(
        self,
        user_id: int,
        projects: list[dict],
    ) -> list[UserProject]:
        """Set the active projects for a user.

        Upserts project entries and deactivates any not in the list.

        Args:
            user_id: The user's ID.
            projects: List of dicts with keys: project_key, project_name,
                      boards (list of {"id": int, "name": str}).
        """
        active_keys = {p["project_key"] for p in projects}
        projects_by_key = {p["project_key"]: p for p in projects}

        # Deactivate projects not in the new list, update boards for existing
        existing = await self.get_all_user_projects(user_id)
        for proj in existing:
            if proj.project_key not in active_keys:
                proj.is_active = False
            else:
                proj.is_active = True
                proj.boards = projects_by_key[proj.project_key]["boards"]

        existing_keys = {p.project_key for p in existing}

        # Create new projects that don't exist yet
        for p in projects:
            if p["project_key"] not in existing_keys:
                new_proj = UserProject(
                    user_id=user_id,
                    project_key=p["project_key"],
                    project_name=p["project_name"],
                    boards=p["boards"],
                    is_active=True,
                )
                self.session.add(new_proj)

        await self.session.commit()
        return await self.get_active_projects(user_id)
