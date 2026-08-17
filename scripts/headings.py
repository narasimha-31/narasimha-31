#!/usr/bin/env python3
"""Render each section title as an SVG, replacing the markdown ## headings.

    python scripts/headings.py

One file per section, lowercase monospace with a gradient fill and a short
rule beneath. These also stand in for the capsule-render divider bars the
README used to load from a third party.
"""

import sys
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).parent))

import palette
from fontkit import Face, advance

ROOT = Path(__file__).parent.parent

FONT_SIZE = 26
WEIGHT = 800
PAD_X = 2          # breathing room so the gradient does not clip the first stem
RULE_GAP = 9       # baseline to rule
RULE_HEIGHT = 3
HEIGHT = 46

SECTIONS = [
    ("hd-about", "about me"),
    ("hd-stack", "tech stack"),
    ("hd-projects", "projects"),
    ("hd-stats", "stats & activity"),
]


def build(text):
    face = Face(weight=WEIGHT, family="HdMono").use(text)
    width = round(advance(text, FONT_SIZE) + PAD_X * 2, 2)
    baseline = FONT_SIZE + 6
    rule_y = baseline + RULE_GAP

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{HEIGHT}" '
        f'viewBox="0 0 {width} {HEIGHT}" role="img" aria-label="{escape(text)}">'
        "<defs>"
        f'{palette.gradient_def("hg")}'
        "</defs>"
        "<style>"
        f"{face.css()}"
        f"text{{font-family:{face.stack()};font-size:{FONT_SIZE}px;font-weight:{WEIGHT};"
        f"letter-spacing:0}}"
        "</style>"
        f'<text x="{PAD_X}" y="{baseline}" fill="url(#hg)">{escape(text)}</text>'
        f'<rect x="{PAD_X}" y="{rule_y}" width="{round(width - PAD_X * 2, 2)}" '
        f'height="{RULE_HEIGHT}" rx="{RULE_HEIGHT / 2}" fill="url(#hg)" '
        f'opacity="{palette.RULE_OPACITY}"/>'
        "</svg>\n"
    )


def main():
    for name, text in SECTIONS:
        dest = ROOT / f"{name}.svg"
        dest.write_text(build(text), encoding="utf-8")
        print(f"  {dest.name:20} {text!r} ({dest.stat().st_size}B)")


if __name__ == "__main__":
    main()
