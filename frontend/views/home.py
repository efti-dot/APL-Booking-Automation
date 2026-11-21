import streamlit as st

from frontend.components import APL_COLOR, GAP_COLOR, PAGES, SWEATER_COLOR, inject_css

inject_css()

st.markdown(
    """
    <div class="hero">
      <span class="badge">Ha-Meem Group · Denim Export Logistics</span>
      <h1>APL Booking Automation</h1>
      <p>Pull PO data from Infor Nexus, prepare the APL booking Excel, and book
         cargo for USA, Canada, Japan and more.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="flow">
      <div class="flow-step" style="--c:{GAP_COLOR}">
        <div class="num">STEP 1</div><h4>Choose account</h4>
        <p>GAP or Sweater Infor Nexus account.</p>
      </div>
      <div class="flow-step" style="--c:{SWEATER_COLOR}">
        <div class="num">STEP 2</div><h4>Prepare booking Excel</h4>
        <p>Auto-built for GAP, template to fill for Sweater.</p>
      </div>
      <div class="flow-step" style="--c:{APL_COLOR}">
        <div class="num">STEP 3</div><h4>Book on APL <span class="soon">SOON</span></h4>
        <p>Submit the cargo booking on APL Logistics.</p>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

_, mid, _ = st.columns([2, 1, 2])
with mid:
    if st.button("Get Started →", type="primary", width="stretch"):
        st.switch_page(PAGES["select"])
