from __future__ import annotations

import csv
import io
import re
from copy import copy
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.styles import PatternFill
from openpyxl.utils import get_column_letter

# Assume the DPO number header
PO_HEADERS = ("po number", "po #", "DPO", "po num", "po", "purchase order", "order number", "order #", "order no")
TOTAL_AMOUNT_HEADER = "Total Amount"
HEADER_SCAN_ROWS = 20
MISSING_FILL = PatternFill("solid", fgColor="FFF2CC")  # light yellow = amount not found


class DpoExcelError(Exception):
    """The DPO file couldn't be read the way we expect."""


@dataclass
class DpoSheet:
    workbook: Workbook
    header_row: int
    po_col: int
    pos: list[str] = field(default_factory=list)  # unique PO
    rows_before: int = 0
    duplicates_removed: int = 0


def load_and_dedupe(content: bytes, filename: str) -> DpoSheet:
    """Opens the DPO file and deletes every row whose PO already appeared above it."""
    wb = _open(content, filename)
    ws = wb.active
    header_row, po_col = _find_po_header(ws)

    seen: set[str] = set()
    duplicate_rows: list[int] = []
    pos: list[str] = []
    rows_before = 0
    for r in range(header_row + 1, ws.max_row + 1):
        po = po_text(ws.cell(r, po_col).value)
        if not po:
            continue
        rows_before += 1
        if po in seen:
            duplicate_rows.append(r)
        else:
            seen.add(po)
            pos.append(po)

    for r in reversed(duplicate_rows):
        ws.delete_rows(r)

    return DpoSheet(wb, header_row, po_col, pos, rows_before, len(duplicate_rows))


def add_total_amount(sheet: DpoSheet, amounts: dict[str, Decimal | None]) -> bytes:
    """Writes each PO's amount into a "Total Amount" column and returns the .xlsx bytes."""
    ws = sheet.workbook.active
    po_header = ws.cell(sheet.header_row, sheet.po_col)
    col = _total_amount_column(ws, sheet.header_row)

    head = ws.cell(sheet.header_row, col, TOTAL_AMOUNT_HEADER)
    for attr in ("font", "fill", "border", "alignment"):
        setattr(head, attr, copy(getattr(po_header, attr)))
    ws.column_dimensions[get_column_letter(col)].width = 16

    for r in range(sheet.header_row + 1, ws.max_row + 1):
        po = po_text(ws.cell(r, sheet.po_col).value)
        if not po:
            continue
        cell = ws.cell(r, col)
        amount = amounts.get(po)
        if amount is None:
            cell.value = None
            cell.fill = MISSING_FILL
        else:
            cell.value = float(amount)
            cell.number_format = "#,##0.00"

    out = io.BytesIO()
    sheet.workbook.save(out)
    return out.getvalue()


def po_text(value) -> str:
    """Cell value → PO as text. Excel often stores 62397850 as the number 62397850.0."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip()


#helpers
def _norm(value) -> str:
    return re.sub(r"[\s_.:]+", " ", str(value or "")).strip().lower()


def _open(content: bytes, filename: str) -> Workbook:
    ext = Path(filename).suffix.lower()
    if ext in (".xlsx", ".xlsm"):
        try:
            return load_workbook(io.BytesIO(content))
        except Exception as exc:
            raise DpoExcelError(f"Couldn't open the DPO Excel ({filename}): {exc}") from exc
    if ext == ".csv":
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content.decode("cp1252")
        wb = Workbook()
        for row in csv.reader(io.StringIO(text)):
            wb.active.append(row)
        return wb
    raise DpoExcelError(
        f"Infor Nexus sent a '{ext or 'unknown'}' file ({filename}). "
        "Only .xlsx and .csv are supported right now."
    )


def _find_po_header(ws) -> tuple[int, int]:
    wanted = {_norm(h) for h in PO_HEADERS}
    seen = []
    for r in range(1, min(ws.max_row, HEADER_SCAN_ROWS) + 1):
        for c in range(1, ws.max_column + 1):
            text = _norm(ws.cell(r, c).value)
            if text in wanted:
                return r, c
            if text:
                seen.append(str(ws.cell(r, c).value).strip())
    raise DpoExcelError(
        "Couldn't find the PO column in the DPO Excel. Headers found: "
        + ", ".join(seen[:30])
        + ". Add the right name to PO_HEADERS in excel_prep/dpo_workbook.py."
    )


def _total_amount_column(ws, header_row: int) -> int:
    """Existing "Total Amount" column if the file has one, else the first empty column."""
    last = 0
    for row in ws.iter_rows():
        for cell in row:
            if cell.value is not None:
                last = max(last, cell.column)
    for c in range(1, last + 1):
        if _norm(ws.cell(header_row, c).value) == _norm(TOTAL_AMOUNT_HEADER):
            return c
    return last + 1
