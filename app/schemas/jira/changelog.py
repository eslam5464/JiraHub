from pydantic import BaseModel, ConfigDict


class JiraChangeItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    field: str
    fieldtype: str | None = None
    fromString: str | None = None
    toString: str | None = None


class JiraChangelogEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    created: str  # ISO datetime
    items: list[JiraChangeItem] = []

    def get_status_changes(self) -> list[JiraChangeItem]:
        """Filter changelog items to only status transitions."""
        return [item for item in self.items if item.field == "status"]


class JiraChangelog(BaseModel):
    model_config = ConfigDict(extra="allow")

    values: list[JiraChangelogEntry] = []
    maxResults: int = 100
    startAt: int = 0
    total: int = 0
    isLast: bool = True


class JiraStatusTransition(BaseModel):
    """Processed status transition with timestamps for cycle time analysis."""

    from_status: str | None
    to_status: str
    timestamp: str  # ISO datetime
    issue_key: str
