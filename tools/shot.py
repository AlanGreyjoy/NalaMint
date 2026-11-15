#!/usr/bin/env python3
"""Screenshot one window (with its frame and shadow) by exact title.

Usage: tools/shot.py "Window Title" out.png [--margin 40] [--scale 1.0]
       tools/shot.py --region X Y W H out.png
"""
import argparse
import re
import subprocess
import tempfile
import time
from pathlib import Path

from PIL import Image


def window_rect(title):
    info = subprocess.run(["xwininfo", "-name", title], capture_output=True,
                          text=True, check=True).stdout
    num = lambda label: int(re.search(label + r":\s+(-?\d+)", info).group(1))
    x, y = num("Absolute upper-left X"), num("Absolute upper-left Y")
    w, h = num("Width"), num("Height")
    wid = re.search(r"Window id: (0x[0-9a-f]+)", info).group(1)
    props = subprocess.run(["xprop", "-id", wid, "_NET_FRAME_EXTENTS"],
                           capture_output=True, text=True).stdout
    m = re.search(r"= (\d+), (\d+), (\d+), (\d+)", props)
    if m:  # server-side frame: grow the rect to include it
        left, right, top, bottom = map(int, m.groups())
        x, y, w, h = x - left, y - top, w + left + right, h + top + bottom
    return x, y, w, h


def grab(x, y, w, h, out, scale=1.0):
    with tempfile.TemporaryDirectory() as tmp:
        full = Path(tmp) / "full.png"
        subprocess.run(["gnome-screenshot", "-f", str(full)], check=True,
                       capture_output=True)
        img = Image.open(full).crop((x, y, x + w, y + h))
    if scale != 1.0:
        img = img.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
    img.save(out)
    print(f"{out}  ({x},{y} {w}x{h})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("target", nargs="*")
    ap.add_argument("--region", nargs=4, type=int)
    ap.add_argument("--margin", type=int, default=40)
    ap.add_argument("--scale", type=float, default=1.0)
    a = ap.parse_args()
    if a.region:
        grab(*a.region, a.target[0], a.scale)
    else:
        title, out = a.target
        subprocess.run(["wmctrl", "-a", title])  # raise so nothing covers it
        time.sleep(0.5)
        x, y, w, h = window_rect(title)
        m = a.margin
        grab(x - m, y - m, w + 2 * m, h + 2 * m, out, a.scale)
