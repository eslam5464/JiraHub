from pydantic import BaseModel, ConfigDict


class JiraEstimationField(BaseModel):
    model_config = ConfigDict(extra="allow")

    fieldId: str
    displayName: str


class JiraEstimation(BaseModel):
    model_config = ConfigDict(extra="allow")

    field: JiraEstimationField | None = None
    type: str | None = None


class JiraBoardLocation(BaseModel):
    model_config = ConfigDict(extra="allow")

    projectId: int | None = None
    projectKey: str | None = None
    projectName: str | None = None


class JiraBoard(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    name: str
    type: str  # "scrum" or "kanban"
    location: JiraBoardLocation | None = None


class JiraBoardConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    name: str | None = None
    estimation: JiraEstimation | None = None

    @property
    def story_points_field(self) -> str | None:
        """Extract the custom field ID used for story points."""
        if self.estimation and self.estimation.field:
            return self.estimation.field.fieldId
        return None


class JiraBoardList(BaseModel):
    model_config = ConfigDict(extra="allow")

    values: list[JiraBoard] = []
    maxResults: int = 50
    startAt: int = 0
    total: int | None = None
    isLast: bool = True
