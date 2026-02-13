from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import FieldSizes, UserRole, UserStatus
from app.models.base import Base


class User(Base):
    email: Mapped[str] = mapped_column(
        String(FieldSizes.MEDIUM), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(FieldSizes.LONG), nullable=False)
    role: Mapped[str] = mapped_column(
        String(FieldSizes.TINY), nullable=False, default=UserRole.USER
    )
    status: Mapped[str] = mapped_column(
        String(FieldSizes.TINY), nullable=False, default=UserStatus.PENDING
    )

    # Jira credentials (filled after Jira Connect)
    jira_url: Mapped[str | None] = mapped_column(String(FieldSizes.LONG), nullable=True)
    jira_email: Mapped[str | None] = mapped_column(String(FieldSizes.MEDIUM), nullable=True)
    encrypted_jira_token: Mapped[str | None] = mapped_column(String(FieldSizes.TEXT), nullable=True)
    jira_display_name: Mapped[str | None] = mapped_column(String(FieldSizes.MEDIUM), nullable=True)
    jira_account_id: Mapped[str | None] = mapped_column(String(FieldSizes.MEDIUM), nullable=True)
