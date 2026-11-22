from __future__ import annotations

from datetime import datetime

import streamlit as st

_KEY = "gap_nexus_session"
_NOTICE_KEY = "gap_login_notice"

GAP_STATE_KEYS = (_KEY, "dpo_filter_result")


def save_login(username: str, storage_state: dict) -> None:
    st.session_state[_KEY] = {
        "username": username,
        "storage_state": storage_state,
        "logged_in_at": datetime.now(),
    }


def current_login() -> dict | None:
    return st.session_state.get(_KEY)


def logout(notice: str | None = None) -> None:
    """Forget this user's Infor Nexus session. `notice` is shown on the login page."""
    for key in GAP_STATE_KEYS:
        st.session_state.pop(key, None)
    if notice:
        st.session_state[_NOTICE_KEY] = notice


def pop_login_notice() -> str | None:
    return st.session_state.pop(_NOTICE_KEY, None)


def require_login(login_page: str) -> dict:
    session = current_login()
    if session is None:
        st.switch_page(login_page)
    return session
