from __future__ import annotations

import io
import json
import re
import time
import zipfile
from dataclasses import dataclass
from typing import Callable, Iterable

from .common import SessionExpired, login_form
from .config import CONFIG


@dataclass
class PoDetails:
    po: str
    buyer: str = ""
    destination: str = ""
    note: str = ""
    debug_zip: bytes | None = None

    @property
    def complete(self) -> bool:
        return bool(self.buyer and self.destination)


ProgressFn = Callable[[int, int, str], None]


def fetch_po_details(page, pos: Iterable[str], on_progress: ProgressFn | None = None) -> dict[str, PoDetails]:
    pos = list(pos)
    results: dict[str, PoDetails] = {}
    debug_taken = False
    search = _GlobalSearch(page)
    for i, po in enumerate(pos):
        if on_progress:
            on_progress(i, len(pos), po)
        details, seen = _details_for(page, search, po)
        if not details.complete and not debug_taken:
            details.debug_zip = _debug_zip(page, po, details.note, seen)
            debug_taken = True
        results[po] = details
    if on_progress:
        on_progress(len(pos), len(pos), "")
    return results


# for one PO
def _details_for(page, search: "_GlobalSearch", po: str) -> tuple[PoDetails, list]:
    links = search.find(po)
    if links is None:
        secs = CONFIG["search_result_timeout_ms"] // 1000
        return PoDetails(po, note=f"No search result for this PO (waited {secs} s)"), []

    labels = [CONFIG["buyer_label"], CONFIG["destination_label"]]
    wanted_type = CONFIG["search_result_type_order"].lower()
    has_any = lambda card: any(card["fields"].values())

    deadline = time.monotonic() + CONFIG["search_card_fields_wait_ms"] / 1000
    while True:
        found = _read_cards(links, labels)
        orders = [r for r in found if wanted_type in (t.lower() for t in r["types"])]
        loaded = has_any(orders[0]) if orders else any(has_any(r) for r in found)
        if loaded or time.monotonic() > deadline:
            break
        page.wait_for_timeout(_POLL_MS)

    if not orders:
        kinds = sorted({t for r in found for t in r["types"] if t}) or ["unknown type"]
        return PoDetails(po, note=f"No '{CONFIG['search_result_type_order']}' result (found: {', '.join(kinds[:5])})"), found

    pick = orders[0]
    buyer, destination = pick["fields"][labels[0]], pick["fields"][labels[1]]
    note = "" if len(orders) == 1 else f"{len(orders)} Order results; used the first"
    missing = [name for name, value in ((labels[0], buyer), (labels[1], destination)) if not value]
    if missing:
        note = f"{' and '.join(missing)} not found in the search result. {note}".strip()
    return PoDetails(po, buyer, destination, note), found


_POLL_MS = 100


class _GlobalSearch:
    """Types POs into the top search box (#navbarsearch) and presses Enter.

    Like Total Amount, the page is opened only ONCE: every next PO is typed into the same
    search box while the previous results panel is still open (results are matched to the
    exact PO, so old results are never mixed up).
    Until retyping has worked once, a retyped PO without a result is searched again on a
    freshly opened OrdersView; if THAT finds it, retyping doesn't work on this site and every
    later PO gets a fresh page (the old, slower way)."""

    def __init__(self, page):
        self.page = page
        self.opened = False
        self.retype = True
        self.proven = False

    def find(self, po: str):
        """→ the visible result links for exactly this PO, or None."""
        if not (self.opened and self.retype) or not self._type(po, quick=True):
            return self._fresh(po)
        wait = CONFIG["search_result_timeout_ms"] if self.proven else CONFIG["search_retype_wait_ms"]
        links = _wait_for_result_links(self.page, po, wait)
        if links is not None:
            self.proven = True
            return links
        if self.proven:  # retyping
            return None
        links = self._fresh(po)
        if links is not None:
            self.retype = False
        return links

    def _fresh(self, po: str):
        self.page.goto(CONFIG["orders_view_url"])
        box = self.page.locator(CONFIG["global_search_selector"]).first
        box.or_(login_form(self.page)).wait_for(state="visible")
        if login_form(self.page).is_visible():
            raise SessionExpired()
        self._type(po)
        self.opened = True
        return _wait_for_result_links(self.page, po, CONFIG["search_result_timeout_ms"])

    def _type(self, po: str, quick: bool = False) -> bool:
        """PO in the search box → Enter. quick=True: don't wait if the box can't be used now."""
        box = self.page.locator(CONFIG["global_search_selector"]).first
        try:
            if quick and not box.is_visible():
                return False
            box.click(timeout=2_000 if quick else None)
            box.fill(po)
            box.press("Enter")
            return True
        except Exception:
            if not quick:
                raise
            return False


def _wait_for_result_links(page, po: str, timeout_ms: int):
    exact = re.compile(rf"^\s*{re.escape(po)}\s*$")
    selector = CONFIG["search_result_link_selector"] + ":visible"
    deadline = time.monotonic() + timeout_ms / 1000
    while True:
        if login_form(page).is_visible():
            raise SessionExpired()
        for frame in page.frames:
            try:
                links = frame.locator(selector).filter(has_text=exact)
                if links.count():
                    return links
            except Exception:
                pass
        if time.monotonic() > deadline:
            return None
        page.wait_for_timeout(_POLL_MS)


def _read_cards(links, labels) -> list[dict]:
    args = {"typeSel": CONFIG["search_result_type_selector"],
            "valueSel": CONFIG["search_result_value_selector"], "labels": labels}
    cards = []
    for i in range(links.count()):
        try:
            cards.append(links.nth(i).evaluate(_READ_CARD_JS, args))
        except Exception:
            pass
    return cards


# troubleshooting file
def _debug_zip(page, po: str, note: str, seen: list) -> bytes | None:
    """screenshot.png + one HTML file per frame (shadow DOM included, hidden elements
    marked data-hidden) + info.txt. Nothing is stored on the server; the user downloads it."""
    try:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            frames = []
            for i, frame in enumerate(page.frames):
                frames.append(frame.url)
                try:
                    z.writestr(f"frame_{i}.html", frame.evaluate(_SERIALIZE_JS))
                except Exception as exc:
                    z.writestr(f"frame_{i}_error.txt", str(exc))
            try:
                z.writestr("screenshot.png", page.screenshot(full_page=True))
            except Exception:
                pass
            z.writestr("info.txt", "\n".join([
                f"PO: {po}",
                f"Note: {note}",
                f"Page URL: {page.url}",
                "Frames:", *[f"  frame_{i}: {u}" for i, u in enumerate(frames)],
                "What the app read from the result card(s):",
                json.dumps(seen, indent=2, ensure_ascii=False),
                "Settings used:",
                json.dumps({k: v for k, v in CONFIG.items() if k.startswith(("search_", "global_", "buyer", "destination"))},
                           indent=2),
            ]))
        return buf.getvalue()
    except Exception:
        return None


# JavaScript run inside the page
# Reads a "label → value" pair. The label is a visible element whose own text is the label
# (<span>Buyer</span>). The value sits in a value wrapper (valueSel):
#   <span class="core-focus-link"><span>THE GAP, INC.</span></span>        → "THE GAP, INC."
#   <span class="core-focus-link …"><a class="coreLink">EAO - 0004</a>…</span> → "EAO - 0004"
# 1st try (HTML order): the first visible text after the label must be inside a value wrapper.
# 2nd try (screen layout): the nearest value wrapper on the same line, right of the label,
#   with no other text in between.
# Hidden elements (e.g. a compact copy of the fields for small screens) are ignored.
_READ_FIELD_JS = """
const clean = s => (s || '').replace(/\\u00a0/g, ' ').replace(/\\s+/g, ' ').trim();
const empty = s => /^[\\s.·…:]*$/.test(clean(s));
const ownText = e => [...e.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join('');
const shown = e => e.getClientRects().length > 0;
const valueText = w => { const a = w.matches('a') ? w : w.querySelector('a'); return clean((a || w).textContent); };
const labelEls = (root, label) => {
  const want = label.toLowerCase();
  return [...root.querySelectorAll('*')].filter(e =>
    shown(e) && clean(ownText(e)).replace(/[\\s.…:]+$/, '').toLowerCase() === want);
};
const byOrder = (root, el, valueSel) => {
  const walk = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
  walk.currentNode = el;
  let n = walk.nextNode();
  while (n && el.contains(n)) n = walk.nextNode();          // skip the label's own insides
  for (; n; n = walk.nextNode()) {
    if (!shown(n) || empty(ownText(n))) continue;
    const wrap = n.closest(valueSel);
    return (wrap && root.contains(wrap)) ? valueText(wrap) : '';
  }
  return '';
};
const byLayout = (root, el, valueSel) => {
  const r = el.getBoundingClientRect(), mid = (r.top + r.bottom) / 2;
  const sameLine = q => q.top <= mid && q.bottom >= mid && q.left >= r.right - 2;
  let best = null, bestX = Infinity;
  for (const v of root.querySelectorAll(valueSel)) {
    if (!shown(v)) continue;
    const q = v.getBoundingClientRect();
    if (sameLine(q) && q.left < bestX) { best = v; bestX = q.left; }
  }
  if (!best) return '';
  for (const t of root.querySelectorAll('*')) {                 // another label in between?
    if (t === el || el.contains(t) || best.contains(t) || t.contains(el) || t.closest(valueSel)) continue;
    if (!shown(t) || empty(ownText(t))) continue;
    const q = t.getBoundingClientRect();
    if (sameLine(q) && q.left < bestX) return '';
  }
  return valueText(best);
};
const readField = (root, label, valueSel) => {
  const els = labelEls(root, label);
  for (const el of els) { const v = byOrder(root, el, valueSel); if (v) return v; }
  for (const el of els) { const v = byLayout(root, el, valueSel); if (v) return v; }
  return '';
};
"""

# Runs on one PO result link {types, fields}.
# Card = the smallest element around the link that holds a type ("Order"/"Invoice") and
# both fields. It never grows to hold another search result (other searchResultRank) or a
# second visible "Buyer" label.
_READ_CARD_JS = "(link, {typeSel, valueSel, labels}) => {" + _READ_FIELD_JS + """
  // Walk outwards from the link; a shadow root (web component) is the last step, since
  // anything outside it is the page behind the results panel.
  const up = n => (n instanceof ShadowRoot) ? null : (n.parentElement || (n.parentNode instanceof ShadowRoot ? n.parentNode : null));
  const rankOf = e => ((e.getAttribute('href') || '').match(/searchResultRank=(\\d+)/) || [])[1];
  const mine = rankOf(link);
  const otherResult = box => [...box.querySelectorAll('a[href*="searchResultRank="]')]
    .some(x => shown(x) && rankOf(x) !== mine);
  // The type label ("Order"/"Invoice") sits above the PO link; values further down may use
  // the same style, so only labels before the link count.
  const typesIn = box => [...box.querySelectorAll(typeSel)]
    .filter(e => shown(e) && (e.compareDocumentPosition(link) & Node.DOCUMENT_POSITION_FOLLOWING))
    .map(e => clean(e.textContent)).filter(Boolean);
  let best = null, levels = 0;
  for (let box = up(link), d = 0; box && box !== document.body && box !== document.documentElement && d < 25;
       box = up(box), d++) {
    if (otherResult(box) || labelEls(box, labels[0]).length > 1) break;
    levels = d + 1;
    const types = typesIn(box);
    const fields = {};
    for (const l of labels) fields[l] = readField(box, l, valueSel);
    if (types.length && labels.every(l => fields[l])) return {types, fields, levels};
    if (types.length) best = {types, fields, levels};   // biggest card that still has a type
  }
  return best || {types: [], fields: Object.fromEntries(labels.map(l => [l, ''])), levels};
}"""

# Whole frame as HTML, including shadow DOM contents; hidden elements get data-hidden="1".
_SERIALIZE_JS = """() => {
  const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const out = []; let size = 0; const MAX = 4000000;
  const walk = n => {
    if (size > MAX) return;
    if (n.nodeType === 3) { if (n.textContent.trim()) { const t = esc(n.textContent); out.push(t); size += t.length; } return; }
    if (n.nodeType !== 1) return;
    const tag = n.tagName.toLowerCase();
    if (tag === 'script' || tag === 'style' || tag === 'noscript') return;
    let s = '<' + tag;
    for (const a of n.attributes) s += ' ' + a.name + '="' + esc(a.value).replace(/"/g, '&quot;') + '"';
    if (n.getClientRects && n.getClientRects().length === 0 && tag !== 'template') s += ' data-hidden="1"';
    out.push(s + '>'); size += s.length;
    if (n.shadowRoot) { out.push('<!--shadow-root-->'); n.shadowRoot.childNodes.forEach(walk); out.push('<!--/shadow-root-->'); }
    (tag === 'template' ? n.content.childNodes : n.childNodes).forEach(walk);
    out.push('</' + tag + '>');
  };
  walk(document.documentElement);
  return out.join('\\n');
}"""

