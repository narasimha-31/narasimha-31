#!/usr/bin/env python3
"""Render data-pipeline.svg, the banner at the top of the README.

    python scripts/pipeline.py

Replaces the hand-authored file and the regex patcher that used to retrofit
fonts into it. Every word is the original wording. What changed:

  flow        a connector per gap at card height, left to right: a faint
              static rail with small dots travelling along it. The rail is
              what you see at rest, the dots are the flow
  colors      sixteen ad-hoc hexes down to the shared palette
  theme       no hardcoded #0d1117 card fill or #e6edf3 text, so the card
              sits on light and dark grounds instead of looking like a dark
              widget pasted onto a white page
  motion      nine indefinite SMIL loops became CSS, so prefers-reduced-motion
              can stop them; SMIL cannot be disabled that way. Also slowed:
              dots sprinting between stages read as busy, not as flow
  type        the embedded subset face, applied at render time rather than
              patched in afterwards
"""

import sys
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).parent))

import palette
from fontkit import FaceSet, advance

TARGET = Path(__file__).parent.parent / "data-pipeline.svg"

W, H = 1060, 300
NAME = "NARASIMHA ROYAL"
TAGLINE = "DATA ANALYST  ·  PYTHON  ·  SQL  ·  BI"
FOOTER = "MESSY DATA → VALIDATED → MODELED → INSIGHT → DECISION"

STAGES = [
    ("SOURCES", "APIs · files · DB"),
    ("SQL", "extract · join"),
    ("VALIDATE", "quality · reconcile"),
    ("MODEL", "clean tables"),
    ("INSIGHT", "Power BI · Tableau"),
    ("DECISION", "people act on it"),
]
BAD_ROWS = ("~150 BAD ROWS", "CAUGHT WEEKLY")

# Cards are 132 rather than the original 120. The longest sublabel,
# "quality · reconcile", is 19 characters, which at 10.5px monospace measures
# 119.7 -- it touched both borders of a 120 card. Widening the card keeps the
# label at a readable size instead of shrinking type to fit.
CARD_W, CARD_H, GAP = 132, 74, 36
CARD_Y = 110
GRID_X = 44

# Connectors sit at card height, one per gap, running left to right between
# adjacent cards. Each gap is a faint static rail with small dots travelling
# along it: the rail is what you see at rest, the dots are the flow.
MID_Y = CARD_Y + CARD_H / 2
BRANCH_TOP = CARD_Y + CARD_H
BOX_Y, BOX_W, BOX_H = 224, 136, 42


def card_x(i):
    return GRID_X + i * (CARD_W + GAP)


def _sample(i):
    """Each card takes its color from the gradient, left to right."""
    from stats import gradient_samples
    return gradient_samples(len(STAGES))[i]


def build():
    faces = FaceSet(500, 600, 800)
    faces[800].use(NAME, *(t for t, _ in STAGES), BAD_ROWS[0])
    faces[600].use(TAGLINE, BAD_ROWS[1], FOOTER)
    faces[500].use(*(s for _, s in STAGES))

    colors = [_sample(i) for i in range(len(STAGES))]
    validate_x = card_x(2) + CARD_W / 2

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" '
        f'height="{H}" fill="none" role="img" aria-label="Narasimha Royal, Data Analyst. '
        f'From messy data to trusted decisions: sources, SQL, validation, modeling, '
        f'insight, decision.">',
        "<defs>",
        palette.gradient_def("gem"),
        "</defs>",
        "<style>",
        faces.css(),
        # One-shot entrance for the cards, continuous flow on the connectors.
        # Both sit inside the reduced-motion guard: the dots march forever, and
        # perpetual motion nobody can stop is a genuine accessibility problem.
        "@keyframes rise{from{opacity:0;transform:translateY(7px)}"
        "to{opacity:1;transform:translateY(0)}}"
        "@keyframes march{to{stroke-dashoffset:-9.1}}"
        "@keyframes fall{"
        "0%{transform:translateY(0);opacity:0}"
        "12%{opacity:1}88%{opacity:1}"
        "100%{transform:translateY(40px);opacity:0}}"
        "@media not all and (prefers-reduced-motion: reduce){"
        "g.card{opacity:0;animation:rise .5s ease-out forwards}"
        + "".join(f"g.c{i}{{animation-delay:{i * 0.08:.2f}s}}" for i in range(len(STAGES)))
        + # 2.4s, not 0.55s. Dots sprinting between stages read as busy;
        # a slow drift reads as flow.
        "line.flow{animation:march 1.1s linear infinite}"
        "circle.drop{animation:fall 2.6s linear infinite}"
        "circle.d2{animation-delay:1.3s}"
        "}",
        "</style>",
    ]

    parts.append(
        f'<text x="{W / 2}" y="46" text-anchor="middle" fill="url(#gem)" font-size="38" '
        f'font-weight="800" font-family={faces[800].stack()!r} letter-spacing="2">'
        f"{escape(NAME)}</text>"
    )
    parts.append(
        f'<text x="{W / 2}" y="74" text-anchor="middle" fill="{palette.DIM}" font-size="14" '
        f'font-weight="600" font-family={faces[600].stack()!r} letter-spacing="5">'
        f"{escape(TAGLINE)}</text>"
    )

    # A connector per gap: static rail, then dots running along it.
    for i in range(len(STAGES) - 1):
        x1 = card_x(i) + CARD_W + 3
        x2 = card_x(i + 1) - 3
        parts.append(
            f'<line x1="{x1}" y1="{MID_Y}" x2="{x2}" y2="{MID_Y}" '
            f'stroke="url(#gem)" stroke-width="1.5" opacity="0.28"/>'
            f'<line class="flow" x1="{x1}" y1="{MID_Y}" x2="{x2}" y2="{MID_Y}" '
            f'stroke="url(#gem)" stroke-width="4.5" stroke-linecap="round" '
            f'stroke-dasharray="0.1 9"/>'
        )

    # Reject branch, leaving the validation gate.
    parts.append(
        f'<line x1="{validate_x}" y1="{BRANCH_TOP}" x2="{validate_x}" y2="{BOX_Y}" '
        f'stroke="{palette.PINK}" stroke-width="2" stroke-dasharray="3 4" opacity="0.55"/>'
    )
    for n in range(2):
        cls = "drop" if n == 0 else "drop d2"
        parts.append(
            f'<circle class="{cls}" r="3" cx="{validate_x}" cy="{BRANCH_TOP}" '
            f'fill="{palette.PINK}" opacity="0"/>'
        )

    box_x = validate_x - BOX_W / 2
    parts.append(
        f'<rect x="{box_x}" y="{BOX_Y}" width="{BOX_W}" height="{BOX_H}" rx="9" '
        f'fill="none" stroke="{palette.PINK}" stroke-width="1.4"/>'
        f'<text x="{validate_x}" y="{BOX_Y + 17}" text-anchor="middle" fill="{palette.PINK}" '
        f'font-size="11.5" font-weight="800" font-family={faces[800].stack()!r}>'
        f"{escape(BAD_ROWS[0])}</text>"
        f'<text x="{validate_x}" y="{BOX_Y + 33}" text-anchor="middle" fill="{palette.DIM}" '
        f'font-size="10" font-weight="600" font-family={faces[600].stack()!r} '
        f'letter-spacing="1">{escape(BAD_ROWS[1])}</text>'
    )

    # Stage cards.
    for i, ((title, sub), color) in enumerate(zip(STAGES, colors)):
        x = card_x(i)
        cx = x + CARD_W / 2
        parts.append(
            f'<g class="card c{i}">'
            f'<rect x="{x}" y="{CARD_Y}" width="{CARD_W}" height="{CARD_H}" rx="12" '
            f'fill="none" stroke="{color}" stroke-width="1.6" opacity="0.75"/>'
            f'<rect x="{x + 12}" y="{CARD_Y + 11}" width="{CARD_W - 24}" height="3.5" rx="2" '
            f'fill="{color}"/>'
            f'<text x="{cx}" y="{CARD_Y + 42}" text-anchor="middle" fill="{palette.INK}" '
            f'font-size="15" font-weight="800" font-family={faces[800].stack()!r}>'
            f"{escape(title)}</text>"
            f'<text x="{cx}" y="{CARD_Y + 60}" text-anchor="middle" fill="{palette.DIM}" '
            f'font-size="10.5" font-weight="500" font-family={faces[500].stack()!r}>'
            f"{escape(sub)}</text>"
            f"</g>"
        )

    parts.append(
        f'<text x="{W / 2}" y="286" text-anchor="middle" fill="{palette.DIM}" font-size="11.5" '
        f'font-weight="600" font-family={faces[600].stack()!r} letter-spacing="1">'
        f"{escape(FOOTER)}</text>"
    )
    parts.append("</svg>\n")
    return "".join(parts)


def main():
    TARGET.write_text(build(), encoding="utf-8")
    print(f"{TARGET.name}: {TARGET.stat().st_size:,}B")


if __name__ == "__main__":
    main()
