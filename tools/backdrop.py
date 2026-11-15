#!/usr/bin/env python3
"""Plain window to put behind test windows (and keep other windows out of screenshots).
Usage: tools/backdrop.py '#f0f0f0' X Y W H
       tools/backdrop.py path/to/image.png X Y W H   (image scaled to cover)"""
import os
import sys
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk  # noqa: E402

color, x, y, w, h = sys.argv[1], *map(int, sys.argv[2:6])
win = Gtk.Window(title="NalaMint Backdrop")
win.set_decorated(False)
win.set_type_hint(Gdk.WindowTypeHint.UTILITY)  # not rounded by the extension
win.set_skip_taskbar_hint(True)                 # keep it out of the dock
win.move(x, y)
win.set_default_size(w, h)
css = Gtk.CssProvider()
if os.path.isfile(color):
    path = os.path.abspath(color)
    css.load_from_data(f"window {{ background: url('file://{path}') center / cover no-repeat; }}".encode())
else:
    css.load_from_data(f"window {{ background: {color}; }}".encode())
Gtk.StyleContext.add_provider_for_screen(win.get_screen(), css, 900)
win.connect("destroy", Gtk.main_quit)
win.show_all()
Gtk.main()
