from pydantic import BaseModel, ConfigDict


class JiraUser(BaseModel):
    """Jira user from API responses (assignee, reporter, /myself)."""

    model_config = ConfigDict(extra="allow")

    accountId: str
    displayName: str
    emailAddress: str | None = None
    active: bool = True
    avatarUrls: dict[str, str] | None = None

    @property
    def avatar_48(self) -> str | None:
        if self.avatarUrls:
            return self.avatarUrls.get("48x48")
        return None
