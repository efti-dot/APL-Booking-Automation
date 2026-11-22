import html
from datetime import date, timedelta

import streamlit as st

from excel_prep.infor_nexus.dpo_list import ReportError, SessionExpired, fill_dpo_report_filter
from frontend.auth import logout, require_login
from frontend.components import GAP_COLOR, PAGES, inject_css, page_header

DATE_FMT = "YYYY/MM/DD"

inject_css()
session = require_login(PAGES["gap_login"])


@st.dialog("Latest Ship Cxl date range")
def date_range_dialog() -> None:
    st.caption("Orders whose **Latest Ship Cxl** date falls in this range will be included.")
    c1, c2 = st.columns(2)
    d_from = c1.date_input("From", value=date.today(), format=DATE_FMT)
    d_to = c2.date_input("To", value=date.today() + timedelta(days=30), format=DATE_FMT)

    if not st.button("Continue", type="primary", width="stretch"):
        return
    if d_from > d_to:
        st.error("'From' date must be on or before 'To' date.")
        return

    result, error = None, None
    with st.spinner("Opening DPO Beta report in Infor Nexus…"):
        try:
            result = fill_dpo_report_filter(session["storage_state"], d_from, d_to)
        except SessionExpired as exc:
            logout(notice=str(exc))
            st.switch_page(PAGES["gap_login"])
        except ReportError as exc:
            error = str(exc)

    if error:
        st.error(error, icon="⚠️")
        return

    st.session_state["dpo_filter_result"] = {
        "requested": (d_from, d_to),
        "shown_from": result.date_from,
        "shown_to": result.date_to,
        "screenshot": result.screenshot,
    }
    st.rerun()  # closes the popup and shows the result on the page


# ── Page ─────────────────────────────────────────────────────────────────
top_left, top_right = st.columns([4, 1])
with top_left:
    page_header(
        "👖 GAP · DPO List Beta",
        f"Logged in to Infor Nexus as <b>{html.escape(session['username'])}</b>",
        GAP_COLOR,
    )
with top_right:
    if st.button("Log out", width="stretch"):
        logout()
        st.switch_page(PAGES["gap_login"])

st.write("")
_, mid, _ = st.columns([1, 1, 1])
with mid:
    if st.button("\n\nDownload DPO Beta Excel", key="dpo_download", type="primary"):
        date_range_dialog()

done = st.session_state.get("dpo_filter_result")
if done:
    d_from, d_to = done["requested"]
    st.success(
        f"Infor Nexus filter set: **Latest Ship Cxl** between "
        f"**{d_from:%Y-%m-%d}** and **{d_to:%Y-%m-%d}** "
        f"(Infor Nexus shows `{done['shown_from']}` – `{done['shown_to']}`).",
    )
    
