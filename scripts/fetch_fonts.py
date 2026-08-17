#!/usr/bin/env python3
"""Download the JetBrains Mono weights the generators subset from.

    python scripts/fetch_fonts.py

The TTFs are gitignored, so CI and fresh clones call this first.
"""

import io
import urllib.request
import zipfile
from pathlib import Path

VERSION = "2.304"
URL = (
    f"https://github.com/JetBrains/JetBrainsMono/releases/download/"
    f"v{VERSION}/JetBrainsMono-{VERSION}.zip"
)
DEST = Path(__file__).parent / "fonts"
WEIGHTS = ["Regular", "Medium", "SemiBold", "ExtraBold"]


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    wanted = {f"fonts/ttf/JetBrainsMono-{w}.ttf": f"JetBrainsMono-{w}.ttf" for w in WEIGHTS}

    if all((DEST / name).exists() for name in wanted.values()):
        print(f"fonts already present in {DEST}")
        return

    print(f"downloading JetBrains Mono {VERSION}...")
    with urllib.request.urlopen(URL, timeout=120) as resp:
        blob = resp.read()

    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        for member, name in wanted.items():
            (DEST / name).write_bytes(z.read(member))
            print(f"  {name}")


if __name__ == "__main__":
    main()
