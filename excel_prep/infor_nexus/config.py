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
    "download_timeout_ms": 1800_000,
    "orders_search_url": os.getenv(
        "NEXUS_ORDERS_SEARCH_URL", "https://network.infornexus.com/en/trade/InProgressOrders"
    ),
    "order_filter_selector": "input[name='ordersFilterOrder']",
    "apply_button_selector": "input[type='button'][value='Apply']",
    "result_cell_class": "listtablecell",
    "total_amount_header_text": "Total Amount",
    "order_search_timeout_ms": 60_000,

    # Buyer and Destination
    "orders_view_url": os.getenv(
        "NEXUS_ORDERS_VIEW_URL", "https://network.infornexus.com/en/trade/OrdersView.jsp"
    ),
    "global_search_selector": "#navbarsearch",
    "search_result_link_selector": "a.coreLink[href*='searchResultRank=']",
    "search_result_type_selector": "span.preserveLineBreaks",
    "search_result_type_order": "Order",
    "search_result_value_selector": ".core-focus-link",
    "buyer_label": "Buyer",
    "destination_label": "Destination",
    "search_result_timeout_ms": 30_000,
    "search_retype_wait_ms": 10_000,
    "search_card_fields_wait_ms": 8_000,
}
