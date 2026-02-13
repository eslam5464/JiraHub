import streamlit as st

from app.core.config import get_settings
from app.core.constants import UserRole
from app.core.logger import setup_logger
from app.services.auth_service import AuthService
from app.utils.async_helpers import run_async


def _init_db():
    """Ensure database directory and tables exist."""
    settings = get_settings()
    settings.db_directory.mkdir(parents=True, exist_ok=True)

    from app.models.base import Base
    from app.models.db import engine
    from app.models.ignored_issue_type import IgnoredIssueType  # noqa: F401
    from app.models.ignored_ticket import IgnoredTicket  # noqa: F401
    from app.models.session import Session  # noqa: F401
    from app.models.team_member import TeamMember  # noqa: F401
    from app.models.user import User  # noqa: F401
    from app.models.user_project import UserProject  # noqa: F401

    async def create_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    run_async(create_tables())


def main():
    settings = get_settings()
    setup_logger(debug=settings.debug)

    st.set_page_config(
        page_title=settings.app_name,
        page_icon="📋",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Initialize database
    _init_db()

    # Clean up expired sessions
    run_async(AuthService.cleanup_sessions())

    # Build navigation based on auth state
    from app.pages import (
        admin,
        dashboard,
        insights,
        jira_connect,
        login,
        member_detail,
        project_setup,
        register,
        settings as settings_page,
        ticket_detail,
    )

    is_authenticated = st.session_state.get("authenticated", False)
    user = st.session_state.get("user")

    # ── Restore session from cookie if not already authenticated ──
    if not is_authenticated:
        from app.utils.cookies import get_session_cookie

        cookie_token = get_session_cookie()
        if cookie_token:
            restored_user = run_async(AuthService.restore_session(cookie_token))
            if restored_user:
                st.session_state["authenticated"] = True
                st.session_state["user"] = restored_user.model_dump()
                st.session_state["session_token"] = cookie_token
                is_authenticated = True
                user = st.session_state["user"]

    has_jira = bool(user and user.get("jira_url"))
    is_admin = bool(user and user.get("role") == UserRole.ADMIN)

    # Check if user has projects configured
    has_projects = st.session_state.get("has_projects", False)
    if has_jira and not has_projects:
        from app.models.db import get_session_direct
        from app.repos.user_project import UserProjectRepo

        session = run_async(get_session_direct())
        try:
            repo = UserProjectRepo(session)
            active = run_async(repo.get_active_projects(user["id"])) if user else []
            has_projects = len(active) > 0
            st.session_state["has_projects"] = has_projects
        finally:
            run_async(session.close())

    if not is_authenticated:
        # Not logged in - show only login and register
        pages = {
            "Account": [
                st.Page(login.render, title="Login", icon="🔑", url_path="login"),
                st.Page(register.render, title="Register", icon="📝", url_path="register"),
            ]
        }
    elif not has_jira:
        # Logged in but no Jira connection
        pages = {
            "Setup": [
                st.Page(
                    jira_connect.render,
                    title="Connect Jira",
                    icon="🔗",
                    default=True,
                    url_path="jira-connect",
                ),
            ],
            "Account": [
                st.Page(
                    settings_page.render,
                    title="Settings",
                    icon="⚙️",
                    url_path="settings",
                ),
            ],
        }
        if is_admin:
            pages["Admin"] = [
                st.Page(admin.render, title="Admin Panel", icon="🛡️", url_path="admin"),
            ]
    elif not has_projects:
        # Jira connected but no projects selected
        pages = {
            "Setup": [
                st.Page(
                    project_setup.render,
                    title="Project Setup",
                    icon="📂",
                    default=True,
                    url_path="project-setup",
                ),
                st.Page(
                    jira_connect.render,
                    title="Connect Jira",
                    icon="🔗",
                    url_path="jira-connect",
                ),
            ],
            "Account": [
                st.Page(
                    settings_page.render,
                    title="Settings",
                    icon="⚙️",
                    url_path="settings",
                ),
            ],
        }
        if is_admin:
            pages["Admin"] = [
                st.Page(admin.render, title="Admin Panel", icon="🛡️", url_path="admin"),
            ]
    else:
        # Fully authenticated
        _member_detail_page = st.Page(
            member_detail.render,
            title="Member Detail",
            icon="👤",
            url_path="member-detail",
        )
        _ticket_detail_page = st.Page(
            ticket_detail.render,
            title="Ticket Detail",
            icon="🎫",
            url_path="ticket-detail",
        )
        st.session_state["_page_member_detail"] = _member_detail_page
        st.session_state["_page_ticket_detail"] = _ticket_detail_page

        pages = {
            "Dashboard": [
                st.Page(
                    dashboard.render,
                    title="Team Dashboard",
                    icon="📊",
                    default=True,
                    url_path="dashboard",
                ),
                _member_detail_page,
                _ticket_detail_page,
                st.Page(insights.render, title="Insights", icon="📈", url_path="insights"),
            ],
            "Setup": [
                st.Page(
                    project_setup.render,
                    title="Project Setup",
                    icon="📂",
                    url_path="project-setup",
                ),
                st.Page(
                    jira_connect.render,
                    title="Connect Jira",
                    icon="🔗",
                    url_path="jira-connect",
                ),
                st.Page(
                    settings_page.render,
                    title="Settings",
                    icon="⚙️",
                    url_path="settings",
                ),
            ],
        }
        if is_admin:
            pages["Admin"] = [
                st.Page(admin.render, title="Admin Panel", icon="🛡️", url_path="admin"),
            ]

    nav = st.navigation(pages)

    # Sidebar info
    if is_authenticated and user:
        # Ensure session cookie is set/refreshed on every authenticated page load
        from app.utils.cookies import set_session_cookie

        session_token = st.session_state.get("session_token")
        if session_token:
            set_session_cookie(session_token, settings.session_expiry_hours)

        with st.sidebar:
            st.markdown(f"**{user['email']}**")
            if user.get("jira_display_name"):
                st.caption(f"Jira: {user['jira_display_name']}")
            st.caption(f"Role: {user['role']}")

    nav.run()


if __name__ == "__main__":
    main()
