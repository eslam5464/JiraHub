"""Ticket Detail page — shows comprehensive info for a single Jira issue."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.core.config import get_settings
from app.schemas.jira.issue import (
    JiraIssue,
    JiraWorklogResponse,
)
from app.services.auth_service import AuthService
from app.services.cache import get_cache_service
from app.services.jira_client import JiraClient
from app.utils.async_helpers import run_async

# ─── Helpers ──────────────────────────────────────────────────────────


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


def _seconds_to_human(seconds: int | None) -> str:
    if not seconds:
        return "-"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours and minutes:
        return f"{hours}h {minutes}m"
    if hours:
        return f"{hours}h"
    return f"{minutes}m"


def _get_sprint_name(issue: JiraIssue, sprint_field: str | None) -> str:
    """Extract sprint name from issue, trying cached custom field first."""
    if sprint_field:
        raw = getattr(issue.fields, sprint_field, None)
        if raw:
            if isinstance(raw, list) and raw:
                return raw[-1].get("name", "-")
            if isinstance(raw, dict):
                return raw.get("name", "-")
    sprint_obj = issue.get_sprint()
    if sprint_obj and sprint_obj.name:
        return sprint_obj.name
    return "-"


def _get_team_tag(issue: JiraIssue, team_field: str | None) -> str:
    """Extract team tag custom field value."""
    if not team_field:
        return "-"
    raw = getattr(issue.fields, team_field, None)
    if not raw:
        return "-"
    # May be a dict with "value" key or a plain string
    if isinstance(raw, dict):
        return raw.get("value", raw.get("name", str(raw)))
    if isinstance(raw, str):
        return raw
    return str(raw)


# ─── Main Render ──────────────────────────────────────────────────────


def render():
    st.title("Ticket Detail")

    user = st.session_state.get("user")
    if not user:
        st.error("Please log in first.")
        return

    ticket_key = st.session_state.get("detail_ticket_key")
    project_key = st.session_state.get("detail_project_key")

    if not ticket_key:
        st.info("No ticket selected. Please go to **Member Detail** and select a ticket.")
        return

    client = _get_jira_client()
    if not client:
        st.warning("Please connect your Jira account first.")
        return

    # ── Load cached field IDs ───────────────────────────────────────
    cache = get_cache_service()
    pk = project_key or ""

    cached_sp_field = run_async(cache.get_cached(user["email"], "sp_field", project_key=pk))
    cached_sprint_field = run_async(cache.get_cached(user["email"], "sprint_field", project_key=pk))
    cached_team_field = run_async(cache.get_cached(user["email"], "team_field", project_key=pk))
    sp_field = cached_sp_field.get("field") if isinstance(cached_sp_field, dict) else None
    sprint_field = (
        cached_sprint_field.get("field") if isinstance(cached_sprint_field, dict) else None
    )
    team_field = cached_team_field.get("field") if isinstance(cached_team_field, dict) else None

    # ── Fetch full issue detail ─────────────────────────────────────
    detail_fields = [
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
        detail_fields.append(sp_field)
    if sprint_field:
        detail_fields.append(sprint_field)
    if team_field:
        detail_fields.append(team_field)

    try:
        issue = run_async(client.get_issue(ticket_key, fields=detail_fields))
    except Exception as exc:
        st.error(f"Failed to load ticket {ticket_key}: {exc}")
        return

    # ── Header ──────────────────────────────────────────────────────
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.subheader(f"{issue.key}: {issue.fields.summary}")
    with col_h2:
        jira_url = user.get("jira_url", "").rstrip("/")
        if jira_url:
            st.link_button("Open in Jira", f"{jira_url}/browse/{issue.key}")

    st.markdown("---")

    # ── Core Info ───────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Status", issue.fields.status.name)
    c2.metric("Type", issue.fields.issuetype.name)
    c3.metric("Priority", issue.fields.priority.name if issue.fields.priority else "-")
    sp = issue.get_story_points(sp_field)
    c4.metric("Story Points", sp if sp is not None else "-")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Assignee", issue.fields.assignee.displayName if issue.fields.assignee else "-")
    c6.metric("Reporter", issue.fields.reporter.displayName if issue.fields.reporter else "-")
    c7.metric("Due Date", issue.fields.duedate or "-")
    c8.metric("Sprint", _get_sprint_name(issue, sprint_field))

    # ── Labels & Team Tag ───────────────────────────────────────────
    labels_col, team_col = st.columns(2)
    with labels_col:
        if issue.fields.labels:
            st.markdown("**Labels:** " + ", ".join(f"`{l}`" for l in issue.fields.labels))
        else:
            st.markdown("**Labels:** -")
    with team_col:
        st.markdown(f"**Team Tag:** {_get_team_tag(issue, team_field)}")

    # ── Dates ───────────────────────────────────────────────────────
    st.markdown("---")
    d1, d2, d3 = st.columns(3)
    d1.markdown(f"**Created:** {issue.fields.created or '-'}")
    d2.markdown(f"**Updated:** {issue.fields.updated or '-'}")
    d3.markdown(f"**Resolved:** {issue.fields.resolutiondate or '-'}")

    # ── Parent Ticket ───────────────────────────────────────────────
    if issue.fields.parent:
        st.markdown("---")
        st.subheader("Parent Ticket")
        parent = issue.fields.parent
        parent_summary = parent.fields.summary if parent.fields else "-"
        parent_status = parent.fields.status.name if parent.fields and parent.fields.status else "-"
        pc1, pc2, pc3 = st.columns(3)
        pc1.markdown(f"**Key:** {parent.key}")
        pc2.markdown(f"**Summary:** {parent_summary}")
        pc3.markdown(f"**Status:** {parent_status}")

    # ── Time Tracking ───────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Time Tracking")
    tt = issue.fields.timetracking
    if tt:
        tc1, tc2, tc3 = st.columns(3)
        tc1.metric("Original Estimate", tt.originalEstimate or "-")
        tc2.metric("Time Spent", tt.timeSpent or "-")
        tc3.metric("Remaining", tt.remainingEstimate or "-")
    else:
        st.caption("No time tracking data for this ticket.")

    # ── On-demand Worklogs ──────────────────────────────────────────
    st.markdown("---")
    st.subheader("Worklogs (Time Logged Per Person)")
    if st.button("Load Worklogs", key="load_worklogs"):
        _render_worklogs(client, ticket_key)

    # ── Linked Issues ───────────────────────────────────────────────
    if issue.fields.issuelinks:
        st.markdown("---")
        st.subheader("Linked Issues")
        link_data = []
        for link in issue.fields.issuelinks:
            link.type.name if link.type else "-"
            if link.outwardIssue:
                direction = link.type.outward if link.type else "relates to"
                ref = link.outwardIssue
            elif link.inwardIssue:
                direction = link.type.inward if link.type else "relates to"
                ref = link.inwardIssue
            else:
                continue
            ref_summary = ref.fields.summary if ref.fields else "-"
            ref_status = ref.fields.status.name if ref.fields and ref.fields.status else "-"
            link_data.append(
                {
                    "Relationship": direction,
                    "Key": ref.key,
                    "Summary": ref_summary,
                    "Status": ref_status,
                }
            )
        if link_data:
            st.dataframe(pd.DataFrame(link_data), width="stretch", hide_index=True)

    # ── Subtasks ────────────────────────────────────────────────────
    if issue.fields.subtasks:
        st.markdown("---")
        st.subheader("Subtasks")
        sub_data = []
        for sub in issue.fields.subtasks:
            sub_summary = sub.fields.summary if sub.fields else "-"
            sub_status = sub.fields.status.name if sub.fields and sub.fields.status else "-"
            sub_type = sub.fields.issuetype.name if sub.fields and sub.fields.issuetype else "-"
            sub_data.append(
                {
                    "Key": sub.key,
                    "Summary": sub_summary,
                    "Status": sub_status,
                    "Type": sub_type,
                }
            )
        st.dataframe(pd.DataFrame(sub_data), width="stretch", hide_index=True)

    # ── Back button ─────────────────────────────────────────────────
    st.markdown("---")
    if st.button("← Back to Member Detail"):
        st.switch_page(st.session_state["_page_member_detail"])


# ─── Worklog rendering ───────────────────────────────────────────────


def _render_worklogs(client: JiraClient, issue_key: str):
    """Fetch and display worklogs grouped by author."""
    try:
        worklog_resp: JiraWorklogResponse = run_async(client.get_issue_worklogs(issue_key))
    except Exception as exc:
        st.error(f"Failed to load worklogs: {exc}")
        return

    worklogs = worklog_resp.worklogs
    if not worklogs:
        st.caption("No worklogs recorded for this ticket.")
        return

    # Group by author
    author_totals: dict[str, int] = {}
    entries_by_author: dict[str, list[dict]] = {}

    for wl in worklogs:
        author_name = wl.author.displayName if wl.author and wl.author.displayName else "Unknown"
        seconds = wl.timeSpentSeconds or 0
        author_totals[author_name] = author_totals.get(author_name, 0) + seconds
        entries_by_author.setdefault(author_name, []).append(
            {
                "Date": wl.started or wl.created or "-",
                "Time Spent": wl.timeSpent or "-",
                "Seconds": seconds,
            }
        )

    # Summary table
    summary_data = [
        {
            "Contributor": name,
            "Total Time": _seconds_to_human(total),
            "Entries": len(entries_by_author.get(name, [])),
        }
        for name, total in sorted(author_totals.items(), key=lambda x: -x[1])
    ]
    st.markdown("**Summary by contributor:**")
    st.dataframe(pd.DataFrame(summary_data), width="stretch", hide_index=True)

    # Detail per author (expandable)
    for author_name, entries in entries_by_author.items():
        with st.expander(f"{author_name} — {_seconds_to_human(author_totals[author_name])}"):
            st.dataframe(pd.DataFrame(entries), width="stretch", hide_index=True)
