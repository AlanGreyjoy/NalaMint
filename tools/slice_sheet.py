#!/usr/bin/env python3
"""Cut a generated icon sheet (equal grid, transparent background) into icons.

Usage: tools/slice_sheet.py SHEET.png COLS ROWS name1 name2 ... [--out src/icons/apps] [--size 512]

Each cell is cropped to its visible pixels, centered on a square canvas with a
little margin, and saved as <out>/<name>.png at --size. Pass '-' as a name to
skip a cell. With --blobs, icons are found as separate opaque shapes (sorted
into rows, then left to right) instead of by grid cells: use it when the
generator didn't keep icons inside equal cells.
"""
import argparse
from pathlib import Path

from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("sheet")
ap.add_argument("cols", type=int)
ap.add_argument("rows", type=int)
ap.add_argument("names", nargs="+")
ap.add_argument("--out", default="src/icons/apps")
ap.add_argument("--size", type=int, default=512)
ap.add_argument("--margin", type=float, default=0.04, help="transparent margin, share of the size")
ap.add_argument("--blobs", action="store_true",
                help="find icons as separate opaque shapes instead of fixed grid cells")
ap.add_argument("--uniform", action="store_true",
                help="scale every icon by the same factor (keeps relative sizes); icons sit on a shared baseline")
ap.add_argument("--alpha-floor", type=int, default=8,
                help="pixels at or below this alpha become fully transparent (generators leave alpha-1 specks)")
a = ap.parse_args()

sheet = Image.open(a.sheet).convert("RGBA")
# Clear near-invisible specks so their color can't bleed into edges when scaled
alpha = sheet.getchannel("A").point(lambda v: 0 if v <= a.alpha_floor else v)
sheet.putalpha(alpha)
sheet = Image.composite(sheet, Image.new("RGBA", sheet.size, (0, 0, 0, 0)), alpha.point(lambda v: 255 if v else 0))
if sheet.getextrema()[3][0] > 10:
    raise SystemExit("sheet has no transparent background (alpha never near 0)")
cw, ch = sheet.width / a.cols, sheet.height / a.rows
out = Path(a.out)
out.mkdir(parents=True, exist_ok=True)

crops = {}


def find_blobs(img, core=200, step=2):
    """Bounding boxes of opaque shapes (alpha > core), sampled every `step` px."""
    a = img.getchannel("A")
    w, h = img.width // step, img.height // step
    small = a.resize((w, h), Image.NEAREST).load()
    seen = [[False] * w for _ in range(h)]
    boxes = []
    for y0 in range(h):
        for x0 in range(w):
            if seen[y0][x0] or small[x0, y0] <= core:
                continue
            stack, box, n = [(x0, y0)], [x0, y0, x0, y0], 0
            seen[y0][x0] = True
            while stack:
                x, y = stack.pop()
                n += 1
                box = [min(box[0], x), min(box[1], y), max(box[2], x), max(box[3], y)]
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if 0 <= nx < w and 0 <= ny < h and not seen[ny][nx] and small[nx, ny] > core:
                        seen[ny][nx] = True
                        stack.append((nx, ny))
            if n * step * step > 0.02 * cw * ch:          # ignore specks
                boxes.append(tuple(v * step for v in box))
    # rows: group by vertical center, then left to right
    boxes.sort(key=lambda b: (b[1] + b[3]) / 2)
    rows, row = [], []
    for b in boxes:
        if row and (b[1] + b[3]) / 2 - (row[0][1] + row[0][3]) / 2 > ch / 2:
            rows.append(row)
            row = []
        row.append(b)
    rows.append(row)
    return [b for r in rows for b in sorted(r, key=lambda b: b[0])]


if a.blobs:
    boxes = find_blobs(sheet)
    names = [n for n in a.names if n != "-"]
    if len(boxes) != len(names):
        raise SystemExit(f"found {len(boxes)} shapes but got {len(names)} names")
    pad = 4
    for i, (name, (x1, y1, x2, y2)) in enumerate(zip(names, boxes)):
        crop = sheet.crop((max(0, x1 - pad), max(0, y1 - pad), min(sheet.width, x2 + pad), min(sheet.height, y2 + pad)))
        mask = crop.getchannel("A").point(lambda v: 255 if v > 24 else 0)
        crops[name] = (i, crop.crop(mask.getbbox()))
else:
  for i, name in enumerate(a.names):
    if name == "-":
        continue
    col, row = i % a.cols, i // a.cols
    cell = sheet.crop((round(col * cw), round(row * ch), round((col + 1) * cw), round((row + 1) * ch)))
    # ignore faint shadow pixels when finding the icon's extent
    mask = cell.getchannel("A").point(lambda v: 255 if v > 24 else 0)
    box = mask.getbbox()
    if not box:
        raise SystemExit(f"cell {i} ({name}) is empty")
    crops[name] = (i, cell.crop(box))

# --uniform: one scale for the whole sheet, so relative sizes survive
# (e.g. a full trash can is taller than an empty one)
common = max(max(icon.size) for _, icon in crops.values())
for name, (i, icon) in crops.items():
    side = common if a.uniform else max(icon.size)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.alpha_composite(icon, ((side - icon.width) // 2, side - icon.height - (side - common) // 2
                                  if a.uniform else (side - icon.height) // 2))
    inner = round(a.size * (1 - 2 * a.margin))
    canvas = canvas.resize((inner, inner), Image.LANCZOS)
    final = Image.new("RGBA", (a.size, a.size), (0, 0, 0, 0))
    final.alpha_composite(canvas, ((a.size - inner) // 2, (a.size - inner) // 2))
    final.save(out / f"{name}.png")
    print(f"{out / (name + '.png')}  from cell {i}, visible {icon.size}")
