#!/usr/bin/env python3
"""Shared colors for every generated SVG.

No prefers-color-scheme anywhere. An SVG loaded through <img> reads the OS
theme, not GitHub's site theme, so the query hands a light-OS/dark-GitHub
visitor the wrong palette. Instead every color here is a mid-tone chosen to
hold up on both grounds. The numbers below are WCAG contrast ratios against
GitHub dark (#0d1117) and white, computed in scripts/palette.py --check.

The three accents are the data-pipeline.svg brand hues nudged toward the
luminance midpoint: same identity, readable either way.
"""

DARK_GROUND = "#0d1117"
LIGHT_GROUND = "#ffffff"

BLUE = "#1681b6"    # 4.37 dark / 4.33 light
PURPLE = "#8e64ce"  # 4.38 / 4.32
PINK = "#e62d4e"    # 4.37 / 4.33

INK = "#6e7781"     # 4.16 / 4.55 -- primary labels
DIM = "#768390"     # 4.88 / 3.87 -- secondary labels, axis text
GRID = "#6e7781"    # structural rules and empty grid cells

# Contrast peaks at the luminance midpoint, so a color cannot be both balanced
# and faint -- any color dim enough to recede on white leaps out on dark. Where
# something should sit quietly (empty calendar cells, rules) use a balanced hue
# at reduced fill-opacity instead: opacity blends toward whichever ground it is
# actually on, so it stays subtle in both.
GRID_OPACITY = 0.30
RULE_OPACITY = 0.45

ACCENTS = [BLUE, PURPLE, PINK]

# Gradient stops, left to right, used by headings and card rules.
GRADIENT = [(0.0, BLUE), (0.5, PURPLE), (1.0, PINK)]


def _luminance(hex_color):
    h = hex_color.lstrip("#")
    channels = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    channels = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast(a, b):
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def gradient_def(ident, x1="0", y1="0", x2="1", y2="0"):
    stops = "".join(
        f'<stop offset="{off}" stop-color="{color}"/>' for off, color in GRADIENT
    )
    return f'<linearGradient id="{ident}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">{stops}</linearGradient>'


def _check():
    print(f"{'name':8} {'hex':9} {'on dark':>8} {'on light':>9} {'min':>6}")
    for name in ("BLUE", "PURPLE", "PINK", "INK", "DIM", "GRID"):
        value = globals()[name]
        d, l = contrast(value, DARK_GROUND), contrast(value, LIGHT_GROUND)
        print(f"{name:8} {value:9} {d:8.2f} {l:9.2f} {min(d, l):6.2f}")


if __name__ == "__main__":
    _check()
