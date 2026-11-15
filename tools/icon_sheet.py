#!/usr/bin/env python3
"""Render the built icon theme to a contact sheet.  Usage: tools/icon_sheet.py out.png [bg]"""
import sys
from pathlib import Path

import gi
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf  # noqa: E402
from PIL import Image  # noqa: E402

root = Path(__file__).resolve().parent.parent / "build/icons/NalaMint"
out, bg = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "#ececee")


def render(path, size):
    pb = GdkPixbuf.Pixbuf.new_from_file_at_size(str(path), size, size)
    mode = "RGBA" if pb.get_has_alpha() else "RGB"
    return Image.frombytes(mode, (pb.get_width(), pb.get_height()), pb.get_pixels(),
                           "raw", mode, pb.get_rowstride()).convert("RGBA")


big = [f for ctx in ("places", "apps") for f in sorted((root / ctx / "256").glob("*.png")) if not f.is_symlink()]
cols, cell = 6, 104
rows = (len(big) + cols - 1) // cols
sheet = Image.new("RGBA", (cols * cell, rows * cell + 40), bg)
for i, f in enumerate(big):
    im = render(f, 72)
    x, y = (i % cols) * cell + (cell - 72) // 2, (i // cols) * cell + 10
    sheet.alpha_composite(im, (x, y))
small = [f for ctx in ("places", "apps") for f in sorted((root / ctx / "16").glob("*.png")) if not f.is_symlink()]
for i, f in enumerate(small):
    sheet.alpha_composite(render(f, 16), (10 + i * 26, rows * cell + 12))
sheet.save(out)
print(out, len(big), "large,", len(small), "small")
