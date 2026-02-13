from datetime import date, datetime
from typing import Any

from app.schemas.jira.changelog import JiraStatusTransition
from app.schemas.jira.issue import JiraIssue


def get_overdue_tickets(
    issues: list[JiraIssue],
    *,
    done_statuses: set[str] | None = None,
) -> list[JiraIssue]:
    """Filter issues that are overdue (past due date and not in a done status)."""
    if done_statuses is None:
        done_statuses = {"Done", "Closed", "Resolved"}

    today = date.today()
    overdue: list[JiraIssue] = []

    for issue in issues:
        if issue.fields.duedate and issue.fields.status.name not in done_statuses:
            try:
                due = date.fromisoformat(issue.fields.duedate)
                if due < today:
                    overdue.append(issue)
            except ValueError:
                continue

    return sorted(
        overdue,
        key=lambda i: (date.fromisoformat(i.fields.duedate) if i.fields.duedate else today),
    )


def get_missing_story_points(
    issues: list[JiraIssue],
    story_points_field: str | None,
) -> list[JiraIssue]:
    """Filter issues that don't have story points assigned."""
    return [issue for issue in issues if issue.get_story_points(story_points_field) is None]


def calculate_workload(
    issues: list[JiraIssue],
    story_points_field: str | None,
) -> dict[str, dict[str, Any]]:
    """Calculate workload distribution per assignee.

    Returns:
        dict mapping assignee display name to:
            - total_tickets: int
            - total_story_points: float
            - in_progress: int
            - done: int
            - overdue: int
            - missing_sp: int
    """
    today = date.today()
    done_statuses = {"Done", "Closed", "Resolved"}
    in_progress_statuses = {"In Progress", "In Review", "In Development"}

    workload: dict[str, dict[str, Any]] = {}

    for issue in issues:
        assignee_name = issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned"

        if assignee_name not in workload:
            workload[assignee_name] = {
                "total_tickets": 0,
                "total_story_points": 0.0,
                "in_progress": 0,
                "done": 0,
                "overdue": 0,
                "missing_sp": 0,
            }

        w = workload[assignee_name]
        w["total_tickets"] += 1

        sp = issue.get_story_points(story_points_field)
        if sp is not None:
            w["total_story_points"] += sp
        else:
            w["missing_sp"] += 1

        status_name = issue.fields.status.name
        if status_name in done_statuses:
            w["done"] += 1
        elif status_name in in_progress_statuses:
            w["in_progress"] += 1

        if issue.fields.duedate and status_name not in done_statuses:
            try:
                if date.fromisoformat(issue.fields.duedate) < today:
                    w["overdue"] += 1
            except ValueError:
                pass

    return workload


def calculate_status_distribution(
    issues: list[JiraIssue],
) -> dict[str, dict[str, int]]:
    """Calculate status distribution per assignee.

    Returns:
        dict mapping assignee name to dict of status_name → count
    """
    dist: dict[str, dict[str, int]] = {}

    for issue in issues:
        assignee_name = issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned"

        if assignee_name not in dist:
            dist[assignee_name] = {}

        status = issue.fields.status.name
        dist[assignee_name][status] = dist[assignee_name].get(status, 0) + 1

    return dist


def calculate_cycle_time(
    transitions: list[JiraStatusTransition],
    *,
    start_status: str = "In Progress",
    end_status: str = "Done",
) -> float | None:
    """Calculate cycle time (in hours) between two status transitions for an issue.

    Returns None if the transitions don't have a complete start→end pair.
    """
    started_at: datetime | None = None
    ended_at: datetime | None = None

    for t in transitions:
        if t.to_status == start_status and started_at is None:
            started_at = datetime.fromisoformat(t.timestamp)
        if t.to_status == end_status and started_at is not None:
            ended_at = datetime.fromisoformat(t.timestamp)

    if started_at and ended_at:
        delta = ended_at - started_at
        return delta.total_seconds() / 3600

    return None


def calculate_time_in_status(
    transitions: list[JiraStatusTransition],
) -> dict[str, float]:
    """Calculate total time (in hours) spent in each status.

    Returns dict mapping status name to hours spent.
    """
    time_in_status: dict[str, float] = {}

    for i in range(len(transitions) - 1):
        current = transitions[i]
        next_t = transitions[i + 1]

        try:
            start = datetime.fromisoformat(current.timestamp)
            end = datetime.fromisoformat(next_t.timestamp)
            hours = (end - start).total_seconds() / 3600

            status = current.to_status
            time_in_status[status] = time_in_status.get(status, 0) + hours
        except ValueError:
            continue

    return time_in_status
