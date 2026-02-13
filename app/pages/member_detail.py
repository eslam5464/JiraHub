from datetime import date

import pandas as pd
import streamlit as st

from app.core.config import get_settings
from app.models.db import get_session_direct
from app.repos.ignored_issue_type import IgnoredIssueTypeRepo
from app.repos.ignored_ticket import IgnoredTicketRepo
from app.repos.user_project import UserProjectRepo
from app.schemas.settings import IgnoredTicketCreate
from app.services.auth_service import AuthService
from app.services.cache import get_cache_service
from app.services.jira_client import JiraClient
from app.utils.async_helpers import run_async


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


def render():
    st.title("Member Detail")

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
        proj_repo = UserProjectRepo(session)
        active_projects = run_async(proj_repo.get_active_projects(user["id"]))
    finally:
        run_async(session.close())

    if not active_projects:
        st.info("No projects configured. Please go to **Project Setup** first.")
        return

    # Project selector
    project_options = {p.project_key: p for p in active_projects}
    selected_project_key = st.selectbox(
        "Select Project",
        list(project_options.keys()),
        key="member_detail_project",
    )

    if not selected_project_key:
        return

    # Load cached issues for selected project
    cache = get_cache_service()
    cached_issues = run_async(
        cache.get_cached(user["email"], "issues", project_key=selected_project_key)
    )
    cached_sp_field = run_async(
        cache.get_cached(user["email"], "sp_field", project_key=selected_project_key)
    )
    cached_sprint_field = run_async(
        cache.get_cached(user["email"], "sprint_field", project_key=selected_project_key)
    )

    if not cached_issues:
        st.info("No cached data. Please visit the Dashboard and load data first.")
        return

    from app.schemas.jira.issue import JiraIssue

    issues = [JiraIssue.model_validate(i) for i in cached_issues]
    sp_field = cached_sp_field.get("field") if isinstance(cached_sp_field, dict) else None
    sprint_field = (
        cached_sprint_field.get("field") if isinstance(cached_sprint_field, dict) else None
    )

    # Get unique assignees
    assignees = sorted({i.fields.assignee.displayName for i in issues if i.fields.assignee})

    if not assignees:
        st.info("No assigned tickets found.")
        return

    selected_member = st.selectbox("Select Team Member", assignees)

    if not selected_member:
        return

    # Filter issues for selected member
    member_issues = [
        i for i in issues if i.fields.assignee and i.fields.assignee.displayName == selected_member
    ]

    # Load ignored data
    session = run_async(get_session_direct())
    try:
        ignored_ticket_repo = IgnoredTicketRepo(session)
        ignored_type_repo = IgnoredIssueTypeRepo(session)
        ignored_keys = run_async(ignored_ticket_repo.get_ignored_keys(user["id"]))
        ignored_types = run_async(ignored_type_repo.get_ignored_types(user["id"]))
    finally:
        run_async(session.close())

    # Show/hide ignored toggle
    show_ignored = st.toggle("Show ignored tickets", value=False)

    # Build table data
    today = date.today()
    done_statuses = {"Done", "Closed", "Resolved"}
    table_data = []

    for issue in member_issues:
        is_ignored = issue.key in ignored_keys or issue.fields.issuetype.name in ignored_types

        if not show_ignored and is_ignored:
            continue

        is_overdue = False
        if issue.fields.duedate and issue.fields.status.name not in done_statuses:
            try:
                is_overdue = date.fromisoformat(issue.fields.duedate) < today
            except ValueError:
                pass

        sp = issue.get_story_points(sp_field)
        has_sp = sp is not None

        # Extract sprint name
        sprint_name = "-"
        if sprint_field:
            raw_sprint = getattr(issue.fields, sprint_field, None)
            if raw_sprint:
                if isinstance(raw_sprint, list) and raw_sprint:
                    sprint_name = raw_sprint[-1].get("name", "-")
                elif isinstance(raw_sprint, dict):
                    sprint_name = raw_sprint.get("name", "-")
        else:
            sprint_obj = issue.get_sprint()
            if sprint_obj and sprint_obj.name:
                sprint_name = sprint_obj.name

        status_icon = ""
        if is_ignored:
            status_icon = "⬜"
        elif is_overdue:
            status_icon = "🔴"
        elif not has_sp:
            status_icon = "🟡"
        else:
            status_icon = "🟢"

        table_data.append(
            {
                "": status_icon,
                "Key": issue.key,
                "Summary": issue.fields.summary,
                "Status": issue.fields.status.name,
                "Story Points": str(sp) if sp is not None else "-",
                "Due Date": issue.fields.duedate or "-",
                "Priority": (issue.fields.priority.name if issue.fields.priority else "-"),
                "Type": issue.fields.issuetype.name,
                "Labels": (", ".join(issue.fields.labels) if issue.fields.labels else "-"),
                "Sprint": sprint_name,
                "Reporter": (issue.fields.reporter.displayName if issue.fields.reporter else "-"),
                "Ignored": "Yes" if is_ignored else "",
            }
        )

    if not table_data:
        st.info(f"No tickets found for {selected_member}.")
        return

    # Summary metrics
    active_issues = [
        i
        for i in member_issues
        if i.key not in ignored_keys and i.fields.issuetype.name not in ignored_types
    ]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Tickets", len(active_issues))
    col2.metric(
        "Story Points",
        f"{sum(i.get_story_points(sp_field) or 0 for i in active_issues):.0f}",
    )
    overdue_count = sum(
        1
        for i in active_issues
        if i.fields.duedate
        and i.fields.status.name not in done_statuses
        and _is_overdue(i.fields.duedate)
    )
    col3.metric("Overdue", overdue_count)
    col4.metric(
        "Missing SP",
        sum(1 for i in active_issues if i.get_story_points(sp_field) is None),
    )

    # Display table
    st.markdown("---")
    st.markdown("**Legend:** 🔴 Overdue | 🟡 Missing Story Points | 🟢 OK | ⬜ Ignored")

    df = pd.DataFrame(table_data)
    st.dataframe(df, width="stretch", hide_index=True)

    # View ticket detail
    st.markdown("---")
    st.subheader("View Ticket Detail")
    ticket_keys = [row["Key"] for row in table_data]
    selected_ticket = st.selectbox(
        "Select a ticket to view details",
        ticket_keys,
        key="view_detail_select",
    )
    if st.button("View Detail", key="view_detail_btn"):
        if selected_ticket:
            st.session_state["detail_ticket_key"] = selected_ticket
            st.session_state["detail_project_key"] = selected_project_key
            st.switch_page(st.session_state["_page_ticket_detail"])

    # Ignore/unignore controls
    st.markdown("---")
    st.subheader("Manage Ignored Tickets")

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("**Ignore a ticket:**")
        ticket_to_ignore = st.selectbox(
            "Select ticket to ignore",
            [i.key for i in member_issues if i.key not in ignored_keys],
            key="ignore_select",
        )
        ignore_reason = st.text_input("Reason (optional)", key="ignore_reason")
        if st.button("Ignore Ticket", key="ignore_btn"):
            if ticket_to_ignore:
                session = run_async(get_session_direct())
                try:
                    repo = IgnoredTicketRepo(session)
                    run_async(
                        repo.create_one(
                            IgnoredTicketCreate(
                                user_id=user["id"],
                                ticket_key=ticket_to_ignore,
                                reason=ignore_reason or None,
                            )
                        )
                    )
                finally:
                    run_async(session.close())
                st.success(f"Ticket {ticket_to_ignore} ignored.")
                st.rerun()

    with col_b:
        st.markdown("**Un-ignore a ticket:**")
        if ignored_keys:
            member_ignored = [k for k in ignored_keys if any(i.key == k for i in member_issues)]
            ticket_to_unignore = st.selectbox(
                "Select ticket to un-ignore",
                member_ignored,
                key="unignore_select",
            )
            if st.button("Un-ignore Ticket", key="unignore_btn"):
                if ticket_to_unignore:
                    session = run_async(get_session_direct())
                    try:
                        repo = IgnoredTicketRepo(session)
                        run_async(repo.unignore(user["id"], ticket_to_unignore))
                    finally:
                        run_async(session.close())
                    st.success(f"Ticket {ticket_to_unignore} un-ignored.")
                    st.rerun()
        else:
            st.caption("No ignored tickets for this member.")


def _is_overdue(duedate_str: str) -> bool:
    try:
        return date.fromisoformat(duedate_str) < date.today()
    except ValueError:
        return False
