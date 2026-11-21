"""Infor Nexus URLs and selectors. Fix things here when the website changes."""
import os

CONFIG = {
    # URLs can be overridden from .env (handy for testing against a fake site).
    "login_url": os.getenv("NEXUS_LOGIN_URL", "https://network.infornexus.com/login"),
    "orders_url": os.getenv(
        "NEXUS_ORDERS_URL",
        "https://network.infornexus.com/en/trade/OrdersView.jsp?legacy=true&grain=Order",
    ),
    "username_selector": "input[name='userid']",
    "password_selector": "input[name='uPassword']",
    "submit_selector": "#loginButton",
    "logged_in_selector": "input[name='ordersFilterOrder']",
    "error_selector": "",  # TODO: selector of the "wrong password" message, if the site shows one
    "timeout_ms": 30_000,
}
