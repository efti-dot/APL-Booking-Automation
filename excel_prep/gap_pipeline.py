from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable

from core.browser import browser_session

from .dpo_workbook import DpoExcelError, add_total_amount, load_and_dedupe
from .infor_nexus.common import ReportError, SessionExpired, snap
from .infor_nexus.config import CONFIG
from .infor_nexus.dpo_list import download_dpo_report
from .infor_nexus.order_amounts import AmountLookup, fetch_total_amounts

__all__ = ["GapExcel", "ReportError", "SessionExpired", "build_gap_dpo_excel"]

Progress = Callable[[float, str], None]


@dataclass
class GapExcel:
    filename: str
    content: bytes
    shown_from: str
    shown_to: str
    dpo_rows: int
    duplicates_removed: int
    lookups: list[AmountLookup]

    @property
    def problems(self) -> list[AmountLookup]:
        return [x for x in self.lookups if x.amount is None or x.note]


def build_gap_dpo_excel(storage_state: dict, date_from: date, date_to: date,
                        progress: Progress | None = None) -> GapExcel:
    from playwright.sync_api import Error as PlaywrightError

    say = progress or (lambda fraction, message: None)

    with browser_session(storage_state=storage_state, timeout_ms=CONFIG["report_timeout_ms"]) as page:
        try:
            say(0.02, "Downloading DPO List Beta from Infor Nexus…")
            report = download_dpo_report(page, date_from, date_to)

            say(0.10, "Removing duplicate POs…")
            sheet = load_and_dedupe(report.content, report.original_filename)
            if not sheet.pos:
                raise ReportError("DPO List Beta has no POs for this date range.")

            def on_po(done: int, total: int, po: str) -> None:
                if po:
                    say(0.10 + 0.88 * done / total, f"Total Amount · PO {po} ({done + 1} of {total})")

            lookups = fetch_total_amounts(page, sheet.pos, on_po)
        except (SessionExpired, ReportError):
            raise
        except DpoExcelError as exc:
            raise ReportError(str(exc)) from exc
        except PlaywrightError as exc:
            raise ReportError(f"Infor Nexus page problem: {exc.message.splitlines()[0]}", snap(page)) from exc

    say(0.99, "Building the final Excel…")
    content = add_total_amount(sheet, {po: x.amount for po, x in lookups.items()})
    return GapExcel(
        filename=f"GAP_DPO_{date_from:%Y-%m-%d}_to_{date_to:%Y-%m-%d}_with_Total_Amount.xlsx",
        content=content,
        shown_from=report.date_from,
        shown_to=report.date_to,
        dpo_rows=sheet.rows_before,
        duplicates_removed=sheet.duplicates_removed,
        lookups=[lookups[po] for po in sheet.pos],
    )
