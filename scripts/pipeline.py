#!/usr/bin/env python3
"""Render data-pipeline.svg, the banner at the top of the README.

    python scripts/pipeline.py

Name, one line, then a flow diagram. The figures under the boxes are from the
Amazon reviews project.
"""

import sys
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).parent))

import palette
from fontkit import FaceSet

TARGET = Path(__file__).parent.parent / "data-pipeline.svg"

W, H = 1060, 262
NAME = "NARASIMHA ROYAL"
TAGLINE = "Data analysis and data engineering, from messy data to numbers a business can act on."

STEPS = ["Sources", "Load", "Check", "Model", "Analyze", "Report"]

# step index, text, colour, anchor
NOTES = [
    (1, "44.2M Amazon reviews", palette.DIM, "middle"),
    (2, "6,231 bad rows removed", palette.RED, "middle"),
    (5, "1,037 reviewers flagged", palette.DIM, "end"),
]

# first step, last step, name of the half
GROUPS = [(0, 3, "data engineering"), (4, 5, "data analysis")]

MARGIN = 44
BOX_W, BOX_H = 128, 44
BOX_Y = 122
PITCH = (W - 2 * MARGIN - BOX_W) / (len(STEPS) - 1)
MID_Y = BOX_Y + BOX_H / 2
NOTE_Y = BOX_Y + BOX_H + 22
GROUP_Y = NOTE_Y + 22


def box_x(i):
    return round(MARGIN + i * PITCH, 1)


def build():
    faces = FaceSet(600, 800)
    faces[800].use(NAME)
    faces[600].use(TAGLINE, *STEPS, *(n[1] for n in NOTES), *(g[2] for g in GROUPS))
    mono = repr(faces[600].stack())
    line = f'stroke="{palette.GRID}" stroke-width="1.5" opacity="0.7"'

    notes = ", ".join(n[1] for n in NOTES)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" '
        f'height="{H}" fill="none" role="img" aria-label="Narasimha Royal. Data analysis '
        f'and data engineering, from messy data to numbers a business can act on. '
        f'{" to ".join(STEPS)}. {notes}.">',
        f"<style>{faces.css()}</style>",
        f'<text x="{MARGIN}" y="58" fill="{palette.BLUE}" font-size="46" font-weight="800" '
        f'font-family={faces[800].stack()!r} letter-spacing="2">{escape(NAME)}</text>',
        f'<text x="{MARGIN}" y="87" fill="{palette.DIM}" font-size="14.5" font-weight="600" '
        f'font-family={mono}>{escape(TAGLINE)}</text>',
    ]

    for i, step in enumerate(STEPS):
        x = box_x(i)
        parts.append(
            f'<rect x="{x}" y="{BOX_Y}" width="{BOX_W}" height="{BOX_H}" rx="4" {line}/>'
            f'<text x="{x + BOX_W / 2}" y="{MID_Y + 5.5}" text-anchor="middle" '
            f'fill="{palette.INK}" font-size="16" font-weight="600" font-family={mono}>'
            f"{escape(step)}</text>"
        )
        if i:
            x1, x2 = box_x(i - 1) + BOX_W + 5, x - 5
            parts.append(
                f'<path d="M{x1} {MID_Y}H{x2}M{x2 - 6} {MID_Y - 5}L{x2} {MID_Y}L{x2 - 6} {MID_Y + 5}" '
                f'{line} stroke-linecap="round" stroke-linejoin="round"/>'
            )

    for i, text, color, anchor in NOTES:
        x = box_x(i) + (BOX_W if anchor == "end" else BOX_W / 2)
        parts.append(
            f'<text x="{x}" y="{NOTE_Y}" text-anchor="{anchor}" fill="{color}" font-size="12.5" '
            f'font-weight="600" font-family={mono}>{escape(text)}</text>'
        )

    for first, last, name in GROUPS:
        x1, x2 = box_x(first), box_x(last) + BOX_W
        parts.append(
            f'<path d="M{x1} {GROUP_Y}v7H{x2}v-7" {line} stroke-linejoin="round"/>'
            f'<text x="{(x1 + x2) / 2}" y="{GROUP_Y + 27}" text-anchor="middle" '
            f'fill="{palette.INK}" font-size="14" font-weight="600" font-family={mono}>'
            f"{escape(name)}</text>"
        )

    parts.append("</svg>\n")
    return "".join(parts)


def main():
    TARGET.write_text(build(), encoding="utf-8")
    print(f"{TARGET.name}: {TARGET.stat().st_size:,}B")


if __name__ == "__main__":
    main()
