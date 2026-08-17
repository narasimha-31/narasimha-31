#!/usr/bin/env python3
"""Subset JetBrains Mono to exactly the glyphs an SVG draws, inline as woff2.

This is load-bearing, not cosmetic. Without an embedded face the viewer falls
back to whatever monospace they have, the advance width stops being 0.600em,
and every character grid in this repo shears. Subsetting keeps that guarantee
affordable: a face carrying five glyphs is well under 1KB.

    from fontkit import Face
    face = Face(weight=600)
    face.use("Total commits 1,247")
    svg = f"<style>{face.css()}</style>..."
"""

import base64
import io
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

FONT_DIR = Path(__file__).parent / "fonts"

# JetBrains Mono ships discrete weights. Synthetic bolding would smear the
# glyphs and break the fixed advance, so each weight is a real file.
WEIGHT_FILES = {
    400: "JetBrainsMono-Regular.ttf",
    500: "JetBrainsMono-Medium.ttf",
    600: "JetBrainsMono-SemiBold.ttf",
    800: "JetBrainsMono-ExtraBold.ttf",
}

ADVANCE_WIDTH = 0.600  # em, identical across every weight and glyph
UNITS_PER_EM = 1000

# Fixed font timestamp, in seconds since 1904-01-01 (the OpenType head epoch).
# Any constant works; it only has to be the same on every run.
EPOCH = 3_600_000_000


def advance(text, font_size):
    """Rendered width of a string. Exact, because the face is monospace."""
    return len(text) * font_size * ADVANCE_WIDTH


class Face:
    """One weight of the font, accumulating the characters an SVG needs."""

    def __init__(self, weight=400, family=None):
        if weight not in WEIGHT_FILES:
            raise ValueError(f"no vendored file for weight {weight}; have {sorted(WEIGHT_FILES)}")
        self.weight = weight
        self.family = family or f"JBM{weight}"
        self._chars = set()

    def use(self, *texts):
        """Register text that will be drawn in this weight."""
        for text in texts:
            self._chars.update(str(text))
        return self

    @property
    def path(self):
        return FONT_DIR / WEIGHT_FILES[self.weight]

    def _woff2(self):
        if not self.path.exists():
            raise SystemExit(
                f"missing font: {self.path}\n"
                "The TTFs are gitignored. Run: python scripts/fetch_fonts.py"
            )

        options = subset.Options()
        options.flavor = "woff2"
        options.hinting = False
        options.desubroutinize = True
        options.layout_features = []   # a fixed grid needs no kerning or ligatures
        options.notdef_outline = False

        # recalcTimestamp=False plus a pinned head timestamp. Otherwise fontTools
        # stamps "modified" with the current time on save, every subset comes out
        # different, and the scheduled workflow commits all nine SVGs every night
        # even when not a single number has changed.
        font = TTFont(self.path, recalcTimestamp=False)
        font["head"].created = font["head"].modified = EPOCH
        missing = sorted(c for c in self._chars if ord(c) not in font.getBestCmap())
        if missing:
            raise SystemExit(
                f"{self.path.name} has no glyph for: {missing!r}\n"
                "Pick different characters or a font that covers them."
            )

        subsetter = subset.Subsetter(options=options)
        subsetter.populate(text="".join(sorted(self._chars)))
        subsetter.subset(font)

        font.flavor = options.flavor
        buf = io.BytesIO()
        font.save(buf)
        font.close()
        return buf.getvalue()

    def css(self):
        """An @font-face rule with the subset inlined as base64."""
        if not self._chars:
            raise ValueError(f"{self.family}: nothing registered via .use()")
        blob = base64.b64encode(self._woff2()).decode("ascii")
        return (
            "@font-face{"
            f"font-family:'{self.family}';font-style:normal;font-weight:{self.weight};"
            f"src:url(data:font/woff2;base64,{blob}) format('woff2');"
            "}"
        )

    def stack(self):
        return f"'{self.family}',monospace"


class FaceSet:
    """Several weights used by one SVG."""

    def __init__(self, *weights):
        self.faces = {w: Face(w) for w in weights}

    def __getitem__(self, weight):
        return self.faces[weight]

    def css(self):
        return "".join(face.css() for face in self.faces.values() if face._chars)
