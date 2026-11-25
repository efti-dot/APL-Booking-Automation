from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Callable, Iterable

from .common import ReportError, SessionExpired, login_form, snap
from .config import CONFIG


@dataclass
class AmountLookup:
    po: str
    amount: Decimal | None
    raw: str = ""
    note: str = ""


ProgressFn = Callable[[int, int, str], None]


def fetch_total_amounts(page, pos: Iterable[str], on_progress: ProgressFn | None = None) -> dict[str, AmountLookup]:
    pos = list(pos)
    _open_search_page(page)
    results: dict[str, AmountLookup] = {}
    for i, po in enumerate(pos):
        if on_progress:
            on_progress(i, len(pos), po)
        results[po] = _lookup(page, po)
    if on_progress:
        on_progress(len(pos), len(pos), "")
    return results


# one PO
def _open_search_page(page) -> None:
    page.goto(CONFIG["orders_search_url"])
    _wait_for_search_page(page)


def _wait_for_search_page(page) -> None:
    box = page.locator(CONFIG["order_filter_selector"]).first
    box.or_(login_form(page)).wait_for(state="visible")
    if login_form(page).is_visible():
        raise SessionExpired()


def _lookup(page, po: str) -> AmountLookup:
    from playwright.sync_api import TimeoutError as PlaywrightTimeout

    page.locator(CONFIG["order_filter_selector"]).first.fill(po)
    apply = page.locator(CONFIG["apply_button_selector"]).first
    try:
        # Apply runs submitUserAction('') → the page reloads with the results.
        with page.expect_navigation(wait_until="domcontentloaded", timeout=CONFIG["order_search_timeout_ms"]):
            apply.click()
    except PlaywrightTimeout as exc:
        raise ReportError(f"Searched PO {po}, but the In-progress orders page didn't reload.", snap(page)) from exc
    _wait_for_search_page(page)

    table = page.evaluate(
        _READ_RESULTS_JS,
        {"header": CONFIG["total_amount_header_text"], "cellClass": CONFIG["result_cell_class"]},
    )
    rows, col = table["rows"], table["col"]
    if not rows:
        return AmountLookup(po, None, note="PO not found in Infor Nexus")
    if col < 0:
        raise ReportError(
            f"Got results for PO {po}, but couldn't find the "
            f"'{CONFIG['total_amount_header_text']}' column.",
            snap(page),
        )

    exact = [r for r in rows if po in r.values()]
    matches = exact or (rows if len(rows) == 1 else [])
    if not matches:
        return AmountLookup(po, None, note=f"{len(rows)} results, none exactly PO {po}")

    raw = matches[0].get(str(col), "")
    amount = parse_amount(raw)
    note = "" if amount is not None else f"Total Amount '{raw}' is not a number"
    if len(matches) > 1:
        note = f"{len(matches)} rows for this PO; used the first. {note}".strip()
    return AmountLookup(po, amount, raw, note)


def parse_amount(text: str) -> Decimal | None:
    """'3,638.25\xa0' → Decimal('3638.25'); '(12.50)' → -12.50; '' → None."""
    t = text.replace("\xa0", " ").strip()
    negative = t.startswith("(") and t.endswith(")")
    t = re.sub(r"[^0-9.\-]", "", t)
    if not t:
        return None
    try:
        value = Decimal(t)
    except InvalidOperation:
        return None
    return -value if negative else value

_READ_RESULTS_JS = """
({header, cellClass}) => {
  const clean = s => s.replace(/\\u00a0/g, ' ').replace(/\\s+/g, ' ').trim();
  const isResultRow = r => [...r.cells].some(c => c.classList.contains(cellClass));
  const rowsOf = t => [...t.rows].filter(isResultRow).map(r => {
    const out = {}; let i = 0;
    for (const c of r.cells) { out[i] = clean(c.textContent); i += c.colSpan || 1; }
    return out;
  });
  const u = [...document.querySelectorAll('u')].find(e => clean(e.textContent) === header);
  if (!u) {
    const t = document.querySelector('td.' + cellClass)?.closest('table');
    return {col: -1, rows: t ? rowsOf(t) : []};
  }
  let cell = u.closest('td,th');
  while (cell && ![...cell.closest('table').rows].some(isResultRow)) {
    cell = cell.parentElement.closest('td,th');
  }
  if (!cell) return {col: -1, rows: []};
  let col = 0;
  for (const c of cell.parentElement.cells) { if (c === cell) break; col += c.colSpan || 1; }
  return {col, rows: rowsOf(cell.closest('table'))};
}
"""
