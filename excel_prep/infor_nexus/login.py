from __future__ import annotations

import time

from core.browser import browser_session

from .config import CONFIG


class LoginError(Exception):
    """Wrong ID/password, or the site didn't respond as expected."""


def login(username: str, password: str) -> dict:
    if not username or not password:
        raise LoginError("Please enter both Infor Nexus ID and password.")

    from playwright.sync_api import Error as PlaywrightError

    with browser_session(timeout_ms=CONFIG["timeout_ms"]) as page:
        try:
            page.goto(CONFIG["login_url"])
            page.fill(CONFIG["username_selector"], username)
            page.fill(CONFIG["password_selector"], password)
            _submit_and_wait(page)

            page.goto(CONFIG["orders_url"])
            logged_in = page.locator(CONFIG["logged_in_selector"])
            login_form = page.locator(CONFIG["password_selector"])
            logged_in.or_(login_form).first.wait_for(state="visible")
            if not logged_in.first.is_visible():
                raise LoginError("Check your ID and password.")

            return page.context.storage_state()
        except LoginError:
            raise
        except PlaywrightError as exc:
            raise LoginError(f"Could not reach Infor Nexus: {exc.message.splitlines()[0]}") from exc


def _submit_and_wait(page) -> None:
    wrong = "Infor Nexus rejected the ID or password."
    password_box = page.locator(CONFIG["password_selector"]).first
    error_box = page.locator(CONFIG["error_selector"]).first if CONFIG["error_selector"] else None

    page_loads: list[int] = []
    on_load = lambda _: page_loads.append(1)  # noqa: E731
    page.on("domcontentloaded", on_load)
    page.click(CONFIG["submit_selector"])

    deadline = time.monotonic() + CONFIG["timeout_ms"] / 1000
    try:
        while time.monotonic() < deadline:
            try:
                if error_box is not None and error_box.is_visible():
                    raise LoginError(error_box.inner_text().strip() or wrong)
                if not password_box.is_visible():
                    page.wait_for_load_state("domcontentloaded")
                    return
                if page_loads:
                    raise LoginError(wrong)
            except LoginError:
                raise
            except Exception:
                pass
            page.wait_for_timeout(250)
    finally:
        page.remove_listener("domcontentloaded", on_load)

    raise LoginError("Login didn't complete in time — check your ID/password or try again.")
