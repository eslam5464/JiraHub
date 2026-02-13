import streamlit as st

from app.core.constants import UserRole
from app.models.db import get_session_direct
from app.repos.team_member import TeamMemberRepo
from app.schemas.team_member import TeamMemberCreate, TeamMemberUpdate
from app.services.auth_service import AuthService
from app.utils.async_helpers import run_async


def render():
    st.title("Admin Panel")

    user = st.session_state.get("user")
    if not user or user.get("role") != UserRole.ADMIN:
        st.error("You do not have permission to access this page.")
        return

    tab1, tab2 = st.tabs(["User Management", "Team Member Labels"])

    with tab1:
        _render_user_management(user)

    with tab2:
        _render_team_labels(user)


def _render_user_management(user: dict):
    st.subheader("Pending Approvals")

    pending_users = run_async(AuthService.get_pending_users())

    if pending_users:
        for pu in pending_users:
            col1, col2, col3 = st.columns([3, 1, 1])
            col1.write(f"**{pu.email}** - registered {pu.created_at.strftime('%Y-%m-%d %H:%M')}")
            if col2.button("Approve", key=f"approve_{pu.id}"):
                run_async(AuthService.approve_user(pu.id))
                st.success(f"Approved {pu.email}")
                st.rerun()
            if col3.button("Reject", key=f"reject_{pu.id}"):
                run_async(AuthService.reject_user(pu.id))
                st.warning(f"Rejected {pu.email}")
                st.rerun()
    else:
        st.caption("No pending users.")

    st.markdown("---")
    st.subheader("All Users")

    all_users = run_async(AuthService.get_all_users())

    for u in all_users:
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        col1.write(f"**{u.email}** - {u.role} - {u.status}")
        col2.write(f"Jira: {'Connected' if u.jira_url else 'Not connected'}")
        if u.id != user["id"]:
            if col3.button("Delete", key=f"delete_{u.id}"):
                run_async(AuthService.delete_user(u.id))
                st.warning(f"Deleted {u.email}")
                st.rerun()
        else:
            col3.caption("(you)")


def _render_team_labels(user: dict):
    st.subheader("Team Member Labels")
    st.caption(
        "Assign labels (e.g., backend, frontend, devops, PM) to team members. "
        "Labels are used for filtering on the Dashboard."
    )

    # Load team members
    session = run_async(get_session_direct())
    try:
        repo = TeamMemberRepo(session)
        members = run_async(repo.get_all(limit=1000))
    finally:
        run_async(session.close())

    if not members:
        st.info(
            "No team members found. Team members are auto-populated when you load data on the Dashboard. "
            "You can also add them manually below."
        )

    # Show existing members with label editor
    for member in members:
        with st.expander(f"{member.display_name} ({member.email or 'No email'})"):
            current_labels = member.labels or []
            default_label_options = [
                "backend",
                "frontend",
                "devops",
                "qa",
                "pm",
                "design",
                "mobile",
                "data",
            ]

            new_labels = st.multiselect(
                "Labels",
                default_label_options,
                default=[l for l in current_labels if l in default_label_options],
                key=f"labels_{member.id}",
            )

            # Allow custom labels
            custom_label = st.text_input(
                "Add custom label",
                key=f"custom_label_{member.id}",
                placeholder="e.g., team-alpha",
            )

            if st.button("Save Labels", key=f"save_labels_{member.id}"):
                final_labels = list(set(new_labels + ([custom_label] if custom_label else [])))
                session = run_async(get_session_direct())
                try:
                    repo = TeamMemberRepo(session)
                    run_async(
                        repo.update_by_id(
                            member.id,
                            TeamMemberUpdate(labels=final_labels),
                        )
                    )
                finally:
                    run_async(session.close())
                st.success(f"Labels updated for {member.display_name}")
                st.rerun()

    # Add member manually
    st.markdown("---")
    st.subheader("Add Team Member Manually")

    with st.form("add_member_form"):
        jira_account_id = st.text_input(
            "Jira Account ID", placeholder="e.g., 5b10ac8d82e05b22cc7d4ef5"
        )
        display_name = st.text_input("Display Name")
        member_email = st.text_input("Email (optional)")
        labels_input = st.text_input("Labels (comma-separated)", placeholder="backend, devops")
        submitted = st.form_submit_button("Add Member")

    if submitted:
        if not jira_account_id or not display_name:
            st.error("Jira Account ID and Display Name are required.")
            return

        labels = (
            [l.strip().lower() for l in labels_input.split(",") if l.strip()]
            if labels_input
            else []
        )

        session = run_async(get_session_direct())
        try:
            repo = TeamMemberRepo(session)
            run_async(
                repo.upsert(
                    TeamMemberCreate(
                        jira_account_id=jira_account_id,
                        display_name=display_name,
                        email=member_email or None,
                        labels=labels,
                        created_by=user["id"],
                    )
                )
            )
        finally:
            run_async(session.close())

        st.success(f"Team member '{display_name}' added.")
        st.rerun()
