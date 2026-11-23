import html
import mimetypes
from datetime import date, timedelta

import streamlit as st

from excel_prep.infor_nexus.dpo_list import ReportError, SessionExpired, download_dpo_report
from frontend.auth import logout, require_login
from frontend.components import GAP_COLOR, PAGES, inject_css, page_header

DATE_FMT = "YYYY/MM/DD"
RESULT_KEY = "dpo_report"

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

    report, error = None, None
    with st.spinner("Getting DPO List Beta from Infor Nexus… big ranges can take a minute."):
        try:
            report = download_dpo_report(session["storage_state"], d_from, d_to)
        except SessionExpired as exc:
            logout(notice=str(exc))
            st.switch_page(PAGES["gap_login"])
        except ReportError as exc:
            error = exc

    if error:
        st.error(str(error))
        if error.screenshot:
            with st.expander("What Infor Nexus showed"):
                st.image(error.screenshot)
        return

    st.session_state[RESULT_KEY] = {"requested": (d_from, d_to), "report": report}
    st.rerun()


# Page
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

done = st.session_state.get(RESULT_KEY)
if done:
    d_from, d_to = done["requested"]
    report = done["report"]
    size_kb = max(1, len(report.content) // 1024)

    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.success(
            f"DPO List Beta is ready: **Latest Ship Cxl** between "
            f"**{d_from:%d/%m/%Y}** and **{d_to:%d/%m/%Y}** "
            f"(Infor Nexus used `{report.date_from}` – `{report.date_to}`).",
        )
        st.download_button(
            f"Save {report.filename} to this PC ({size_kb:,} KB)",
            data=report.content,
            file_name=report.filename,
            mime=mimetypes.guess_type(report.filename)[0] or "application/octet-stream",
            on_click="ignore",  # no rerun; the file stays available until logout or a new run
            type="primary",
            width="stretch",
        )
