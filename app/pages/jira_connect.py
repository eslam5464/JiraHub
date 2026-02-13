import streamlit as st
from loguru import logger

from app.core.config import get_settings
from app.core.exceptions.domain import JiraAuthenticationError, JiraConnectionError
from app.services.auth_service import AuthService
from app.services.jira_client import JiraClient
from app.utils.async_helpers import run_async


def render():
    st.title("Connect to Jira")
    st.markdown("Enter your Jira Cloud credentials to connect your account.")

    user = st.session_state.get("user")
    if not user:
        st.error("Please log in first.")
        return

    # Show current connection status
    if user.get("jira_url"):
        st.info(
            f"Currently connected to: **{user['jira_url']}** as **{user.get('jira_display_name', 'Unknown')}**"
        )
        st.markdown("---")
        st.markdown("Update your Jira credentials below if needed:")

    with st.form("jira_connect_form"):
        jira_url = st.text_input(
            "Jira Cloud URL",
            value=user.get("jira_url", ""),
            placeholder="https://yourteam.atlassian.net",
            help="Your Jira Cloud instance URL (e.g., https://yourteam.atlassian.net)",
        )
        jira_email = st.text_input(
            "Jira Account Email",
            value=user.get("email", ""),
            help="The email address associated with your Atlassian/Jira account",
        )
        jira_token = st.text_input(
            "API Token",
            type="password",
            placeholder="Your Jira API token",
            help="Generate at https://id.atlassian.com/manage-profile/security/api-tokens",
        )
        submitted = st.form_submit_button("Connect", use_container_width=True)

    if submitted:
        if not jira_url or not jira_token or not jira_email:
            st.error("All fields are required.")
            return

        # Normalize URL
        jira_url = jira_url.rstrip("/")
        if not jira_url.startswith("https://"):
            st.error("Jira URL must start with https://")
            return

        with st.spinner("Validating Jira credentials..."):
            try:
                # Validate + store in a single async context to avoid event loop issues
                async def _connect():
                    settings = get_settings()
                    client = JiraClient(
                        jira_url, jira_email, jira_token, proxy_url=settings.proxy_url
                    )
                    try:
                        jira_user = await client.get_myself()
                    finally:
                        await client.close()

                    # Store encrypted credentials
                    updated_user = await AuthService.connect_jira(
                        user["id"], jira_url, jira_email, jira_token
                    )

                    # Update Jira profile info
                    await AuthService.update_jira_profile(
                        user["id"],
                        jira_user.displayName,
                        jira_user.accountId,
                    )

                    return updated_user, jira_user

                updated_user, jira_user = run_async(_connect())

                # Update session state
                user_data = updated_user.model_dump()
                user_data["jira_display_name"] = jira_user.displayName
                user_data["jira_account_id"] = jira_user.accountId
                st.session_state["user"] = user_data

                st.success(f"Connected to Jira as **{jira_user.displayName}**!")
                st.rerun()

            except JiraAuthenticationError:
                st.error("Invalid Jira credentials. Please check your email and API token.")
            except JiraConnectionError as e:
                logger.exception(f"Jira connection error: {e.message}")
                st.error(f"Cannot connect to Jira: {e.message}")
            except Exception as e:
                logger.exception("Unexpected error during Jira connection")
                st.error(f"Connection failed: {e}")
