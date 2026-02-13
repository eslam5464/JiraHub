import streamlit as st

from app.core.config import get_settings
from app.models.db import get_session_direct
from app.repos.user_project import UserProjectRepo
from app.services.auth_service import AuthService
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
    st.title("Project Setup")
    st.markdown("Select the Jira projects you want to track on your dashboard.")

    user = st.session_state.get("user")
    if not user:
        st.error("Please log in first.")
        return

    client = _get_jira_client()
    if not client:
        st.warning("Please connect your Jira account first.")
        return

    # ─── Fetch available boards from Jira ─────────────────────────
    @st.cache_data(ttl=300, show_spinner=False)
    def fetch_boards(_user_id: int):
        """Fetch all boards from Jira (cached for 5 min)."""
        boards = run_async(client.get_boards())
        return [b.model_dump() for b in boards]

    with st.spinner("Loading boards from Jira..."):
        try:
            boards_data = fetch_boards(user["id"])
        except Exception as e:
            st.error(f"Failed to fetch boards from Jira: {e}")
            return

    if not boards_data:
        st.warning("No boards found in your Jira instance.")
        return

    # Group boards by project
    projects: dict[str, list[dict]] = {}
    for board in boards_data:
        loc = board.get("location") or {}
        project_key = loc.get("projectKey")
        project_name = loc.get("name") or loc.get("displayName") or project_key
        if not project_key:
            continue
        if project_key not in projects:
            projects[project_key] = []
        projects[project_key].append(
            {
                "board_id": board["id"],
                "board_name": board["name"],
                "project_key": project_key,
                "project_name": project_name,
            }
        )

    if not projects:
        st.warning("No boards with project associations found.")
        return

    # ─── Load currently selected projects ─────────────────────────
    session = run_async(get_session_direct())
    try:
        repo = UserProjectRepo(session)
        current_projects = run_async(repo.get_active_projects(user["id"]))
        current_keys = {p.project_key for p in current_projects}
    finally:
        run_async(session.close())

    # ─── Project selection ────────────────────────────────────────
    st.subheader("Available Projects")

    # Build selection options: "KEY - Project Name"
    options = sorted(projects.keys())
    option_labels = {key: f"{key} - {projects[key][0]['project_name']}" for key in options}

    selected_keys = st.multiselect(
        "Select projects to track",
        options=options,
        default=[k for k in options if k in current_keys],
        format_func=lambda k: option_labels[k],
    )

    # For each selected project, let user pick boards (multiselect)
    selected_projects: list[dict] = []
    for key in selected_keys:
        project_boards = projects[key]
        board_options = {b["board_id"]: b["board_name"] for b in project_boards}

        # Find previously selected board IDs for this project
        prev_board_ids: list[int] = []
        for cp in current_projects:
            if cp.project_key == key:
                prev_board_ids = [b["id"] for b in (cp.boards or [])]
                break

        if len(project_boards) == 1:
            # Only one board - auto-select it
            chosen_ids = [project_boards[0]["board_id"]]
        else:
            st.markdown(f"**{key}** - select boards to track:")
            default_ids = [bid for bid in prev_board_ids if bid in board_options] or list(
                board_options.keys()
            )[:1]
            chosen_ids = st.multiselect(
                f"Boards for {key}",
                options=list(board_options.keys()),
                default=default_ids,
                format_func=lambda bid, _opts=board_options: _opts.get(bid, str(bid)),
                key=f"board_select_{key}",
            )

        if chosen_ids:
            boards_list = [{"id": bid, "name": board_options[bid]} for bid in chosen_ids]
            selected_projects.append(
                {
                    "project_key": key,
                    "project_name": project_boards[0]["project_name"],
                    "boards": boards_list,
                }
            )

    # ─── Save selection ───────────────────────────────────────────
    st.markdown("---")
    if st.button("Save Project Selection", use_container_width=True, type="primary"):
        if not selected_projects:
            st.warning("Please select at least one project.")
            return

        session = run_async(get_session_direct())
        try:
            repo = UserProjectRepo(session)
            saved = run_async(repo.set_active_projects(user["id"], selected_projects))
        finally:
            run_async(session.close())

        st.session_state["has_projects"] = True
        project_keys = sorted({p.project_key for p in saved})
        st.success(f"Saved {len(project_keys)} project(s): {', '.join(project_keys)}")
        st.rerun()

    # ─── Current selection summary ────────────────────────────────
    if current_projects:
        st.markdown("---")
        st.subheader("Currently Tracked Projects")
        for proj in current_projects:
            board_names = ", ".join(b["name"] for b in (proj.boards or []))
            st.markdown(f"- **{proj.project_key}** - {proj.project_name} (Boards: {board_names})")
