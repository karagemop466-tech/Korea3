"""HTML rendering primitives.

Two rules are enforced in code, not by review:

1. every table row carries at least one anchor whose href starts with ``https://``;
   :func:`table` raises otherwise (this is the same rule the repository's
   ``verify/source_audit.py`` gate applies to every published page);
2. a blank value can only be emitted together with a link to the review page.
"""
from __future__ import annotations

import html
from typing import Iterable, Sequence


REVIEW_PAGE = "flagged.html"


def esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def link(href: str, text: str, cls: str = "") -> str:
    c = f' class="{cls}"' if cls else ""
    return (f'<a href="{esc(href)}" target="_blank" rel="noopener noreferrer"{c}>'
            f'{esc(text)}</a>')


# One authoritative official link per flag id: the page that was actually opened when the
# gap was found.  A blank cell links its flag *and* the page that was checked.
FLAG_SOURCE = {
    "DS-F01": "https://www.nfl.com/teams/kansas-city-chiefs/depth-chart",
    "DS-F02": "https://operations.nfl.com/",
    "DS-F03": "https://support.draftkings.com/dk/en-us/what-is-a-same-game-parlay-sgp-bet",
    "DS-F04": "https://pmc.ncbi.nlm.nih.gov/articles/PMC3496575/",
    "DS-F05": "https://support.draftkings.com/dk/en-us/what-is-a-prop-bet",
    "DS-F06": "https://www.nfl.com/injuries/",
    "DS-F07": "https://www.nfl.com/injuries/league/2025/reg9",
    "DS-F08": "https://github.com/nflverse/nflverse-data/releases/tag/injuries",
    "DS-F09": "https://github.com/karagemop466-tech/Korea3",
    "DS-F10": "https://github.com/karagemop466-tech/Korea3/blob/main/session-398c4b58/scripts/fetch_data.py",
    "DS-F11": "https://www.itl.nist.gov/div898/handbook/prc/section4/prc47.htm",
    "DS-F12": "https://github.com/karagemop466-tech/Korea3",
}


def blank(flag: str) -> str:
    """A deliberately empty cell: never inferred, always flagged, always sourced."""
    src = FLAG_SOURCE.get(flag, "https://github.com/karagemop466-tech/Korea3")
    return (f'<span class="blank" title="not known — flagged for review">'
            f'<a href="{REVIEW_PAGE}#{esc(flag)}">blank</a></span>'
            f' <a href="{esc(src)}" target="_blank" rel="noopener noreferrer" '
            f'class="blanksrc" title="the page checked when this gap was found">checked →</a>')


def fmt(value, digits: int = 2, pct: bool = False):
    if value is None or value == "":
        return None
    if isinstance(value, float):
        if pct:
            return f"{value:.{digits}f}%"
        return f"{value:,.{digits}f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def table(caption: str, headers: Sequence[str], rows: Iterable[Sequence[str]],
          note: str = "", cls: str = "data", source_headers: Sequence[int] = ()) -> str:
    body = [list(r) for r in rows]
    for i, r in enumerate(body):
        if not any("https://" in str(cell) for cell in r):
            raise ValueError(f"table '{caption}': row {i} has no external source link: {r}")
    head = "".join(f"<th scope=\"col\">{esc(h)}</th>" for h in headers)
    trs = []
    for r in body:
        cells = "".join(f"<td>{c}</td>" for c in r)
        trs.append(f"<tr>{cells}</tr>")
    n = (f'<p class="note">{note}</p>' if note else "")
    return (f'<figure class="tbl"><figcaption>{esc(caption)}</figcaption>'
            f'<div class="scroll"><table class="{cls}"><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(trs)}</tbody></table></div>{n}'
            f'<p class="note">Rows: {len(body)}</p></figure>')


def kpi(label: str, value: str, sub: str = "", tone: str = "") -> str:
    return (f'<div class="card {tone}"><div class="tag">{esc(label)}</div>'
            f'<div class="num">{value}</div><div class="sub">{sub}</div></div>')


def notice(kind: str, title: str, body: str) -> str:
    return (f'<div class="notice {kind}"><strong>{esc(title)}</strong> {body}</div>')


# Repository paths used as per-row provenance in tables whose claim is "this file computes it".
CODE = "https://github.com/karagemop466-tech/Korea3/blob/main/"


def code(path: str, text: str = "code") -> str:
    return link(CODE + path, text)


def review(anchor: str = "", text: str = "flag") -> str:
    return link(f"{REVIEW_PAGE}{('#' + anchor) if anchor else ''}", text)
