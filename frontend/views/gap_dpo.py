import html

import streamlit as st
from frontend.auth import logout, require_login
from frontend.components import GAP_COLOR, PAGES, inject_css, page_header

inject_css()
session = require_login(PAGES["gap_login"])

top_left, top_right = st.columns([4, 1])
with top_left:
    page_header("👖 GAP", f"Logged in to Infor Nexus as <b>{html.escape(session['username'])}</b>", GAP_COLOR)
with top_right:
    if st.button("Log out", width="stretch"):
        logout()
        st.switch_page(PAGES["gap_login"])

st.write("")
_, mid, _ = st.columns([1, 1, 1])
with mid:
    clicked = st.button("\n\nDownload DPO Beta Excel", key="dpo_download", type="primary")

if clicked:
    try:
        path = download_dpo_beta_excel(session["storage_state"])
    except NotImplementedError:
        st.info("Login works")
    else:
        st.success(f"Downloaded `{path.name}`")
