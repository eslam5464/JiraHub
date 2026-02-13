from typing import Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Generic repository with async CRUD operations."""

    def __init__(self, session: AsyncSession, model: type[ModelType]):
        self.session = session
        self.model = model

    async def create_one(
        self,
        schema: CreateSchemaType,
        *,
        exclude_none: bool = False,
        auto_commit: bool = True,
    ) -> ModelType:
        """Create a single record."""
        data = schema.model_dump(exclude_none=exclude_none)
        instance = self.model(**data)
        self.session.add(instance)
        if auto_commit:
            await self.session.commit()
            await self.session.refresh(instance)
        else:
            await self.session.flush()
        return instance

    async def get_by_id(self, obj_id: int) -> ModelType | None:
        """Get a record by its primary key."""
        return await self.session.get(self.model, obj_id)

    async def get_all(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ModelType]:
        """Get all records with pagination."""
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_by_id(
        self,
        obj_id: int,
        schema: UpdateSchemaType,
        *,
        exclude_none: bool = True,
        auto_commit: bool = True,
    ) -> ModelType | None:
        """Update a record by ID."""
        instance = await self.get_by_id(obj_id)
        if not instance:
            return None

        data = schema.model_dump(exclude_none=exclude_none)
        for key, value in data.items():
            setattr(instance, key, value)

        if auto_commit:
            await self.session.commit()
            await self.session.refresh(instance)
        else:
            await self.session.flush()
        return instance

    async def delete_by_id(self, obj_id: int, *, auto_commit: bool = True) -> bool:
        """Delete a record by ID. Returns True if deleted."""
        instance = await self.get_by_id(obj_id)
        if not instance:
            return False
        await self.session.delete(instance)
        if auto_commit:
            await self.session.commit()
        return True

    async def delete_by_ids(self, obj_ids: list[int], *, auto_commit: bool = True) -> int:
        """Delete multiple records by IDs. Returns count of deleted."""
        stmt = delete(self.model).where(self.model.id.in_(obj_ids))
        result = await self.session.execute(stmt)
        if auto_commit:
            await self.session.commit()
        return result.rowcount  # type: ignore

    async def count(self) -> int:
        """Count all records."""
        from sqlalchemy import func

        stmt = select(func.count()).select_from(self.model)
        result = await self.session.execute(stmt)
        return result.scalar_one()
