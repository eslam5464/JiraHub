from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import FieldSizes
from app.models.base import Base


class IgnoredIssueType(Base):
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    issue_type: Mapped[str] = mapped_column(String(FieldSizes.MEDIUM), nullable=False)
