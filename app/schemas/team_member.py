from datetime import datetime

from pydantic import Field

from app.schemas.base import BaseSchema


class TeamMemberCreate(BaseSchema):
    jira_account_id: str
    display_name: str
    email: str | None = None
    avatar_url: str | None = None
    labels: list[str] = Field(default_factory=list)
    created_by: int


class TeamMemberUpdate(BaseSchema):
    display_name: str | None = None
    email: str | None = None
    avatar_url: str | None = None
    labels: list[str] | None = None


class TeamMemberResponse(BaseSchema):
    id: int
    jira_account_id: str
    display_name: str
    email: str | None = None
    avatar_url: str | None = None
    labels: list[str]
    created_by: int
    created_at: datetime
    updated_at: datetime | None = None
