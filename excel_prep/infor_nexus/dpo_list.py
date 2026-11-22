from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from core.browser import browser_session

from .config import CONFIG


class SessionExpired(Exception):


class ReportError(Exception):


@dataclass
class DpoFilterResult:
    date_from: str
    date_to: str
    screenshot: bytes


def fill_dpo_report_filter(storage_state: dict, date_from: date, date_to: date) -> DpoFilterResult:
    from playwright.sync_api import Error as PlaywrightError

    with browser_session(storage_state=storage_state, timeout_ms=CONFIG["report_timeout_ms"]) as page:
        try:
            page.goto(CONFIG["dpo_report_url"])
            label = _wait_for_report_or_login(page)
            row = _criterion_row(label)

            # operator dropdown to "between"
            row.locator(CONFIG["operator_selector"]).first.select_option(CONFIG["operator_between_value"])

            # "between" shows two date boxes
            boxes = row.locator(CONFIG["date_box_selector"])
            boxes.nth(1).wait_for(state="visible")
            shown_from = _fill_date_box(boxes.nth(0), date_from)
            shown_to = _fill_date_box(boxes.nth(1), date_to)

            return DpoFilterResult(shown_from, shown_to, page.screenshot(full_page=True))
        except (SessionExpired, ReportError):
            raise
        except PlaywrightError as exc:
            raise ReportError(f"Infor Nexus report page problem: {exc.message.splitlines()[0]}") from exc


# helpers
def _wait_for_report_or_login(page):
    text = re.compile(rf"^\s*{re.escape(CONFIG['ship_cxl_label_text'])}\s*$")
    label = page.locator(CONFIG["criterion_label_selector"]).filter(has_text=text).first
    login_form = page.locator(CONFIG["password_selector"]).first

    label.or_(login_form).wait_for(state="visible")
    if login_form.is_visible():
        raise SessionExpired("Your Infor Nexus session has expired. Please log in again.")
    return label


def _criterion_row(label):
    row = label.locator(
        "xpath=ancestor::*[.//select[contains(concat(' ', normalize-space(@class), ' '), ' predicateoperator ')]][1]"
    )
    if row.count() == 0:
        raise ReportError("Found 'Latest Ship Cxl' but not its operator dropdown.")
    return row


def _fill_date_box(box, value: date) -> str:
    """Types the date like a user, then Tab so GWT accepts it. Returns what the box shows."""
    text = value.strftime(CONFIG["report_date_format"])
    box.click()
    box.fill(text)
    box.press("Tab")

    shown = box.input_value().strip()
    if not shown:
        raise ReportError(
            f"Infor Nexus didn't accept the date '{text}'. "
            "Check `report_date_format` in excel_prep/infor_nexus/config.py."
        )
    return shown
