import pandas as pd
import streamlit as st

from app.core.config import get_settings
from app.models.db import get_session_direct
from app.repos.ignored_issue_type import IgnoredIssueTypeRepo
from app.repos.ignored_ticket import IgnoredTicketRepo
from app.repos.user_project import UserProjectRepo
from app.services.auth_service import AuthService
from app.services.cache import get_cache_service
from app.services.jira_client import JiraClient
from app.utils.async_helpers import run_async
from app.utils.metrics import (
    calculate_cycle_time,
    calculate_time_in_status,
    get_missing_story_points,
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


def render():
    st.title("Insights & Analytics")

    user = st.session_state.get("user")
    if not user:
        st.error("Please log in first.")
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
        key="insights_project",
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

    if not cached_issues:
        st.info("No cached data. Please visit the Dashboard and load data first.")
        return

    from app.schemas.jira.issue import JiraIssue

    issues = [JiraIssue.model_validate(i) for i in cached_issues]
    sp_field = cached_sp_field.get("field") if isinstance(cached_sp_field, dict) else None

    # Exclude ignored
    session = run_async(get_session_direct())
    try:
        ignored_ticket_repo = IgnoredTicketRepo(session)
        ignored_type_repo = IgnoredIssueTypeRepo(session)
        ignored_keys = run_async(ignored_ticket_repo.get_ignored_keys(user["id"]))
        ignored_types = run_async(ignored_type_repo.get_ignored_types(user["id"]))
    finally:
        run_async(session.close())

    issues = [
        i
        for i in issues
        if i.key not in ignored_keys and i.fields.issuetype.name not in ignored_types
    ]

    if not issues:
        st.info("No issues to analyze.")
        return

    # ─── Story Point Coverage ─────────────────────────────────────
    st.subheader("Story Point Coverage")

    missing_sp = get_missing_story_points(issues, sp_field)
    total = len(issues)
    with_sp = total - len(missing_sp)
    coverage_pct = (with_sp / total * 100) if total > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("With Story Points", with_sp)
    col2.metric("Without Story Points", len(missing_sp))
    col3.metric("Coverage", f"{coverage_pct:.0f}%")

    # Per-member breakdown
    member_coverage: dict[str, dict[str, int]] = {}
    for issue in issues:
        name = issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned"
        if name not in member_coverage:
            member_coverage[name] = {"with_sp": 0, "without_sp": 0}
        if issue.get_story_points(sp_field) is not None:
            member_coverage[name]["with_sp"] += 1
        else:
            member_coverage[name]["without_sp"] += 1

    df_coverage = pd.DataFrame.from_dict(member_coverage, orient="index")
    df_coverage.index.name = "Assignee"
    df_coverage["coverage_%"] = (
        df_coverage["with_sp"] / (df_coverage["with_sp"] + df_coverage["without_sp"]) * 100
    ).round(0)
    st.dataframe(df_coverage.sort_values("coverage_%", ascending=True), width="stretch")

    # ─── Cycle Time Analysis ─────────────────────────────────────
    st.markdown("---")
    st.subheader("Cycle Time Analysis")
    st.caption(
        "Select issues to analyze their status transitions. This makes API calls to Jira for changelog data."
    )

    client = _get_jira_client()
    if not client:
        st.warning("Jira connection required for cycle time analysis.")
        return

    # Select issues for analysis (limit to avoid API overload)
    done_issues = [i for i in issues if i.fields.status.name in {"Done", "Closed", "Resolved"}]

    if not done_issues:
        st.info("No completed issues to analyze cycle time.")
        return

    max_analyze = st.slider("Number of recent issues to analyze", 5, min(50, len(done_issues)), 10)

    if st.button("Analyze Cycle Time"):
        cycle_times: dict[str, list[float]] = {}
        time_in_status_totals: dict[str, float] = {}

        progress = st.progress(0)
        for idx, issue in enumerate(done_issues[:max_analyze]):
            try:
                transitions = run_async(client.get_status_transitions(issue.key))
                ct = calculate_cycle_time(transitions)
                tis = calculate_time_in_status(transitions)

                assignee = (
                    issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned"
                )
                if assignee not in cycle_times:
                    cycle_times[assignee] = []
                if ct is not None:
                    cycle_times[assignee].append(ct)

                for status_name, hours in tis.items():
                    time_in_status_totals[status_name] = (
                        time_in_status_totals.get(status_name, 0) + hours
                    )

            except Exception:
                continue
            finally:
                progress.progress((idx + 1) / max_analyze)

        # Display cycle time per member
        if cycle_times:
            st.markdown("**Average Cycle Time per Member (hours)**")
            ct_data = {
                name: {
                    "avg_hours": round(sum(times) / len(times), 1),
                    "min_hours": round(min(times), 1),
                    "max_hours": round(max(times), 1),
                    "issues_analyzed": len(times),
                }
                for name, times in cycle_times.items()
                if times
            }
            if ct_data:
                df_ct = pd.DataFrame.from_dict(ct_data, orient="index")
                df_ct.index.name = "Assignee"
                st.dataframe(df_ct, width="stretch")

        # Display time in status
        if time_in_status_totals:
            st.markdown("**Total Time in Each Status (hours)**")
            df_tis = pd.DataFrame(
                [{"Status": k, "Hours": round(v, 1)} for k, v in time_in_status_totals.items()]
            )
            df_tis = df_tis.sort_values("Hours", ascending=False)
            st.bar_chart(df_tis.set_index("Status"))
