"""Errors shared by every Infor Nexus stage."""
from __future__ import annotations

from .config import CONFIG


class SessionExpired(Exception):
    """Infor Nexus sent us to the login page — the saved cookies are no longer valid."""

    def __init__(self, message: str = "Your Infor Nexus session has expired. Please log in again."):
        super().__init__(message)


class ReportError(Exception):
    """An Infor Nexus page didn't look/behave as expected."""

    def __init__(self, message: str, screenshot: bytes | None = None):
        super().__init__(message)
        self.screenshot = screenshot


def login_form(page):
    """Locator for the Infor Nexus password box (visible = we were logged out)."""
    return page.locator(CONFIG["password_selector"]).first


def snap(page) -> bytes | None:
    try:
        return page.screenshot(full_page=True)
    except Exception:
        return None
