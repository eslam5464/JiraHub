from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class JiraStatusCategory(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    key: str
    name: str


class JiraStatus(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    id: str | None = None
    statusCategory: JiraStatusCategory | None = None


class JiraIssueType(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    id: str | None = None
    subtask: bool = False
    iconUrl: str | None = None


class JiraPriority(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    id: str | None = None
    iconUrl: str | None = None


# ─── Time Tracking & Worklogs ────────────────────────────────────────


class JiraTimeTracking(BaseModel):
    model_config = ConfigDict(extra="allow")

    originalEstimate: str | None = None
    remainingEstimate: str | None = None
    timeSpent: str | None = None
    originalEstimateSeconds: int | None = None
    remainingEstimateSeconds: int | None = None
    timeSpentSeconds: int | None = None


class JiraWorklogAuthor(BaseModel):
    model_config = ConfigDict(extra="allow")

    accountId: str | None = None
    displayName: str | None = None
    emailAddress: str | None = None


class JiraWorklogEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str | None = None
    author: JiraWorklogAuthor | None = None
    updateAuthor: JiraWorklogAuthor | None = None
    timeSpent: str | None = None
    timeSpentSeconds: int | None = None
    started: str | None = None
    created: str | None = None
    updated: str | None = None
    comment: dict | None = None  # ADF format


class JiraWorklogResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    total: int = 0
    maxResults: int = 0
    startAt: int = 0
    worklogs: list[JiraWorklogEntry] = []


# ─── Parent / Links / Subtasks ────────────────────────────────────────


class JiraParent(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str | None = None
    key: str
    fields: JiraParentFields | None = None


class JiraParentFields(BaseModel):
    model_config = ConfigDict(extra="allow")

    summary: str | None = None
    status: JiraStatus | None = None
    issuetype: JiraIssueType | None = None
    priority: JiraPriority | None = None


class JiraIssueLinkType(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str | None = None
    name: str | None = None
    inward: str | None = None
    outward: str | None = None


class JiraLinkedIssueRef(BaseModel):
    """Minimal issue reference used inside an issue link."""

    model_config = ConfigDict(extra="allow")

    id: str | None = None
    key: str
    fields: JiraParentFields | None = None


class JiraIssueLink(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str | None = None
    type: JiraIssueLinkType | None = None
    inwardIssue: JiraLinkedIssueRef | None = None
    outwardIssue: JiraLinkedIssueRef | None = None


class JiraSubtask(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str | None = None
    key: str
    fields: JiraParentFields | None = None


# ─── Sprint (embedded in issue response) ─────────────────────────────


class JiraSprintInfo(BaseModel):
    """Sprint info as embedded in an issue (differs from the board-level JiraSprint)."""

    model_config = ConfigDict(extra="allow")

    id: int | None = None
    name: str | None = None
    state: str | None = None
    startDate: str | None = None
    endDate: str | None = None
    goal: str | None = None


# ─── Issue Fields & Issue ─────────────────────────────────────────────


class JiraIssueFields(BaseModel):
    """Issue fields from Jira API. Story points field is dynamic (custom field)."""

    model_config = ConfigDict(extra="allow")

    summary: str
    status: JiraStatus
    assignee: JiraUser | None = None
    reporter: JiraUser | None = None
    issuetype: JiraIssueType
    priority: JiraPriority | None = None
    duedate: str | None = None  # ISO date string "YYYY-MM-DD"
    labels: list[str] = []
    created: str | None = None
    updated: str | None = None
    resolutiondate: str | None = None
    parent: JiraParent | None = None
    issuelinks: list[JiraIssueLink] = []
    subtasks: list[JiraSubtask] = []
    timetracking: JiraTimeTracking | None = None


class JiraIssue(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    key: str
    fields: JiraIssueFields

    def get_story_points(self, story_points_field: str | None) -> float | None:
        """Get story points from the dynamic custom field."""
        if not story_points_field:
            return None
        # The field is stored in the extra fields via model_config extra="allow"
        return getattr(self.fields, story_points_field, None)

    def get_sprint(self) -> JiraSprintInfo | None:
        """Get sprint info from the dynamic sprint field."""
        # Sprint may be in a custom field like customfield_10020
        # or in the 'sprint' extra field
        sprint_data = getattr(self.fields, "sprint", None)
        if sprint_data and isinstance(sprint_data, dict):
            return JiraSprintInfo.model_validate(sprint_data)
        # Some Jira configs return sprint as a list (active + closed)
        if sprint_data and isinstance(sprint_data, list) and sprint_data:
            # Return the last (most recent / active) sprint
            return JiraSprintInfo.model_validate(sprint_data[-1])
        return None


class JiraSearchResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    issues: list[JiraIssue] = []
    total: int = 0
    nextPageToken: str | None = None


# ─── Field metadata (for auto-discovering custom fields) ─────────────


class JiraFieldMeta(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    custom: bool = False
    clauseNames: list[str] = []
    schema_: dict | None = None


# Avoid circular import - resolve forward ref
from app.schemas.jira.user import JiraUser  # noqa: E402

JiraIssueFields.model_rebuild()
JiraParent.model_rebuild()
JiraLinkedIssueRef.model_rebuild()
JiraSubtask.model_rebuild()
