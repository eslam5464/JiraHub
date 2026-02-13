"""Cookie utilities for session persistence across browser refreshes.

Uses st.components.v1.html() to SET cookies (via JavaScript) and
st.context.cookies to READ them (native Streamlit, read-only).
"""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components


def set_session_cookie(token: str, max_age_hours: int = 72) -> None:
    """Set the session_token cookie in the browser via a hidden JS snippet."""
    max_age_seconds = max_age_hours * 3600
    js = f"""
    <script>
        document.cookie = "session_token={token}; path=/; max-age={max_age_seconds}; SameSite=Strict";
    </script>
    """
    components.html(js, height=0, width=0)


def clear_session_cookie() -> None:
    """Expire the session_token cookie in the browser."""
    js = """
    <script>
        document.cookie = "session_token=; path=/; max-age=0; SameSite=Strict";
    </script>
    """
    components.html(js, height=0, width=0)


def get_session_cookie() -> str | None:
    """Read the session_token cookie from the browser (read-only via Streamlit)."""
    try:
        cookies = st.context.cookies
        token = cookies.get("session_token")
        return token if token else None
    except Exception:
        return None
