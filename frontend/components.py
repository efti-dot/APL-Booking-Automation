from __future__ import annotations

import streamlit as st

# Colours
GAP_COLOR = "#4A9BEF"
SWEATER_COLOR = "#EE9637"
APL_COLOR = "#F2CF1D"
NAVY = "#1F3A5F"

PAGES = {
    "home": "frontend/views/home.py",
    "select": "frontend/views/select_account.py",
    "gap_login": "frontend/views/gap_login.py",
    "gap_dpo": "frontend/views/gap_dpo.py",
}

_CSS = f"""
<style>
  .block-container {{ max-width: 1100px; padding-top: 2.5rem; }}

  .hero {{ text-align: center; padding: 3.5rem 1rem 2rem; }}
  .hero .badge {{
      display: inline-block; padding: .35rem .9rem; border-radius: 999px;
      background: rgba(31,58,95,.08); color: {NAVY}; font-size: .85rem; font-weight: 600;
  }}
  .hero h1 {{ font-size: 3.2rem; font-weight: 800; margin: 1rem 0 .5rem; color: {NAVY}; }}
  .hero p  {{ font-size: 1.15rem; opacity: .75; max-width: 680px; margin: 0 auto; }}

  .flow {{ display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap; margin: 2rem 0 2.5rem; }}
  .flow-step {{
      flex: 1 1 220px; max-width: 300px; padding: 1.2rem; border-radius: 14px;
      background: rgba(127,127,127,.06); border-top: 4px solid var(--c);
  }}
  .flow-step .num {{ font-size: .8rem; font-weight: 700; color: var(--c); letter-spacing: .05em; }}
  .flow-step h4 {{ margin: .3rem 0 .4rem; }}
  .flow-step p  {{ margin: 0; font-size: .92rem; opacity: .75; }}
  .soon {{ font-size: .7rem; background: {APL_COLOR}; color: #333; padding: .1rem .45rem;
           border-radius: 6px; margin-left: .3rem; vertical-align: middle; }}

  .account-card {{
      padding: 1.6rem; border-radius: 16px; min-height: 310px; margin-bottom: .8rem;
      border: 1px solid rgba(127,127,127,.2); border-top: 6px solid var(--c);
      background: rgba(127,127,127,.04);
  }}
  .account-card h3 {{ margin: 0 0 .25rem; }}
  .account-card .tag {{ color: var(--c); font-weight: 700; font-size: .9rem; }}
  .account-card ul {{ margin: .8rem 0 0; padding-left: 1.1rem; opacity: .8; }}

  .page-header {{ border-left: 6px solid var(--c); padding-left: 1rem; margin: .5rem 0 1.5rem; }}
  .page-header h2 {{ margin: 0; }}
  .page-header p  {{ margin: .2rem 0 0; opacity: .7; }}
</style>
"""


def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str, color: str = NAVY) -> None:
    st.markdown(
        f'<div class="page-header" style="--c:{color}"><h2>{title}</h2><p>{subtitle}</p></div>',
        unsafe_allow_html=True,
    )


def back_button(page_key: str, label: str = "← Back") -> None:
    if st.button(label, key=f"back_to_{page_key}"):
        st.switch_page(PAGES[page_key])
