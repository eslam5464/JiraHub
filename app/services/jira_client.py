import asyncio
from base64 import b64encode

import httpx
from loguru import logger

from app.core.exceptions.domain import (
    JiraAuthenticationError,
    JiraConnectionError,
    JiraRateLimitError,
)
from app.schemas.jira.board import JiraBoard, JiraBoardConfig, JiraBoardList
from app.schemas.jira.changelog import (
    JiraChangelog,
    JiraChangelogEntry,
    JiraStatusTransition,
)
from app.schemas.jira.issue import (
    JiraFieldMeta,
    JiraIssue,
    JiraSearchResponse,
    JiraWorklogResponse,
)
from app.schemas.jira.sprint import JiraSprint, JiraSprintList
from app.schemas.jira.user import JiraUser


class JiraClient:
    """Async Jira Cloud API client using httpx."""

    def __init__(self, base_url: str, email: str, api_token: str, proxy_url: str | None = None):
        self.base_url = base_url.rstrip("/")
        self._email = email
        self._auth_header = self._build_auth_header(email, api_token)
        self._proxy_url = proxy_url
        self._client: httpx.AsyncClient | None = None
        logger.debug(
            f"JiraClient initialized: base_url={self.base_url}, email={email}, proxy={proxy_url or 'None'}"
        )

    @staticmethod
    def _build_auth_header(email: str, api_token: str) -> str:
        credentials = b64encode(f"{email}:{api_token}".encode()).decode()
        return f"Basic {credentials}"

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": self._auth_header,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            # Create AsyncClient with optional proxy
            client_kwargs = {
                "base_url": self.base_url,
                "headers": self._headers,
                "timeout": httpx.Timeout(30.0),
            }

            # Add proxy if configured
            if self._proxy_url:
                client_kwargs["proxies"] = self._proxy_url
                logger.debug(f"Using proxy: {self._proxy_url}")

            self._client = httpx.AsyncClient(**client_kwargs)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json_data: dict | None = None,
        max_retries: int = 3,
    ) -> dict:
        """Make an authenticated request with rate limit handling and retries."""
        client = await self._get_client()

        for attempt in range(max_retries):
            try:
                response = await client.request(
                    method,
                    path,
                    params=params,
                    json=json_data,
                )

                if response.status_code == 200:
                    return response.json()

                if response.status_code == 401:
                    logger.warning("Jira authentication failed - check API token")
                    logger.error(f"Jira auth error response: {response.text}")
                    raise JiraAuthenticationError()

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "10"))
                    if attempt < max_retries - 1:
                        wait = retry_after * (2**attempt)
                        logger.warning(
                            f"Jira rate limit hit, retrying in {wait}s (attempt {attempt + 1})"
                        )
                        await asyncio.sleep(wait)
                        continue
                    raise JiraRateLimitError(retry_after=retry_after)

                if response.status_code == 403:
                    raise JiraAuthenticationError("Insufficient permissions for this Jira resource")

                # Other errors
                error_msg = f"Jira API error: {response.status_code}"
                try:
                    error_body = response.json()
                    if "errorMessages" in error_body:
                        error_msg += f" - {', '.join(error_body['errorMessages'])}"
                except Exception:
                    error_msg += f" - {response.text[:200]}"

                raise JiraConnectionError(error_msg)

            except httpx.ConnectError as e:
                raise JiraConnectionError(f"Cannot connect to Jira at {self.base_url}: {e}") from e
            except httpx.TimeoutException as e:
                if attempt < max_retries - 1:
                    wait = 2 ** (attempt + 1)
                    logger.warning(
                        f"Jira request timeout, retrying in {wait}s (attempt {attempt + 1})"
                    )
                    await asyncio.sleep(wait)
                    continue
                raise JiraConnectionError(
                    f"Jira request timed out after {max_retries} attempts"
                ) from e

        raise JiraConnectionError("Max retries exceeded")

    # ─── Authentication ───────────────────────────────────────────────

    async def get_myself(self) -> JiraUser:
        """Validate credentials and get the authenticated user's profile."""
        data = await self._request("GET", "/rest/api/3/myself")
        return JiraUser.model_validate(data)

    # ─── Boards ───────────────────────────────────────────────────────

    async def get_boards(
        self,
        *,
        project_key: str | None = None,
        board_type: str | None = None,
    ) -> list[JiraBoard]:
        """Get all boards, optionally filtered by project or type."""
        params: dict = {"maxResults": 50, "startAt": 0}
        if project_key:
            params["projectKeyOrId"] = project_key
        if board_type:
            params["type"] = board_type

        all_boards: list[JiraBoard] = []
        while True:
            data = await self._request("GET", "/rest/agile/1.0/board", params=params)
            result = JiraBoardList.model_validate(data)
            all_boards.extend(result.values)
            if result.isLast:
                break
            params["startAt"] += result.maxResults

        return all_boards

    async def get_board_config(self, board_id: int) -> JiraBoardConfig:
        """Get board configuration, including the story points field."""
        data = await self._request("GET", f"/rest/agile/1.0/board/{board_id}/configuration")
        return JiraBoardConfig.model_validate(data)

    # ─── Sprints ──────────────────────────────────────────────────────

    async def get_sprints(
        self,
        board_id: int,
        *,
        state: str | None = None,
    ) -> list[JiraSprint]:
        """Get sprints for a board. state: 'active', 'closed', 'future', or None for all."""
        params: dict = {"maxResults": 50, "startAt": 0}
        if state:
            params["state"] = state

        all_sprints: list[JiraSprint] = []
        while True:
            data = await self._request(
                "GET", f"/rest/agile/1.0/board/{board_id}/sprint", params=params
            )
            result = JiraSprintList.model_validate(data)
            all_sprints.extend(result.values)
            if result.isLast:
                break
            params["startAt"] += result.maxResults

        return all_sprints

    # ─── Issues ───────────────────────────────────────────────────────

    async def search_issues(
        self,
        jql: str,
        *,
        fields: list[str] | None = None,
        max_results: int = 100,
    ) -> list[JiraIssue]:
        """Search issues using JQL. Handles pagination automatically."""
        all_issues: list[JiraIssue] = []
        next_page_token: str | None = None

        default_fields = [
            "summary",
            "status",
            "assignee",
            "issuetype",
            "priority",
            "duedate",
            "labels",
            "created",
            "updated",
            "resolutiondate",
        ]
        request_fields = fields or default_fields

        while True:
            json_data: dict = {
                "jql": jql,
                "fields": request_fields,
                "maxResults": min(max_results - len(all_issues), 100),
            }
            if next_page_token:
                json_data["nextPageToken"] = next_page_token

            data = await self._request("POST", "/rest/api/3/search/jql", json_data=json_data)
            result = JiraSearchResponse.model_validate(data)
            all_issues.extend(result.issues)

            if not result.nextPageToken or len(all_issues) >= max_results:
                break
            next_page_token = result.nextPageToken

        return all_issues[:max_results]

    async def get_sprint_issues(
        self,
        board_id: int,
        sprint_id: int,
        *,
        fields: list[str] | None = None,
    ) -> list[JiraIssue]:
        """Get all issues in a sprint."""
        default_fields = [
            "summary",
            "status",
            "assignee",
            "issuetype",
            "priority",
            "duedate",
            "labels",
            "created",
            "updated",
            "resolutiondate",
        ]
        request_fields = fields or default_fields
        params: dict = {
            "maxResults": 100,
            "startAt": 0,
            "fields": ",".join(request_fields),
        }

        all_issues: list[JiraIssue] = []
        while True:
            data = await self._request(
                "GET",
                f"/rest/agile/1.0/board/{board_id}/sprint/{sprint_id}/issue",
                params=params,
            )
            issues = [JiraIssue.model_validate(i) for i in data.get("issues", [])]
            all_issues.extend(issues)

            total = data.get("total", 0)
            if len(all_issues) >= total:
                break
            params["startAt"] += params["maxResults"]

        return all_issues

    # ─── Changelog ────────────────────────────────────────────────────

    async def get_issue_changelog(
        self,
        issue_key: str,
        *,
        max_results: int = 100,
    ) -> list[JiraChangelogEntry]:
        """Get the changelog for an issue (for cycle time analysis)."""
        params: dict = {"maxResults": max_results, "startAt": 0}
        all_entries: list[JiraChangelogEntry] = []

        while True:
            data = await self._request(
                "GET",
                f"/rest/api/3/issue/{issue_key}/changelog",
                params=params,
            )
            result = JiraChangelog.model_validate(data)
            all_entries.extend(result.values)

            if result.isLast or len(all_entries) >= result.total:
                break
            params["startAt"] += result.maxResults

        return all_entries

    async def get_status_transitions(self, issue_key: str) -> list[JiraStatusTransition]:
        """Get status transitions for an issue (processed for cycle time)."""
        entries = await self.get_issue_changelog(issue_key)
        transitions: list[JiraStatusTransition] = []

        for entry in entries:
            for item in entry.get_status_changes():
                transitions.append(
                    JiraStatusTransition(
                        from_status=item.fromString,
                        to_status=item.toString or "",
                        timestamp=entry.created,
                        issue_key=issue_key,
                    )
                )

        return transitions

    # ─── Team Members ─────────────────────────────────────────────────

    async def get_project_members(self, project_key: str) -> list[JiraUser]:
        """Get assignable users for a project."""
        params: dict = {
            "project": project_key,
            "maxResults": 1000,
        }
        data = await self._request("GET", "/rest/api/3/user/assignable/search", params=params)
        return [JiraUser.model_validate(u) for u in data]

    # ─── Single Issue & Worklogs ──────────────────────────────────────

    async def get_issue(
        self,
        issue_key: str,
        *,
        fields: list[str] | None = None,
        expand: list[str] | None = None,
    ) -> JiraIssue:
        """Fetch a single issue by key with specified fields."""
        params: dict = {}
        if fields:
            params["fields"] = ",".join(fields)
        if expand:
            params["expand"] = ",".join(expand)
        data = await self._request("GET", f"/rest/api/3/issue/{issue_key}", params=params)
        return JiraIssue.model_validate(data)

    async def get_issue_worklogs(
        self,
        issue_key: str,
        *,
        max_results: int = 1000,
    ) -> JiraWorklogResponse:
        """Get worklogs for an issue (time tracking per person)."""
        params: dict = {"maxResults": max_results, "startAt": 0}
        data = await self._request("GET", f"/rest/api/3/issue/{issue_key}/worklog", params=params)
        return JiraWorklogResponse.model_validate(data)

    # ─── Field Discovery ──────────────────────────────────────────────

    async def get_all_fields(self) -> list[JiraFieldMeta]:
        """Get all available fields (for discovering custom fields like Team)."""
        data = await self._request("GET", "/rest/api/3/field")
        return [JiraFieldMeta.model_validate(f) for f in data]

    async def discover_field_by_name(self, field_name: str) -> str | None:
        """Find a custom field ID by its display name (case-insensitive)."""
        all_fields = await self.get_all_fields()
        target = field_name.lower()
        for f in all_fields:
            if f.name.lower() == target:
                return f.id
        return None
