import streamlit as st

from app.core.exceptions.domain import AuthenticationError, AuthorizationError
from app.services.auth_service import AuthService
from app.utils.async_helpers import run_async


def render():
    st.title("Login")
    st.markdown("Sign in to access the Jira Team Dashboard.")

    with st.form("login_form"):
        email = st.text_input("Email", placeholder="you@dar.com")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", use_container_width=True)

    if submitted:
        if not email or not password:
            st.error("Email and password are required.")
            return

        try:
            user, session_token = run_async(AuthService.login(email, password))

            # Store in session state
            st.session_state["authenticated"] = True
            st.session_state["user"] = user.model_dump()
            st.session_state["session_token"] = session_token

            st.success(f"Welcome back, {user.email}!")
            st.rerun()

        except AuthenticationError as e:
            st.error(str(e.message))
        except AuthorizationError as e:
            st.warning(str(e.message))
        except Exception as e:
            st.error(f"Login failed: {e}")
