"""Extract FAO-56 Tables 11, 12, 22 and 24 from the official HTML edition into CSV for review.

Usage:  uv run python -u scripts/extract_fao56.py <html_dir> <out_dir>

Source: Allen, Pereira, Raes & Smith (1998), FAO Irrigation and Drainage Paper 56,
https://www.fao.org/4/x0490e/ — Chapter 6 (x0490e0b.htm: Tables 11, 12) and Chapter 8
(x0490e0e.htm: Tables 22, 24). Cells are copied as text; superscript footnote numbers are
written as ' ^n' so they never merge into values; rowspan/colspan are expanded so that
group headers (e.g. Kc ini of a crop group) stay visible next to each row. No values are edited.
"""

import csv
import html
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

TABLES = {"x0490e0b.htm": ("11", "12"), "x0490e0e.htm": ("22", "24")}


class _Tables(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self._stack = [], []

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): v for k, v in attrs}
        if tag == "table":
            self._stack.append({"rows": [], "row": None, "cell": None, "pos": self.getpos()})
        elif not self._stack:
            return
        elif tag == "tr":
            self._stack[-1]["row"] = []
        elif tag in ("td", "th"):
            self._stack[-1]["cell"] = {
                "text": [],
                "rs": int(a.get("rowspan") or 1),
                "cs": int(a.get("colspan") or 1),
            }
        elif tag == "sup" and self._stack[-1]["cell"] is not None:
            self._stack[-1]["cell"]["text"].append(" ^")  # footnote marker, kept apart from values
        elif tag == "img" and self._stack[-1]["cell"] is not None:
            self._stack[-1]["cell"]["text"].append(f"[img:{a.get('src')}]")

    def handle_endtag(self, tag):
        if not self._stack:
            return
        t = self._stack[-1]
        if tag in ("td", "th") and t["cell"] is not None:
            txt = re.sub(r"\s+", " ", "".join(t["cell"]["text"])).strip()
            t["row"].append((txt, t["cell"]["rs"], t["cell"]["cs"]))
            t["cell"] = None
        elif tag == "tr" and t["row"] is not None:
            t["rows"].append(t["row"])
            t["row"] = None
        elif tag == "table":
            self.tables.append(self._stack.pop())

    def handle_data(self, data):
        if self._stack and self._stack[-1]["cell"] is not None:
            self._stack[-1]["cell"]["text"].append(data)


def expand(rows):
    """Expand rowspan/colspan into a rectangular grid of strings."""
    grid, pending = [], {}
    for r in rows:
        out, col, it = [], 0, iter(r)
        while True:
            if col in pending and pending[col][1] > 0:
                txt, left = pending[col]
                out.append(txt)
                pending[col] = (txt, left - 1)
                col += 1
                continue
            cell = next(it, None)
            if cell is None:
                break
            txt, rs, cs = cell
            for k in range(cs):
                out.append(txt)
                if rs > 1:
                    pending[col + k] = (txt, rs - 1)
            col += cs
        grid.append(out)
    return grid


def main() -> None:
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    for page, wanted in TABLES.items():
        raw = (src / page).read_text(encoding="latin-1")
        p = _Tables()
        p.feed(raw)
        lines = raw.splitlines()
        done = set()
        for t in p.tables:
            line = t["pos"][0]
            before = html.unescape(
                re.sub(r"<[^>]+>", " ", "\n".join(lines[max(0, line - 12) : line]))
            )
            m = re.findall(r"TABLE\s+(\d+)\.", before, flags=re.I)
            if not m or m[-1] not in wanted or m[-1] in done:
                continue  # first table after its caption only (later boxes cite it)
            done.add(m[-1])
            path = out / f"fao56_table{m[-1]}.csv"
            with path.open("w", newline="", encoding="utf-8") as fh:
                csv.writer(fh).writerows(expand(t["rows"]))
            print(f"Table {m[-1]} ({page}, html line {line}): {len(t['rows'])} rows -> {path}")


if __name__ == "__main__":
    main()
