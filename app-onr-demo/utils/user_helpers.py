"""
User and SSO Helpers for ONR ITSS POC
Handles SSO user detection from Databricks App headers.
"""

from typing import Optional, Dict
import streamlit as st


def _parse_name_from_email(email: str) -> Dict[str, str]:
    """Parse first/last name from email address."""
    local = email.split("@", 1)[0]
    name_raw = local.replace(".", " ").replace("_", " ").replace("-", " ")
    parts = [p for p in name_raw.split() if p]

    first_name = parts[0].title() if parts else ""
    last_name = " ".join(p.title() for p in parts[1:]) if len(parts) > 1 else ""
    return {"first_name": first_name, "last_name": last_name}


def get_current_user_from_headers() -> Optional[Dict]:
    """Extract user info from Databricks App SSO headers."""
    headers = getattr(st.context, "headers", None)
    if not headers:
        return None

    email = (
        headers.get("X-Forwarded-Email")
        or headers.get("x-forwarded-email")
    )
    preferred_username = (
        headers.get("X-Forwarded-Preferred-Username")
        or headers.get("x-forwarded-preferred-username")
    )

    if not email:
        return None

    email = email.strip().lower()
    display_source = preferred_username or email
    name_parts = _parse_name_from_email(display_source)

    return {
        "first_name": name_parts["first_name"],
        "last_name": name_parts["last_name"],
        "email": email,
        "display_name": display_source,
    }


def get_current_user() -> Optional[Dict]:
    """Return end-user info if available; cache once per session."""
    if "sso_user_initialized" not in st.session_state:
        st.session_state["sso_user_initialized"] = True
        st.session_state["sso_user"] = get_current_user_from_headers()
    return st.session_state.get("sso_user")


def init_user_session_state() -> Optional[Dict]:
    """
    Initialize global name/email fields from SSO headers,
    but only if they are not already set (so user edits survive).
    Call this once near the top of each page.
    """
    user = get_current_user()
    if not user:
        return None

    sso_first = user.get("first_name", "") or ""
    sso_last = user.get("last_name", "") or ""
    sso_email = user.get("email", "") or ""

    # Global identity fields
    if not st.session_state.get("first_name"):
        st.session_state["first_name"] = sso_first
    if not st.session_state.get("last_name"):
        st.session_state["last_name"] = sso_last
    if not st.session_state.get("email"):
        st.session_state["email"] = sso_email
        st.session_state["email_valid"] = True  # trust SSO email

    return user
