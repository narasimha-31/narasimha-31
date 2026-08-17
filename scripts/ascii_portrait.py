#!/usr/bin/env python3
"""Render a background-removed portrait PNG as an ASCII-art SVG.

    python scripts/ascii_portrait.py profile_pic.png ascii.svg

The PNG is composited onto white before any grayscale conversion, cropped to
the subject, downsampled to a character grid, and emitted as one <text> row
per line with a subsetted JetBrains Mono inlined as base64 woff2.
"""

import argparse
import base64
import io
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageEnhance, ImageOps
from fontTools import subset
from fontTools.ttLib import TTFont

# --- Tunables ---------------------------------------------------------------

COLS = 70               # character columns in the output grid
GAMMA = 1.3             # >1 lifts midtones toward the quiet end of the ramp
CONTRAST = 1.15         # ImageEnhance.Contrast factor, applied after autocontrast
RAMP = " :+#@"          # quiet -> loud; inverted below so dark pixels are loud
CROP_THRESHOLD = 245    # pixels darker than this count as subject when cropping

AUTOCONTRAST_CUTOFF = 1  # percent clipped off each end of the histogram

# --- Typography -------------------------------------------------------------
# JetBrains Mono advances 600/1000 em per glyph. Rows must be squashed by
# ADVANCE_WIDTH / LINE_HEIGHT or the face comes out vertically stretched.

FONT_PATH = Path(__file__).parent / "fonts" / "JetBrainsMono-Regular.ttf"
FONT_FAMILY = "ASCIIPortrait"
FONT_SIZE = 11
LINE_HEIGHT = 1.10
ADVANCE_WIDTH = 0.600

FILL_DARK = "#c9d1d9"   # default, for GitHub's dark theme
FILL_LIGHT = "#24292f"  # swapped in under prefers-color-scheme: light


def load_subject(path):
    """Composite onto white, grayscale, and crop to the subject's bounding box."""
    img = Image.open(path).convert("RGBA")

    # Compositing first matters: .convert("L") straight off RGBA ignores alpha,
    # so fully transparent pixels arrive as black and swamp the dark end of the ramp.
    white = Image.new("RGBA", img.size, (255, 255, 255, 255))
    gray = Image.alpha_composite(white, img).convert("L")

    mask = gray.point(lambda p: 255 if p < CROP_THRESHOLD else 0)
    bbox = mask.getbbox()
    if bbox is None:
        raise SystemExit(f"{path}: no pixels darker than {CROP_THRESHOLD}; nothing to crop to")

    return gray.crop(bbox), bbox


def to_rows(gray):
    """Downsample to the character grid and map each cell through the ramp."""
    width, height = gray.size
    rows = max(1, round(height * (COLS / width) * (ADVANCE_WIDTH / LINE_HEIGHT)))

    gray = ImageOps.autocontrast(gray, cutoff=AUTOCONTRAST_CUTOFF)
    gray = ImageEnhance.Contrast(gray).enhance(CONTRAST)
    gray = gray.resize((COLS, rows), Image.LANCZOS)

    last = len(RAMP) - 1
    pixels = list(gray.getdata())
    lines = []
    for y in range(rows):
        row = pixels[y * COLS:(y + 1) * COLS]
        # Invert (dark -> loud), then gamma-correct the darkness.
        lines.append("".join(RAMP[round(((255 - p) / 255) ** GAMMA * last)] for p in row))
    return lines


def subset_font():
    """Cut JetBrains Mono down to the ramp characters and return it as woff2 bytes."""
    if not FONT_PATH.exists():
        raise SystemExit(
            f"missing font: {FONT_PATH}\n"
            "The TTF is gitignored. Fetch it with:\n"
            "  curl -L -o jbm.zip https://github.com/JetBrains/JetBrainsMono"
            "/releases/download/v2.304/JetBrainsMono-2.304.zip\n"
            f"  unzip -j jbm.zip fonts/ttf/JetBrainsMono-Regular.ttf -d {FONT_PATH.parent}"
        )

    options = subset.Options()
    options.flavor = "woff2"
    options.hinting = False
    options.desubroutinize = True
    options.layout_features = []      # no kerning/ligatures needed for a fixed grid
    options.notdef_outline = False
    options.drop_tables += ["FFTM"]

    font = TTFont(FONT_PATH)
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(text=RAMP)     # equivalent to pyftsubset --text=" :+#@"
    subsetter.subset(font)

    font.flavor = options.flavor
    buf = io.BytesIO()
    font.save(buf)
    font.close()
    return buf.getvalue()


def build_svg(lines):
    width = round(COLS * FONT_SIZE * ADVANCE_WIDTH, 2)
    step = FONT_SIZE * LINE_HEIGHT
    height = round(len(lines) * step, 2)
    font_b64 = base64.b64encode(subset_font()).decode("ascii")

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="ASCII portrait">',
        "<style>",
        "@font-face{"
        f"font-family:'{FONT_FAMILY}';font-style:normal;font-weight:400;"
        f"src:url(data:font/woff2;base64,{font_b64}) format('woff2');"
        "}",
        f"text{{font-family:'{FONT_FAMILY}',monospace;font-size:{FONT_SIZE}px;"
        f"white-space:pre;fill:{FILL_DARK};}}",
        f"@media (prefers-color-scheme: light){{text{{fill:{FILL_LIGHT};}}}}",
        "</style>",
    ]
    for i, line in enumerate(lines):
        y = round(i * step, 2)
        out.append(
            f'<text x="0" y="{y}" xml:space="preserve" '
            f'dominant-baseline="hanging">{escape(line)}</text>'
        )
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", nargs="?", default="profile_pic.png", type=Path)
    ap.add_argument("dest", nargs="?", default="ascii.svg", type=Path)
    args = ap.parse_args()

    gray, bbox = load_subject(args.source)
    lines = to_rows(gray)
    args.dest.write_text(build_svg(lines), encoding="utf-8")

    w, h = gray.size
    print(f"{args.source} -> {args.dest}")
    print(f"  crop {bbox}  ({w}x{h})")
    print(f"  grid {COLS}x{len(lines)}")


if __name__ == "__main__":
    main()
