import streamlit as st

st.set_page_config(page_title="APL Booking Automation", page_icon="🚢", layout="wide")

pages = [
    st.Page("frontend/views/home.py", title="Home", default=True),
    st.Page("frontend/views/select_account.py", title="Select account"),
    st.Page("frontend/views/gap_login.py", title="GAP login", icon="👖"),
    st.Page("frontend/views/gap_dpo.py", title="GAP DPO List", icon="📄"),
]


st.navigation(pages, position="hidden").run()