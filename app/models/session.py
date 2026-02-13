from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import FieldSizes
from app.models.base import Base


class Session(Base):
    token: Mapped[str] = mapped_column(
        String(FieldSizes.MEDIUM), unique=True, nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
