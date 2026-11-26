import base64
import html
import json
from datetime import date, timedelta

import streamlit as st

from excel_prep.gap_pipeline import ReportError, SessionExpired, build_gap_dpo_excel
from frontend.auth import logout, require_login
from frontend.components import GAP_COLOR, PAGES, inject_css, page_header

DATE_FMT = "YYYY/MM/DD"
RESULT_KEY = "dpo_report"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

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

    bar = st.progress(0.0, text="Starting…")
    st.caption("Each PO is searched in Infor Nexus one by one — please keep this tab open.")

    excel, error = None, None
    try:
        # Uses the cookies
        excel = build_gap_dpo_excel(
            session["storage_state"], d_from, d_to,
            progress=lambda fraction, message: bar.progress(min(fraction, 1.0), text=message),
        )
    except SessionExpired as exc:
        logout(notice=str(exc))
        st.switch_page(PAGES["gap_login"])
    except ReportError as exc:
        error = exc

    if error:
        bar.empty()
        st.error(str(error))
        if error.screenshot:
            with st.expander("What Infor Nexus showed"):
                st.image(error.screenshot)
        return

    # Kept only in this user's session
    st.session_state[RESULT_KEY] = {"requested": (d_from, d_to), "excel": excel, "auto_download": True}
    st.rerun()  # closes the popup


def auto_download(filename: str, content: bytes) -> None:
    """Makes the user's browser save the file — it lands in *their* Downloads folder,
    even when this app runs on the company server."""
    st.html(
        f"""<script>
        (() => {{
          const bytes = Uint8Array.from(atob("{base64.b64encode(content).decode()}"), c => c.charCodeAt(0));
          const a = document.createElement("a");
          a.href = URL.createObjectURL(new Blob([bytes], {{type: "{XLSX_MIME}"}}));
          a.download = {json.dumps(filename)};
          document.body.appendChild(a);
          a.click();
          setTimeout(() => {{ URL.revokeObjectURL(a.href); a.remove(); }}, 2000);
        }})();
        </script>""",
        unsafe_allow_javascript=True,
    )


#Page
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
    excel = done["excel"]
    if done.pop("auto_download", False):  # only once, right after it was built
        auto_download(excel.filename, excel.content)

    total = len(excel.rows)
    complete = sum(r.complete for r in excel.rows)
    _, mid, _ = st.columns([1, 8, 1])
    with mid:
        st.success(
            f"**{excel.filename}** was downloaded to this PC.\n\n"
            f"Latest Ship Cxl **{d_from:%d/%m/%Y} – {d_to:%d/%m/%Y}** · "
            f"{total} POs ({excel.duplicates_removed} duplicate rows removed) · "
            f"Total Amount, Buyer and Destination found for **{complete} of {total}**.",
            icon="✅",
        )
        if excel.problems:
            st.warning(
                f"{len(excel.problems)} PO(s) need a look — their missing cells are "
                "yellow in the Excel. See the Note column below.",
                icon="⚠️",
            )
        with st.expander(f"Details per PO ({total})", expanded=bool(excel.problems)):
            st.dataframe(
                [
                    {
                        "PO": r.po,
                        "Total Amount": r.amount.raw or "—",
                        "Buyer": r.details.buyer or "—",
                        "Destination": r.details.destination or "—",
                        "Note": r.notes,
                    }
                    for r in excel.rows
                ],
                hide_index=True,
                width="stretch",
                column_config={"Note": st.column_config.TextColumn(width="large")},
            )
        debug = excel.debug
        if debug:
            st.download_button(
                f"Download troubleshooting file (PO {debug.po})",
                data=debug.details.debug_zip,
                file_name=f"buyer_destination_debug_{debug.po}.zip",
                mime="application/zip",
                on_click="ignore",
                icon=":material/bug_report:",
                help="Screenshot + HTML of the Infor Nexus search result where Buyer/Destination "
                     "couldn't be read. Send it to whoever maintains this app.",
            )
        st.download_button(
            "Didn't download? Save it again",
            data=excel.content,
            file_name=excel.filename,
            mime=XLSX_MIME,
            on_click="ignore",
            type="tertiary",
            icon=":material/download:",
        )

