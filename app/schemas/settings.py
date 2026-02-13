from datetime import datetime

from app.schemas.base import BaseSchema


class IgnoredTicketCreate(BaseSchema):
    user_id: int
    ticket_key: str
    reason: str | None = None


class IgnoredTicketResponse(BaseSchema):
    id: int
    user_id: int
    ticket_key: str
    reason: str | None = None
    created_at: datetime


class IgnoredIssueTypeCreate(BaseSchema):
    user_id: int
    issue_type: str


class IgnoredIssueTypeResponse(BaseSchema):
    id: int
    user_id: int
    issue_type: str
    created_at: datetime
