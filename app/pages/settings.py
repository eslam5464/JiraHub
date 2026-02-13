import streamlit as st

from app.models.db import get_session_direct
from app.repos.ignored_issue_type import IgnoredIssueTypeRepo
from app.repos.ignored_ticket import IgnoredTicketRepo
from app.repos.user_project import UserProjectRepo
from app.services.auth_service import AuthService
from app.services.cache import get_cache_service
from app.utils.async_helpers import run_async


def render():
    st.title("Settings")

    user = st.session_state.get("user")
    if not user:
        st.error("Please log in first.")
        return

    # ─── Jira Connection ──────────────────────────────────────────
    st.subheader("Jira Connection")
    if user.get("jira_url"):
        st.success(
            f"Connected to: **{user['jira_url']}** as **{user.get('jira_display_name', 'Unknown')}**"
        )
        if st.button("Reconnect Jira"):
            st.session_state["_navigate_to"] = "jira_connect"
            st.rerun()
    else:
        st.warning("Jira not connected.")
        if st.button("Connect Jira"):
            st.session_state["_navigate_to"] = "jira_connect"
            st.rerun()

    # ─── Ignored Issue Types ──────────────────────────────────────
    st.markdown("---")
    st.subheader("Ignored Issue Types")
    st.caption("Tickets of these types will be excluded from dashboard and metrics.")

    common_types = ["Epic", "Sub-task", "Story", "Bug", "Task", "Subtask"]

    session = run_async(get_session_direct())
    try:
        repo = IgnoredIssueTypeRepo(session)
        current_ignored = run_async(repo.get_ignored_types(user["id"]))
    finally:
        run_async(session.close())

    selected_types = st.multiselect(
        "Select issue types to ignore",
        common_types,
        default=list(current_ignored),
        key="ignored_types_select",
    )

    if st.button("Save Ignored Types"):
        session = run_async(get_session_direct())
        try:
            repo = IgnoredIssueTypeRepo(session)
            run_async(repo.set_ignored_types(user["id"], selected_types))
        finally:
            run_async(session.close())
        st.success("Ignored issue types updated.")

    # ─── Ignored Tickets ──────────────────────────────────────────
    st.markdown("---")
    st.subheader("Ignored Tickets")

    session = run_async(get_session_direct())
    try:
        repo = IgnoredTicketRepo(session)
        ignored_tickets = run_async(repo.get_by_user(user["id"]))
    finally:
        run_async(session.close())

    if ignored_tickets:
        for ticket in ignored_tickets:
            col1, col2, col3 = st.columns([2, 3, 1])
            col1.write(f"**{ticket.ticket_key}**")
            col2.write(ticket.reason or "No reason")
            if col3.button("Un-ignore", key=f"unignore_{ticket.ticket_key}"):
                session = run_async(get_session_direct())
                try:
                    repo = IgnoredTicketRepo(session)
                    run_async(repo.unignore(user["id"], ticket.ticket_key))
                finally:
                    run_async(session.close())
                st.rerun()
    else:
        st.caption("No ignored tickets.")

    # ─── Cache Management ─────────────────────────────────────────
    st.markdown("---")
    st.subheader("Cache Management")

    cache = get_cache_service()

    # Show per-project cache info
    session = run_async(get_session_direct())
    try:
        proj_repo = UserProjectRepo(session)
        active_projects = run_async(proj_repo.get_active_projects(user["id"]))
    finally:
        run_async(session.close())

    if active_projects:
        for proj in active_projects:
            last_refresh = run_async(
                cache.get_last_refresh(user["email"], project_key=proj.project_key)
            )
            col_p1, col_p2, col_p3 = st.columns([2, 3, 1])
            col_p1.write(f"**{proj.project_key}**")
            if last_refresh:
                col_p2.caption(f"Last refresh: {last_refresh[:19].replace('T', ' ')} UTC")
            else:
                col_p2.caption("Not refreshed yet")
            if col_p3.button("Clear", key=f"clear_cache_{proj.project_key}"):
                run_async(cache.invalidate(user["email"], "issues", project_key=proj.project_key))
                run_async(cache.invalidate(user["email"], "sp_field", project_key=proj.project_key))
                run_async(
                    cache.invalidate(user["email"], "last_refresh", project_key=proj.project_key)
                )
                st.success(f"Cache cleared for {proj.project_key}.")
                st.rerun()

    if st.button("Clear All Cached Data"):
        run_async(cache.invalidate_all(user["email"]))
        st.success("Cache cleared. Data will be re-fetched on next Dashboard visit.")

    # ─── Logout ───────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Session")

    if st.button("Logout", type="primary"):
        session_token = st.session_state.get("session_token")
        if session_token:
            run_async(AuthService.logout(session_token))

        # Clear browser cookie
        from app.utils.cookies import clear_session_cookie

        clear_session_cookie()

        # Clear session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]

        st.success("Logged out successfully.")
        st.rerun()
