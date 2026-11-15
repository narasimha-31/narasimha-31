#!/usr/bin/env python3
"""Render a background-removed portrait PNG as an ASCII-art SVG.

    python scripts/ascii_portrait.py profile_pic.png ascii.svg

The PNG is composited onto black before any grayscale conversion, cropped to
the subject, downsampled to a character grid, and emitted as one <text> row
per line with a subsetted JetBrains Mono inlined as base64 woff2.
"""

import argparse
import base64
import colorsys
import io
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageEnhance, ImageOps
from fontTools import subset
from fontTools.ttLib import TTFont

# --- Tunables ---------------------------------------------------------------

COLS = 70               # character columns in the output grid
GAMMA = 2.6             # >1 pushes midtones toward the quiet end of the ramp
CONTRAST = 1.0          # ImageEnhance.Contrast factor, applied after autocontrast
RAMP = " :+#@"          # quiet -> loud; bright pixels are loud
ALPHA_THRESHOLD = 10    # alpha above this counts as subject when cropping
SUBJECT_KEEP = 0.56     # keep only the top fraction of the subject, so the head fills the frame
SUBJECT_WIDTH = 0.60    # and this fraction of its width, centred on the head

AUTOCONTRAST_CUTOFF = 1  # percent clipped off each end of the histogram

# --- Reveal animation -------------------------------------------------------
# Per row, not per character: 70 columns x 29 rows would be 2030 elements.

REVEAL_DUR = 0.06       # seconds for one row to wipe in
REVEAL_STAGGER = 0.06   # seconds between consecutive row starts

# Rows draw in white, then the photo's own colours fade in.
TINT_COLORS = 10        # palette size
TINT_FLOOR = 0.62       # darkest value a colour may have, so hair stays readable on the panel
TINT_SATURATION = 1.25
TINT_DUR = 0.9
TINT_PAUSE = 0.15       # gap between the last row and the fade

# --- Typography -------------------------------------------------------------
# JetBrains Mono advances 600/1000 em per glyph. Rows must be squashed by
# ADVANCE_WIDTH / LINE_HEIGHT or the face comes out vertically stretched.

FONT_PATH = Path(__file__).parent / "fonts" / "JetBrainsMono-Regular.ttf"
FONT_FAMILY = "ASCIIPortrait"
FONT_SIZE = 11
LINE_HEIGHT = 1.10
ADVANCE_WIDTH = 0.600

# White text needs its own dark panel, or it vanishes on GitHub's light theme.
FILL = "#ffffff"
GROUND = "#0d1117"      # GitHub dark, so the panel vanishes on a dark page
PAD = 18                # panel padding around the grid, px
RADIUS = 12


def load_subject(path):
    """Composite onto black, grayscale, and crop to the subject's bounding box."""
    img = Image.open(path).convert("RGBA")

    # Composite first, transparent pixels can carry any colour underneath.
    black = Image.new("RGBA", img.size, (0, 0, 0, 255))
    gray = Image.alpha_composite(black, img).convert("L")

    mask = img.getchannel("A").point(lambda p: 255 if p > ALPHA_THRESHOLD else 0)
    bbox = mask.getbbox()
    if bbox is None:
        raise SystemExit(f"{path}: fully transparent; nothing to crop to")

    # Then keep only the top slice of the subject so the head fills the frame.
    left, top, right, bottom = bbox
    head = mask.crop((left, top, right, top + (bottom - top) // 3)).getbbox()
    centre = left + (head[0] + head[2]) / 2
    half = (right - left) * SUBJECT_WIDTH / 2
    left, right = max(left, round(centre - half)), min(right, round(centre + half))
    bbox = (left, top, right, top + int((bottom - top) * SUBJECT_KEEP))

    rgb = Image.alpha_composite(black, img).convert("RGB")
    return gray.crop(bbox), rgb.crop(bbox), img.getchannel("A").crop(bbox), bbox


def lift(rgb):
    h, s, v = colorsys.rgb_to_hsv(*(c / 255 for c in rgb))
    # near-black has no real hue, keep it grey
    s = min(1.0, s * TINT_SATURATION) * min(1.0, v / 0.2)
    v = TINT_FLOOR + (1 - TINT_FLOOR) * v
    return tuple(round(c * 255) for c in colorsys.hsv_to_rgb(h, s, v))


def to_rows(gray, rgb, alpha):
    """Downsample to the character grid; return ramp rows, palette indexes and the palette."""
    width, height = gray.size
    rows = max(1, round(height * (COLS / width) * (ADVANCE_WIDTH / LINE_HEIGHT)))

    gray = ImageOps.autocontrast(gray, cutoff=AUTOCONTRAST_CUTOFF)
    gray = ImageEnhance.Contrast(gray).enhance(CONTRAST)
    gray = gray.resize((COLS, rows), Image.LANCZOS)

    solid = [a > 127 for a in alpha.resize((COLS, rows), Image.LANCZOS).getdata()]

    tint = Image.new("RGB", (COLS, rows))
    cells = rgb.resize((COLS, rows), Image.LANCZOS).getdata()
    grey = lift((0, 0, 0))
    tint.putdata([lift(c) if ok else grey for c, ok in zip(cells, solid)])
    tint = tint.quantize(TINT_COLORS, method=Image.MEDIANCUT, dither=Image.NONE)
    flat = tint.getpalette()
    palette = [tuple(flat[i * 3:i * 3 + 3]) for i in range(TINT_COLORS)]
    index = list(tint.getdata())

    last = len(RAMP) - 1
    pixels = list(gray.getdata())
    lines, tints = [], []
    for y in range(rows):
        chars = []
        for x in range(COLS):
            i = y * COLS + x
            level = round((pixels[i] / 255) ** GAMMA * last)
            # dark hair and clothes still get a mark, or they vanish into the panel
            if solid[i]:
                level = max(level, 1)
            chars.append(RAMP[level])
        lines.append("".join(chars))
        tints.append(index[y * COLS:(y + 1) * COLS])
    return lines, tints, palette


def tint_runs(line, tint):
    """Split a row into (palette index, text) runs; spaces ride along with the run before."""
    runs = []
    for ch, t in zip(line, tint):
        if runs and (ch == " " or runs[-1][0] == t):
            runs[-1][1] += ch
        else:
            runs.append([t if ch != " " else -1, ch])
    return runs


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

    # Pinned timestamp, matching scripts/fontkit.py: fontTools would otherwise
    # stamp "modified" with the current time and every rebuild would differ.
    font = TTFont(FONT_PATH, recalcTimestamp=False)
    font["head"].created = font["head"].modified = 3_600_000_000
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(text=RAMP)     # equivalent to pyftsubset --text=" :+#@"
    subsetter.subset(font)

    font.flavor = options.flavor
    buf = io.BytesIO()
    font.save(buf)
    font.close()
    return buf.getvalue()


def build_svg(lines, tints, palette):
    step = FONT_SIZE * LINE_HEIGHT
    width = round(COLS * FONT_SIZE * ADVANCE_WIDTH + 2 * PAD, 2)
    height = round(len(lines) * step + 2 * PAD, 2)
    font_b64 = base64.b64encode(subset_font()).decode("ascii")

    # Literal per-row delays. "not all and" rather than the Media Queries 4 form
    # "not (...)", which older engines fail to parse -- same meaning, wider support.
    delays = "".join(
        f".r{i}{{animation-delay:{i * REVEAL_STAGGER:.3f}s}}" for i in range(len(lines))
    )
    colours = "".join(
        f".c{k}{{fill:#{r:02x}{g:02x}{b:02x}}}" for k, (r, g, b) in enumerate(palette)
    )
    tint_delay = (len(lines) - 1) * REVEAL_STAGGER + REVEAL_DUR + TINT_PAUSE

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="ASCII portrait">',
        "<style>",
        "@font-face{"
        f"font-family:'{FONT_FAMILY}';font-style:normal;font-weight:400;"
        f"src:url(data:font/woff2;base64,{font_b64}) format('woff2');"
        "}",
        f"text{{font-family:'{FONT_FAMILY}',monospace;font-size:{FONT_SIZE}px;"
        f"white-space:pre;fill:{FILL};opacity:1}}",
        f"{colours}"
        "@keyframes reveal{"
        "from{opacity:0;clip-path:inset(0 100% 0 0)}"
        "to{opacity:1;clip-path:inset(0 0 0 0)}"
        "}",
        "@media not all and (prefers-reduced-motion: reduce){"
        f"text{{opacity:0;animation:reveal {REVEAL_DUR}s linear forwards}}"
        f"{delays}"
        f"@keyframes tint{{from{{fill:{FILL}}}}}"
        f"tspan{{animation:tint {TINT_DUR}s ease-in-out {tint_delay:.2f}s both}}"
        "}",
        "</style>",
        f'<rect width="{width}" height="{height}" rx="{RADIUS}" fill="{GROUND}"/>',
    ]
    for i, (line, tint) in enumerate(zip(lines, tints)):
        y = round(PAD + i * step, 2)
        body = "".join(
            f'<tspan class="c{t}">{escape(text)}</tspan>' if t >= 0 else escape(text)
            for t, text in tint_runs(line, tint)
        )
        out.append(
            f'<text class="r{i}" x="{PAD}" y="{y}" xml:space="preserve" '
            f'dominant-baseline="hanging">{body}</text>'
        )
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", nargs="?", default="profile_pic.png", type=Path)
    ap.add_argument("dest", nargs="?", default="ascii.svg", type=Path)
    args = ap.parse_args()

    gray, rgb, alpha, bbox = load_subject(args.source)
    lines, tints, palette = to_rows(gray, rgb, alpha)
    args.dest.write_text(build_svg(lines, tints, palette), encoding="utf-8")

    w, h = gray.size
    print(f"{args.source} -> {args.dest}")
    print(f"  crop {bbox}  ({w}x{h})")
    print(f"  grid {COLS}x{len(lines)}")


if __name__ == "__main__":
    main()
