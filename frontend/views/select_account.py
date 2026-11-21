import streamlit as st

from frontend.components import GAP_COLOR, PAGES, SWEATER_COLOR, back_button, inject_css, page_header

inject_css()
back_button("home")
page_header("Which Infor Nexus account?", "Pick the account you're booking cargo for.")

gap_col, sweater_col = st.columns(2, gap="large")

with gap_col:
    st.markdown(
        f"""
        <div class="account-card" style="--c:{GAP_COLOR}">
          <h3>👖 GAP</h3>
          <span class="tag">Excel built automatically</span>
          <ul>
            <li>Logs in to Infor Nexus with the GAP ID</li>
            <li>Searches DPO List Beta by date, description, buyer &amp; custom code</li>
            <li>Collects order totals and generates the APL booking Excel</li>
          </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Continue with GAP", type="primary", width="stretch", key="go_gap"):
        st.switch_page(PAGES["gap"])

with sweater_col:
    st.markdown(
        f"""
        <div class="account-card" style="--c:{SWEATER_COLOR}">
          <h3>🧶 Sweater</h3>
          <span class="tag">Excel filled manually</span>
          <ul>
            <li>Download an empty APL booking Excel</li>
            <li>Fill in the PO details yourself</li>
            <li>Upload it back to check it's ready for booking</li>
          </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Continue with Sweater", type="primary", width="stretch", key="go_sweater"):
        st.switch_page(PAGES["sweater"])
