from datetime import datetime

from app.schemas.base import BaseSchema


class SessionCreate(BaseSchema):
    token: str
    user_id: int
    expires_at: datetime


class SessionResponse(BaseSchema):
    id: int
    token: str
    user_id: int
    expires_at: datetime
    created_at: datetime
