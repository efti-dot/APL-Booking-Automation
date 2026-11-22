import streamlit as st

from config import settings
from excel_prep.infor_nexus.login import LoginError, login
from frontend.auth import current_login, pop_login_notice, save_login
from frontend.components import GAP_COLOR, PAGES, back_button, inject_css, page_header

inject_css()

if current_login():
    st.switch_page(PAGES["gap_dpo"])

back_button("select")

_, mid, _ = st.columns([1, 1.4, 1])
with mid:
    page_header("Infor Nexus login", "GAP account · sign in with your own ID.", GAP_COLOR)

    notice = pop_login_notice()
    if notice:
        st.warning(notice)

    has_default = bool(settings.NEXUS_USERNAME and settings.NEXUS_PASSWORD)

    with st.form("gap_login", border=True):
        username = st.text_input("Infor Nexus ID", autocomplete="username")
        password = st.text_input("Password", type="password", autocomplete="current-password")
        if has_default:
            st.caption("Leave both fields empty to use the default account from `.env`.")
        submitted = st.form_submit_button("Log in", type="primary", width="stretch")

    if submitted:
        username = username.strip()
        if has_default and not username and not password:
            username, password = settings.NEXUS_USERNAME, settings.NEXUS_PASSWORD

        cookies, error = None, None
        with st.spinner("Logging in to Infor Nexus… this can take a few seconds."):
            try:
                cookies = login(username, password)
            except LoginError as exc:
                error = str(exc)

        if error:
            st.error(error, icon="🔒")
        else:
            save_login(username, cookies)
            st.switch_page(PAGES["gap_dpo"])
