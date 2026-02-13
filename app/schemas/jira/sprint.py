from pydantic import BaseModel, ConfigDict


class JiraSprint(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    name: str
    state: str  # "active", "closed", "future"
    startDate: str | None = None
    endDate: str | None = None
    completeDate: str | None = None
    originBoardId: int | None = None
    goal: str | None = None


class JiraSprintList(BaseModel):
    model_config = ConfigDict(extra="allow")

    values: list[JiraSprint] = []
    maxResults: int = 50
    startAt: int = 0
    isLast: bool = True
