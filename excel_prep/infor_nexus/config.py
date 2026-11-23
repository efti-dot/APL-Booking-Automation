"""Infor Nexus URLs and selectors. Fix things here when the website changes."""
import os

CONFIG = {
    # Login page
    "login_url": os.getenv("NEXUS_LOGIN_URL", "https://network.infornexus.com/login"),
    "orders_url": os.getenv(
        "NEXUS_ORDERS_URL",
        "https://network.infornexus.com/en/trade/OrdersView.jsp?legacy=true&grain=Order",
    ),
    "username_selector": "input[name='userid']",
    "password_selector": "input[name='uPassword']",
    "submit_selector": "#loginButton",
    "logged_in_selector": "input[name='ordersFilterOrder']",
    "error_selector": "",  # TODO: selector of the "wrong password" message
    "timeout_ms": 30_000,

    
    # DPO Beta report
    "dpo_report_url": os.getenv(
        "NEXUS_DPO_REPORT_URL",
        "https://network.infornexus.com/en/trade/ReportRun?key=290450662346&voType=ReportSpecVO",
    ),
    "criterion_label_selector": "span.gwt-InlineHTML",
    "ship_cxl_label_text": "Latest Ship Cxl",
    "operator_selector": "select.predicateoperator",
    "operator_between_value": "BETWEEN",
    "date_box_selector": "input.gwt-DateBox.valuewidgetdatebox",
    "report_date_format": "%Y-%m-%d",
    "report_timeout_ms": 60_000,

    "run_button_selector": "button.btn.btn-primary.btn-mini",
    "run_button_text": "Run",
    "download_timeout_ms": 1800_000,  # big date ranges can take a while to generate
}
