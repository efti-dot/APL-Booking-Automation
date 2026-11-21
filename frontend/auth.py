from __future__ import annotations

from datetime import datetime

import streamlit as st

_KEY = "gap_nexus_session"


def save_login(username: str, storage_state: dict) -> None:
    st.session_state[_KEY] = {
        "username": username,
        "storage_state": storage_state,
        "logged_in_at": datetime.now(),
    }


def current_login() -> dict | None:
    return st.session_state.get(_KEY)


def logout() -> None:
    st.session_state.pop(_KEY, None)


def require_login(login_page: str) -> dict:
    session = current_login()
    if session is None:
        st.switch_page(login_page)
    return session
