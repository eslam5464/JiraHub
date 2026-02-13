import re
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    __abstract__ = True

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    @declared_attr.directive
    @classmethod
    def __tablename__(cls) -> str:
        """Auto-generate table name from class name (PascalCase → snake_case)."""
        return re.sub(r"(?<!^)(?=[A-Z])", "_", cls.__name__).lower()

    def to_dict(self, exclude_keys: set[str] | None = None, exclude_none: bool = False) -> dict:
        """Convert model instance to dictionary."""
        exclude = exclude_keys or set()
        result = {}
        for column in self.__table__.columns:
            if column.name in exclude:
                continue
            value = getattr(self, column.name)
            if exclude_none and value is None:
                continue
            result[column.name] = value
        return result
