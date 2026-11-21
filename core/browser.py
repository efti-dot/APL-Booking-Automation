from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Iterator

from config import settings

# Shared by all users
_browser_slots = threading.BoundedSemaphore(settings.MAX_CONCURRENT_BROWSERS)


@contextmanager
def browser_session(storage_state: dict | None = None, timeout_ms: int = 30_000) -> Iterator["Page"]:  # noqa: F821
    """Yields a Page in a fresh browser. Pass `storage_state` to reuse a login."""
    from playwright.sync_api import sync_playwright

    with _browser_slots, sync_playwright() as p:
        browser = p.chromium.launch(headless=settings.HEADLESS, slow_mo=settings.SLOW_MO_MS)
        context = browser.new_context(storage_state=storage_state, accept_downloads=True)
        context.set_default_timeout(timeout_ms)
        page = context.new_page()
        try:
            yield page
        finally:
            context.close()
            browser.close()
