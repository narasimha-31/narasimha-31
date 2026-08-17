#!/usr/bin/env python3
"""Embed the subset font into data-pipeline.svg.

    python scripts/fix_pipeline.py

The card shipped with font-family="'Segoe UI',Roboto,Helvetica,Arial", which
resolves to a different face on every platform: Segoe UI on Windows, Roboto or
Helvetica elsewhere, each with its own metrics. Centred labels drift and the
pipeline row can overrun its card. Embedding the same subset face the rest of
the repo uses makes the card render identically everywhere.

Idempotent: rerunning strips the previously injected block and rebuilds it, so
this can run in CI alongside the other generators.
"""

import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fontkit import Face

TARGET = Path(__file__).parent.parent / "data-pipeline.svg"
MARKER_OPEN = '<style id="fontkit">'
# Consume the leading whitespace too. Stripping only the tags would leave the
# indentation behind for the next insert to pad again, so the file would drift
# by a few bytes every run and the workflow would commit it daily forever.
MARKER_RE = re.compile(r'\s*<style id="fontkit">.*?</style>', re.S)

TEXT_RE = re.compile(r"<text\b([^>]*)>(.*?)</text>", re.S)
WEIGHT_RE = re.compile(r'font-weight="(\d+)"')
FAMILY_RE = re.compile(r'font-family="[^"]*"')


def main():
    svg = TARGET.read_text(encoding="utf-8")
    svg = MARKER_RE.sub("", svg)

    faces = {}
    for attrs, body in TEXT_RE.findall(svg):
        weight = int(WEIGHT_RE.search(attrs).group(1)) if WEIGHT_RE.search(attrs) else 400
        text = html.unescape(re.sub(r"<[^>]+>", "", body))
        faces.setdefault(weight, Face(weight=weight, family=f"Pipe{weight}")).use(text)

    def swap(match):
        attrs, body = match.group(1), match.group(2)
        weight = int(WEIGHT_RE.search(attrs).group(1)) if WEIGHT_RE.search(attrs) else 400
        stack = faces[weight].stack()
        if FAMILY_RE.search(attrs):
            attrs = FAMILY_RE.sub(f'font-family="{stack.replace(chr(39), chr(39))}"', attrs)
        else:
            attrs += f' font-family="{stack}"'
        return f"<text{attrs}>{body}</text>"

    svg = TEXT_RE.sub(swap, svg)

    block = MARKER_OPEN + "".join(f.css() for f in faces.values()) + "</style>"
    if "<defs>" in svg:
        svg = svg.replace("<defs>", "<defs>\n    " + block, 1)
    else:
        svg = re.sub(r"(<svg\b[^>]*>)", r"\1\n  <defs>" + block + "</defs>", svg, count=1)

    TARGET.write_text(svg, encoding="utf-8")
    total = sum(len(f.css()) for f in faces.values())
    print(f"{TARGET.name}: embedded weights {sorted(faces)} ({total:,}B of css)")
    print(f"  size now {TARGET.stat().st_size:,}B")


if __name__ == "__main__":
    main()
