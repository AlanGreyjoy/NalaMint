#!/usr/bin/env python3
"""Launch an app, screenshot its first new window, then close that window.

Usage: tools/appshot.py out.png -- command [args...]
       [--size 1000x700] [--at 2700,120] [--wait 8] [--settle 1.5] [--keep] [--scale 0.8]

Only the window this run opened is closed (matched by Cinnamon's stable
window sequence), so the user's own windows are never touched.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def ceval(js):
    out = subprocess.run([sys.executable, str(HERE / "ceval.py"), js], capture_output=True, text=True)
    return json.loads(out.stdout) if out.returncode == 0 and out.stdout.strip() else None


WINDOWS = ("JSON.stringify(global.get_window_actors().map(a => a.meta_window)"
           ".filter(w => w.get_window_type() == 0 || w.get_window_type() == 3 || w.get_window_type() == 4)"
           ".map(w => [w.get_stable_sequence(), w.get_title() || '', w.get_wm_class() || '']))")


def windows():
    return {seq: (title, cls) for seq, title, cls in json.loads(ceval(WINDOWS) or "[]")}


def main():
    argv = sys.argv[1:]
    if "--" not in argv:
        sys.exit(__doc__)
    split = argv.index("--")
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--size", default="1000x700")
    ap.add_argument("--at", default="2700,120")
    ap.add_argument("--wait", type=float, default=8)
    ap.add_argument("--settle", type=float, default=1.5)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args(argv[:split])
    cmd = argv[split + 1:]

    before = windows()
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    seq = None
    deadline = time.time() + a.wait
    while time.time() < deadline and seq is None:
        time.sleep(0.4)
        new = [s for s in windows() if s not in before]
        seq = max(new) if new else None
    if seq is None:
        sys.exit("no new window appeared")

    w, h = (int(v) for v in a.size.split("x"))
    x, y = (int(v) for v in a.at.split(","))
    find = f"global.get_window_actors().map(a => a.meta_window).find(w => w.get_stable_sequence() == {seq})"
    if w > 0:
        ceval(f"let w = {find}; w.move_resize_frame(true, {x}, {y}, {w}, {h}); 'ok'")
    time.sleep(a.settle)
    ceval(f"let w = {find}; w.activate(global.get_current_time()); 'ok'")
    time.sleep(0.6)
    rect = ceval(f"let w = {find}; let f = w.get_frame_rect(); JSON.stringify([f.x, f.y, f.width, f.height, w.get_title()])")
    fx, fy, fw, fh, title = json.loads(rect)
    m = 16
    subprocess.run([sys.executable, str(HERE / "shot.py"), "--region", str(fx - m), str(fy - m),
                    str(fw + 2 * m), str(fh + 2 * m), a.out, "--scale", str(a.scale)],
                   stdout=subprocess.DEVNULL, check=True)
    print(f"{a.out}  [{title}] {fw}x{fh}")
    if not a.keep:
        ceval(f"let w = {find}; if (w) w.delete(global.get_current_time()); 'closed'")


if __name__ == "__main__":
    main()
