import streamlit as st
from pydantic import SecretStr, ValidationError as PydanticValidationError

from app.core.exceptions.domain import AuthorizationError, DuplicateResourceError
from app.schemas.user import UserRegister
from app.services.auth_service import AuthService
from app.utils.async_helpers import run_async


def render():
    st.title("Register")
    st.markdown("Create an account to access the Jira Team Dashboard.")

    with st.form("register_form"):
        email = st.text_input("Email", placeholder="you@dar.com")
        password = st.text_input(
            "Password", type="password", placeholder="Min 8 chars, 1 uppercase, 1 digit"
        )
        confirm_password = st.text_input("Confirm Password", type="password")
        submitted = st.form_submit_button("Register", use_container_width=True)

    if submitted:
        if not email or not password:
            st.error("Email and password are required.")
            return

        if password != confirm_password:
            st.error("Passwords do not match.")
            return

        try:
            data = UserRegister(email=email, password=SecretStr(password))
        except PydanticValidationError as e:
            for error in e.errors():
                st.error(error["msg"])
            return

        try:
            user = run_async(AuthService.register(data))
            if user.status == "approved":
                st.success("Account created! You are the admin. You can now log in.")
            else:
                st.success("Account created! Please wait for admin approval before logging in.")
        except DuplicateResourceError:
            st.error("An account with this email already exists.")
        except AuthorizationError as e:
            st.error(str(e.message))
        except Exception as e:
            st.error(f"Registration failed: {e}")
