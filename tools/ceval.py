#!/usr/bin/env python3
"""Run JavaScript inside the running Cinnamon shell (org.Cinnamon.Eval).

Usage: tools/ceval.py 'global.get_window_actors().length'
       tools/ceval.py < script.js
"""
import sys

from gi.repository import Gio, GLib

code = sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read()
bus = Gio.bus_get_sync(Gio.BusType.SESSION)
ok, result = bus.call_sync(
    "org.Cinnamon", "/org/Cinnamon", "org.Cinnamon", "Eval",
    GLib.Variant("(s)", (code,)), GLib.VariantType("(bs)"),
    Gio.DBusCallFlags.NONE, 5000, None).unpack()
print(result if ok else f"ERROR: {result}")
sys.exit(0 if ok else 1)
