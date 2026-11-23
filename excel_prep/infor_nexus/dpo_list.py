from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from core.browser import browser_session

from .config import CONFIG


class SessionExpired(Exception):
    """The Infor Nexus session has expired; the user must log in again."""


class ReportError(Exception):
    """The report page didn't behave as expected."""

    def __init__(self, message: str, screenshot: bytes | None = None):
        super().__init__(message)
        self.screenshot = screenshot


@dataclass
class DpoReport:
    date_from: str
    date_to: str
    filename: str
    original_filename: str
    content: bytes


def download_dpo_report(storage_state: dict, date_from: date, date_to: date) -> DpoReport:
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
            shown_from = _fill_date_box(page, boxes.nth(0), date_from)
            shown_to = _fill_date_box(page, boxes.nth(1), date_to)

            # Run btn Infor Nexus generates the report and downloads it
            download = _run_and_wait_for_download(page)
            content = Path(download.path()).read_bytes()
        except (SessionExpired, ReportError):
            raise
        except PlaywrightError as exc:
            raise ReportError(
                f"Infor Nexus report page problem: {exc.message.splitlines()[0]}", _snap(page)
            ) from exc

    original = download.suggested_filename or "DPO_List_Beta.xlsx"
    ext = Path(original).suffix or ".xlsx"
    filename = f"DPO_List_Beta_{date_from:%Y-%m-%d}_to_{date_to:%Y-%m-%d}{ext}"
    return DpoReport(shown_from, shown_to, filename, original, content)


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


def _fill_date_box(page, box, value: date) -> str:
    text = value.strftime(CONFIG["report_date_format"])
    box.click()
    box.fill(text)
    box.press("Tab")

    shown = box.input_value().strip()
    if not shown:
        raise ReportError(
            f"Infor Nexus didn't accept the date '{text}'. "
            "Check `report_date_format` in excel_prep/infor_nexus/config.py.",
            _snap(page),
        )
    return shown


def _run_and_wait_for_download(page):
    text = re.compile(rf"^\s*{re.escape(CONFIG['run_button_text'])}\s*$")
    run = page.locator(CONFIG["run_button_selector"]).filter(has_text=text)
    if run.count() == 0:
        raise ReportError("Couldn't find the 'Run' button on the DPO Beta report.", _snap(page))

    downloads = []

    def on_download(download):
        downloads.append(download)

    def watch(p):
        p.on("download", on_download)

    watch(page)
    page.context.on("page", watch)

    run.first.click()

    deadline = time.monotonic() + CONFIG["download_timeout_ms"] / 1000
    while not downloads:
        if time.monotonic() > deadline:
            raise ReportError(
                f"Clicked Run, but Infor Nexus didn't send a file within "
                f"{CONFIG['download_timeout_ms'] // 1000} s.",
                _snap(page),
            )
        page.wait_for_timeout(500)

    download = downloads[0]
    if failure := download.failure():
        raise ReportError(f"The DPO Beta download failed: {failure}", _snap(page))
    return download


def _snap(page) -> bytes | None:
    try:
        return page.screenshot(full_page=True)
    except Exception:
        return None
