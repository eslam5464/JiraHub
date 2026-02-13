from app.schemas.base import BaseSchema, BaseTimestampSchema


class BoardEntry(BaseSchema):
    id: int
    name: str


class UserProjectCreate(BaseSchema):
    user_id: int
    project_key: str
    project_name: str
    boards: list[BoardEntry]
    is_active: bool = True


class UserProjectUpdate(BaseSchema):
    boards: list[BoardEntry] | None = None
    is_active: bool | None = None


class UserProjectResponse(BaseTimestampSchema):
    id: int
    user_id: int
    project_key: str
    project_name: str
    boards: list[BoardEntry]
    is_active: bool
