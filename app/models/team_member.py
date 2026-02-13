from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import FieldSizes
from app.models.base import Base


class TeamMember(Base):
    jira_account_id: Mapped[str] = mapped_column(
        String(FieldSizes.MEDIUM), unique=True, nullable=False, index=True
    )
    display_name: Mapped[str] = mapped_column(String(FieldSizes.MEDIUM), nullable=False)
    email: Mapped[str | None] = mapped_column(String(FieldSizes.MEDIUM), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(FieldSizes.LONG), nullable=True)
    labels: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_by: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
