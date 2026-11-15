#!/usr/bin/env python3
"""Zoomed contact sheet of a window's four frame corners.

Usage: tools/corners.py "Window Title" out.png [--size 28] [--zoom 5]
Uses Cinnamon's frame rect, so it works for client-side and server-side frames.
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent

ap = argparse.ArgumentParser()
ap.add_argument("title")
ap.add_argument("out")
ap.add_argument("--size", type=int, default=28)
ap.add_argument("--zoom", type=int, default=5)
a = ap.parse_args()

js = ("let w = global.get_window_actors().map(x => x.meta_window)"
      f".find(w => w.get_title() == {json.dumps(a.title)});"
      "let f = w.get_frame_rect(); JSON.stringify([f.x, f.y, f.width, f.height])")
res = subprocess.run([sys.executable, str(HERE / "ceval.py"), js], capture_output=True, text=True)
x, y, w, h = json.loads(json.loads(res.stdout))
subprocess.run(["wmctrl", "-F", "-a", a.title])
subprocess.run(["sleep", "0.5"])

with tempfile.TemporaryDirectory() as tmp:
    full = Path(tmp) / "full.png"
    subprocess.run(["gnome-screenshot", "-f", str(full)], check=True, capture_output=True)
    img = Image.open(full).convert("RGB")

s, z = a.size, a.zoom
spots = [(x, y), (x + w, y), (x, y + h), (x + w, y + h)]
tile = s * 2 * z
sheet = Image.new("RGB", (tile * 4 + 30, tile), (255, 0, 255))
for i, (cx, cy) in enumerate(spots):
    crop = img.crop((cx - s, cy - s, cx + s, cy + s)).resize((tile, tile), Image.NEAREST)
    sheet.paste(crop, (i * (tile + 10), 0))
sheet.save(a.out)
print(a.out, (x, y, w, h))
