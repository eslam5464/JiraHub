from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import FieldSizes
from app.models.base import Base


class IgnoredTicket(Base):
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ticket_key: Mapped[str] = mapped_column(String(FieldSizes.SHORT), nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
