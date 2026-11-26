"""GAP: DPO List Beta + Total Amount + Buyer + Destination, in ONE browser with the
user's saved login.

  1. DPO Beta report → filter Latest Ship Cxl → Run → file   (infor_nexus/dpo_list.py)
  2. Remove duplicate POs                                    (dpo_workbook.py)
  3. In-progress orders → search each PO → Total Amount      (infor_nexus/order_amounts.py)
  4. Global search → each PO's "Order" result → Buyer, Destination (infor_nexus/po_details.py)
  5. Add the new columns → final .xlsx bytes                 (dpo_workbook.py)

Nothing is written to the server's disk; the frontend sends the bytes to the user's PC.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Callable

from core.browser import browser_session

from .dpo_workbook import DpoExcelError, NewColumn, add_columns, load_and_dedupe
from .infor_nexus.common import ReportError, SessionExpired, snap
from .infor_nexus.config import CONFIG
from .infor_nexus.dpo_list import download_dpo_report
from .infor_nexus.order_amounts import AmountLookup, fetch_total_amounts
from .infor_nexus.po_details import PoDetails, fetch_po_details

__all__ = ["GapExcel", "PoResult", "ReportError", "SessionExpired", "build_gap_dpo_excel"]

Progress = Callable[[float, str], None]

# Share of the progress bar for each stage
_AMOUNTS = (0.10, 0.55)
_DETAILS = (0.55, 0.98)


@dataclass
class PoResult:
    po: str
    amount: AmountLookup
    details: PoDetails

    @property
    def notes(self) -> str:
        return " · ".join(n for n in (self.amount.note, self.details.note) if n)

    @property
    def complete(self) -> bool:
        return self.amount.amount is not None and bool(self.details.buyer and self.details.destination)


@dataclass
class GapExcel:
    filename: str
    content: bytes
    shown_from: str
    shown_to: str
    dpo_rows: int
    duplicates_removed: int
    rows: list[PoResult]

    @property
    def problems(self) -> list[PoResult]:
        return [r for r in self.rows if not r.complete or r.notes]

    @property
    def debug(self) -> PoResult | None:
        """First PO whose Buyer or Destination couldn't be read and has a troubleshooting zip."""
        return next((r for r in self.rows if r.details.debug_zip), None)


def build_gap_dpo_excel(storage_state: dict, date_from: date, date_to: date,
                        progress: Progress | None = None) -> GapExcel:
    from playwright.sync_api import Error as PlaywrightError

    say = progress or (lambda fraction, message: None)

    def stage(span: tuple[float, float], label: str):
        start, end = span

        def on_po(done: int, total: int, po: str) -> None:
            if po:
                say(start + (end - start) * done / total, f"{label} · PO {po} ({done + 1} of {total})")
        return on_po

    with browser_session(storage_state=storage_state, timeout_ms=CONFIG["report_timeout_ms"]) as page:
        try:
            say(0.02, "Downloading DPO List Beta from Infor Nexus…")
            report = download_dpo_report(page, date_from, date_to)

            say(_AMOUNTS[0], "Removing duplicate POs…")
            sheet = load_and_dedupe(report.content, report.original_filename)
            if not sheet.pos:
                raise ReportError("DPO List Beta has no POs for this date range.")

            amounts = fetch_total_amounts(page, sheet.pos, stage(_AMOUNTS, "Total Amount"))
            details = fetch_po_details(page, sheet.pos, stage(_DETAILS, "Buyer & Destination"))
        except (SessionExpired, ReportError):
            raise
        except DpoExcelError as exc:
            raise ReportError(str(exc)) from exc
        except PlaywrightError as exc:
            raise ReportError(f"Infor Nexus page problem: {exc.message.splitlines()[0]}", snap(page)) from exc

    say(0.99, "Building the final Excel…")
    rows = [PoResult(po, amounts[po], details[po]) for po in sheet.pos]
    content = add_columns(sheet, [
        NewColumn("Total Amount", {r.po: r.amount.amount for r in rows}, number_format="#,##0.00"),
        NewColumn("Buyer", {r.po: r.details.buyer for r in rows}, width=28),
        NewColumn("Destination", {r.po: r.details.destination for r in rows}, width=14),
    ])
    return GapExcel(
        filename=f"GAP_DPO_{date_from:%Y-%m-%d}_to_{date_to:%Y-%m-%d}.xlsx",
        content=content,
        shown_from=report.date_from,
        shown_to=report.date_to,
        dpo_rows=sheet.rows_before,
        duplicates_removed=sheet.duplicates_removed,
        rows=rows,
    )
