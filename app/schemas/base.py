from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        extra="forbid",
    )


class BaseTimestampSchema(BaseSchema):
    created_at: datetime
    updated_at: datetime | None = None
