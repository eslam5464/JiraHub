from datetime import date, datetime, timezone

import pandas as pd
import streamlit as st
from loguru import logger

from app.core.config import get_settings
from app.core.exceptions.domain import JiraConnectionError
from app.models.db import get_session_direct
from app.repos.user_project import UserProjectRepo
from app.services.auth_service import AuthService
from app.services.cache import get_cache_service
from app.services.jira_client import JiraClient
from app.utils.async_helpers import run_async
from app.utils.metrics import (
    calculate_status_distribution,
    calculate_workload,
    get_missing_story_points,
    get_overdue_tickets,
)


def _get_jira_client() -> JiraClient | None:
    user = st.session_state.get("user")
    if not user or not user.get("jira_url"):
        return None
    try:
        jira_url, jira_email, token = run_async(AuthService.get_jira_token(user["id"]))
        settings = get_settings()
        return JiraClient(jira_url, jira_email, token, proxy_url=settings.proxy_url)
    except Exception:
        return None


def _load_project_data(
    client: JiraClient,
    user_email: str,
    project_key: str,
    board_ids: list[int],
    force_refresh: bool = False,
):
    """Load Jira data for a single project from cache or API."""
    cache = get_cache_service()

    # Try cache first
    if not force_refresh:
        cached_issues = run_async(cache.get_cached(user_email, "issues", project_key=project_key))
        cached_sp_field = run_async(
            cache.get_cached(user_email, "sp_field", project_key=project_key)
        )
        if cached_issues is not None:
            from app.schemas.jira.issue import JiraIssue

            issues = [JiraIssue.model_validate(i) for i in cached_issues]
            sp_field = cached_sp_field.get("field") if isinstance(cached_sp_field, dict) else None
            return issues, sp_field

    # Fetch from Jira - combine all async ops into a single coroutine
    # to avoid reusing httpx client across different event loops.
    user_id = st.session_state.get("user", {}).get("id", 1)

    async def _fetch():
        sp_field = None
        # Try each board to discover the story points field
        for bid in board_ids:
            try:
                config = await client.get_board_config(bid)
                sp_field = config.story_points_field
                if sp_field:
                    break
            except Exception:
                continue
        if sp_field:
            await cache.set_cached(
                user_email,
                "sp_field",
                {"field": sp_field},
                project_key=project_key,
            )

        jql = f"project = {project_key} AND assignee is not EMPTY ORDER BY updated DESC"

        fields = [
            "summary",
            "status",
            "assignee",
            "reporter",
            "issuetype",
            "priority",
            "duedate",
            "labels",
            "created",
            "updated",
            "resolutiondate",
            "parent",
            "issuelinks",
            "subtasks",
            "timetracking",
        ]
        if sp_field:
            fields.append(sp_field)

        # Auto-discover Team custom field and sprint field
        try:
            team_field_id = await client.discover_field_by_name("Team")
            if team_field_id:
                fields.append(team_field_id)
                await cache.set_cached(
                    user_email,
                    "team_field",
                    {"field": team_field_id},
                    project_key=project_key,
                )
        except Exception:
            pass

        # Sprint is usually a custom field; discover it
        try:
            sprint_field_id = await client.discover_field_by_name("Sprint")
            if sprint_field_id:
                fields.append(sprint_field_id)
                await cache.set_cached(
                    user_email,
                    "sprint_field",
                    {"field": sprint_field_id},
                    project_key=project_key,
                )
        except Exception:
            pass

        issues = await client.search_issues(jql, fields=fields, max_results=500)
        issues_data = [i.model_dump() for i in issues]
        await cache.set_cached(user_email, "issues", issues_data, project_key=project_key)

        # Auto-populate team members from issue assignees
        from app.models.db import get_session_direct as _get_session
        from app.repos.team_member import TeamMemberRepo
        from app.schemas.team_member import TeamMemberCreate

        seen_accounts: set[str] = set()
        tm_session = await _get_session()
        try:
            tm_repo = TeamMemberRepo(tm_session)
            for issue in issues:
                assignee = issue.fields.assignee
                if assignee and assignee.accountId and assignee.accountId not in seen_accounts:
                    seen_accounts.add(assignee.accountId)
                    await tm_repo.upsert(
                        TeamMemberCreate(
                            jira_account_id=assignee.accountId,
                            display_name=assignee.displayName,
                            email=assignee.emailAddress,
                            avatar_url=(
                                assignee.avatarUrls.get("48x48") if assignee.avatarUrls else None
                            ),
                            created_by=user_id,  # auto-populated by dashboard
                        )
                    )
        finally:
            await tm_session.close()

        now = datetime.now(timezone.utc).isoformat()
        await cache.set_last_refresh(user_email, now, project_key=project_key)

        return issues, sp_field

    with st.spinner(f"Fetching data for {project_key} from Jira..."):
        issues, sp_field = run_async(_fetch())

    return issues, sp_field


def _render_project_tab(
    client: JiraClient,
    user: dict,
    project_key: str,
    boards: list[dict],
    force_refresh: bool,
):
    """Render dashboard content for a single project inside its tab."""

    # ─── Board Filter ─────────────────────────────────────────────
    board_options = {b["name"]: b["id"] for b in boards}
    if len(boards) > 1:
        selected_board_names = st.multiselect(
            "Filter by Board",
            list(board_options.keys()),
            default=list(board_options.keys()),
            key=f"boards_{project_key}",
        )
        board_ids = [board_options[n] for n in selected_board_names]
    else:
        board_ids = [b["id"] for b in boards]

    if not board_ids:
        st.info("No boards selected.")
        return

    cache = get_cache_service()
    last_refresh = run_async(cache.get_last_refresh(user["email"], project_key=project_key))
    if last_refresh:
        st.caption(f"Last refreshed: {last_refresh[:19].replace('T', ' ')} UTC")

    try:
        issues, sp_field = _load_project_data(
            client, user["email"], project_key, board_ids, force_refresh
        )
    except JiraConnectionError as e:
        st.error(f"Failed to load Jira data for {project_key}: {e.message}")
        return
    except Exception as e:
        logger.exception("Error loading Jira data")
        st.error(f"Error loading data for {project_key}: {e}")
        return

    if not issues:
        st.info(f"No issues found for project {project_key}.")
        return

    # ─── Filters ──────────────────────────────────────────────────
    with st.expander("Filters", expanded=False):
        # --- Collect filter options from issues ---
        assignees = sorted({i.fields.assignee.displayName for i in issues if i.fields.assignee})
        statuses = sorted({i.fields.status.name for i in issues})
        all_issue_labels: set[str] = set()
        for i in issues:
            all_issue_labels.update(i.fields.labels or [])
        issue_label_options = sorted(all_issue_labels)

        # Load team member labels from DB
        from app.repos.team_member import TeamMemberRepo

        session = run_async(get_session_direct())
        try:
            tm_repo = TeamMemberRepo(session)
            all_team_members = run_async(tm_repo.get_all(limit=1000))
            label_map = {tm.display_name: tm.labels for tm in all_team_members}
            available_labels = sorted(
                {label for tm in all_team_members for label in (tm.labels or [])}
            )
        finally:
            run_async(session.close())

        # ── Row 1: Team Label + Assignee ──
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            selected_labels = st.multiselect(
                "Filter by Team Label",
                available_labels,
                key=f"labels_{project_key}",
            )
        with col_f2:
            selected_assignees = st.multiselect(
                "Filter by Assignee", assignees, key=f"assignees_{project_key}"
            )

        # ── Row 2: Status + Exclude Status ──
        col_f3, col_f4 = st.columns(2)
        with col_f3:
            selected_statuses = st.multiselect(
                "Filter by Status",
                statuses,
                key=f"statuses_{project_key}",
            )
        with col_f4:
            excluded_statuses = st.multiselect(
                "Exclude Status",
                statuses,
                key=f"exclude_statuses_{project_key}",
            )

        # ── Row 3: Jira Issue Labels ──
        col_f5a, col_f5b = st.columns(2)
        with col_f5a:
            combined_label_options = issue_label_options
            selected_issue_labels = st.multiselect(
                "Filter by Jira Issue Labels",
                combined_label_options,
                key=f"issue_labels_{project_key}",
            )

        # ── Row 4: Date Ranges ──
        # Compute min/max dates from issues for sensible defaults
        created_dates: list[date] = []
        due_dates: list[date] = []
        for i in issues:
            if i.fields.created:
                try:
                    created_dates.append(date.fromisoformat(i.fields.created[:10]))
                except ValueError:
                    pass
            if i.fields.duedate:
                try:
                    due_dates.append(date.fromisoformat(i.fields.duedate))
                except ValueError:
                    pass

        col_f5, col_f6 = st.columns(2)
        with col_f5:
            created_range = None
            if created_dates:
                created_range = st.date_input(
                    "Created Date Range",
                    value=(min(created_dates), max(created_dates)),
                    min_value=min(created_dates),
                    max_value=max(created_dates),
                    key=f"created_range_{project_key}",
                )
        with col_f6:
            due_range = None
            if due_dates:
                due_range = st.date_input(
                    "Due Date Range",
                    value=(min(due_dates), max(due_dates)),
                    min_value=min(due_dates),
                    max_value=max(due_dates),
                    key=f"due_range_{project_key}",
                )

    # ── Apply filters ─────────────────────────────────────────────

    # Team label filter
    if selected_labels:
        label_members = {
            name for name, labels in label_map.items() if any(l in labels for l in selected_labels)
        }
        issues = [
            i
            for i in issues
            if i.fields.assignee and i.fields.assignee.displayName in label_members
        ]

    # Assignee filter
    if selected_assignees:
        issues = [
            i
            for i in issues
            if i.fields.assignee and i.fields.assignee.displayName in selected_assignees
        ]

    # Status filter
    if selected_statuses:
        issues = [i for i in issues if i.fields.status.name in selected_statuses]

    # Exclude status filter
    if excluded_statuses:
        issues = [i for i in issues if i.fields.status.name not in excluded_statuses]

    # Jira issue labels filter
    if selected_issue_labels:
        issues = [
            i
            for i in issues
            if i.fields.labels and any(l in i.fields.labels for l in selected_issue_labels)
        ]

    # Created date range filter
    if created_range and isinstance(created_range, (list, tuple)) and len(created_range) == 2:
        cr_start, cr_end = created_range
        filtered = []
        for i in issues:
            if i.fields.created:
                try:
                    cr_date = date.fromisoformat(i.fields.created[:10])
                    if cr_start <= cr_date <= cr_end:
                        filtered.append(i)
                except ValueError:
                    filtered.append(i)
            else:
                filtered.append(i)
        issues = filtered

    # Due date range filter
    if due_range and isinstance(due_range, (list, tuple)) and len(due_range) == 2:
        dr_start, dr_end = due_range
        filtered = []
        for i in issues:
            if i.fields.duedate:
                try:
                    dr_date = date.fromisoformat(i.fields.duedate)
                    if dr_start <= dr_date <= dr_end:
                        filtered.append(i)
                except ValueError:
                    pass
            # Issues without a due date are excluded when a due-date range is active
        issues = filtered

    # Load ignored tickets/types
    from app.repos.ignored_issue_type import IgnoredIssueTypeRepo
    from app.repos.ignored_ticket import IgnoredTicketRepo

    session = run_async(get_session_direct())
    try:
        ignored_ticket_repo = IgnoredTicketRepo(session)
        ignored_type_repo = IgnoredIssueTypeRepo(session)
        ignored_keys = run_async(ignored_ticket_repo.get_ignored_keys(user["id"]))
        ignored_types = run_async(ignored_type_repo.get_ignored_types(user["id"]))
    finally:
        run_async(session.close())

    # Filter out ignored
    issues = [
        i
        for i in issues
        if i.key not in ignored_keys and i.fields.issuetype.name not in ignored_types
    ]

    # ─── Metrics ──────────────────────────────────────────────────
    st.markdown("---")

    total = len(issues)
    overdue = get_overdue_tickets(issues)
    missing_sp = get_missing_story_points(issues, sp_field)
    total_sp = sum(i.get_story_points(sp_field) or 0 for i in issues)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Tickets", total)
    col2.metric("Overdue", len(overdue))
    col3.metric("Missing Story Points", len(missing_sp))
    col4.metric("Total Story Points", f"{total_sp:.0f}")

    # ─── Workload Distribution ────────────────────────────────────
    st.markdown("---")
    st.subheader("Workload Distribution")

    workload = calculate_workload(issues, sp_field)
    if workload:
        df = pd.DataFrame.from_dict(workload, orient="index")
        df.index.name = "Assignee"
        df = df.sort_values("total_story_points", ascending=False)

        st.bar_chart(df[["total_story_points"]])
        st.dataframe(df, width="stretch")

    # ─── Status Distribution ─────────────────────────────────────
    st.markdown("---")
    st.subheader("Status Distribution")

    status_dist = calculate_status_distribution(issues)
    if status_dist:
        df_status = pd.DataFrame.from_dict(status_dist, orient="index").fillna(0).astype(int)
        df_status.index.name = "Assignee"
        st.bar_chart(df_status)

    # ─── Overdue Tickets ──────────────────────────────────────────
    if overdue:
        st.markdown("---")
        st.subheader(f"Overdue Tickets ({len(overdue)})")

        overdue_data = []
        for issue in overdue:
            overdue_data.append(
                {
                    "Key": issue.key,
                    "Summary": issue.fields.summary,
                    "Assignee": (
                        issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned"
                    ),
                    "Due Date": issue.fields.duedate,
                    "Status": issue.fields.status.name,
                    "Story Points": str(issue.get_story_points(sp_field) or "-"),
                }
            )

        st.dataframe(pd.DataFrame(overdue_data), width="stretch", hide_index=True)

    # ─── Missing Story Points ────────────────────────────────────
    if missing_sp:
        st.markdown("---")
        st.subheader(f"Tickets Missing Story Points ({len(missing_sp)})")

        missing_data = []
        for issue in missing_sp:
            missing_data.append(
                {
                    "Key": issue.key,
                    "Summary": issue.fields.summary,
                    "Assignee": (
                        issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned"
                    ),
                    "Status": issue.fields.status.name,
                    "Type": issue.fields.issuetype.name,
                }
            )

        st.dataframe(pd.DataFrame(missing_data), width="stretch", hide_index=True)

    # ─── All Filtered Tickets ────────────────────────────────────
    st.markdown("---")
    st.subheader(f"All Tickets ({len(issues)})")

    tickets_data = []
    for issue in issues:
        tickets_data.append(
            {
                "Key": issue.key,
                "Summary": issue.fields.summary,
                "Type": issue.fields.issuetype.name,
                "Status": issue.fields.status.name,
                "Priority": (issue.fields.priority.name if issue.fields.priority else "-"),
                "Assignee": (
                    issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned"
                ),
                "Reporter": (issue.fields.reporter.displayName if issue.fields.reporter else "-"),
                "Story Points": str(issue.get_story_points(sp_field) or "-"),
                "Labels": (", ".join(issue.fields.labels) if issue.fields.labels else "-"),
                "Due Date": issue.fields.duedate or "-",
                "Created": (issue.fields.created[:10] if issue.fields.created else "-"),
            }
        )

    if tickets_data:
        st.dataframe(
            pd.DataFrame(tickets_data),
            width="stretch",
            hide_index=True,
            height=500,
        )
    else:
        st.info("No tickets match the current filters.")


def render():
    st.title("Team Dashboard")

    user = st.session_state.get("user")
    if not user:
        st.error("Please log in first.")
        return

    client = _get_jira_client()
    if not client:
        st.warning("Please connect your Jira account first.")
        return

    # Load user's active projects
    session = run_async(get_session_direct())
    try:
        repo = UserProjectRepo(session)
        active_projects = run_async(repo.get_active_projects(user["id"]))
    finally:
        run_async(session.close())

    if not active_projects:
        st.info("No projects configured. Please go to **Project Setup** to select projects.")
        return

    # Global refresh button
    col1, col2 = st.columns([3, 1])
    with col2:
        force_refresh = st.button("Refresh All Projects", use_container_width=True)

    # Create tabs - one per project
    tab_labels = [f"{p.project_key}" for p in active_projects]
    tabs = st.tabs(tab_labels)

    for tab, project in zip(tabs, active_projects):
        with tab:
            # Per-project refresh
            pcol1, pcol2 = st.columns([3, 1])
            with pcol2:
                proj_refresh = st.button(
                    f"Refresh {project.project_key}",
                    key=f"refresh_{project.project_key}",
                )

            should_refresh = force_refresh or proj_refresh
            proj_boards = project.boards or []
            _render_project_tab(client, user, project.project_key, proj_boards, should_refresh)
