from sqlalchemy import JSON, Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import FieldSizes
from app.models.base import Base


class UserProject(Base):
    __table_args__ = (UniqueConstraint("user_id", "project_key", name="uq_user_project"),)

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_key: Mapped[str] = mapped_column(String(FieldSizes.SHORT), nullable=False)
    project_name: Mapped[str] = mapped_column(String(FieldSizes.MEDIUM), nullable=False)
    boards: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list
    )  # [{"id": 123, "name": "Board Name"}, ...]
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
