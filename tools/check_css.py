#!/usr/bin/env python3
"""Load built stylesheets through GTK's own parser and report errors.

Usage: tools/check_css.py [--gtk4] [file.css ...]
  default: build/*/gtk-3.0/gtk*.css with GTK 3
  --gtk4:  build/*/gtk-4.0/gtk*.css and libadwaita base.css (with its colors) with GTK 4
"""
import sys
import tempfile
from pathlib import Path

import gi
GTK4 = "--gtk4" in sys.argv
try:
    gi.require_version("Gtk", "4.0" if GTK4 else "3.0")
except ValueError:
    sys.exit("GTK 4 Python bindings missing: sudo apt install gir1.2-gtk-4.0")
from gi.repository import Gtk  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
args = [a for a in sys.argv[1:] if a != "--gtk4"]
if GTK4 and not args:
    # Themes only: build/flatpak/ targets the Flatpak runtime's newer GTK (@media)
    args = sorted(str(p) for p in ROOT.glob("build/NalaMint*/gtk-4.0/gtk*.css"))
    for adw in sorted(ROOT.glob("build/*/libadwaita-*")):   # colors + base, as libadwaita loads them
        tmp = Path(tempfile.mkdtemp()) / "adw-combined.css"
        tmp.write_text((adw / "defaults-dark.css").read_text() + (adw / "base.css").read_text())
        args.append(str(tmp))
files = args or sorted(str(p) for p in ROOT.glob("build/*/gtk-3.0/gtk*.css"))
errors = 0
for path in files:
    provider = Gtk.CssProvider()
    lines = Path(path).read_text().splitlines()

    def on_error(_provider, section, error, path=path):
        global errors
        errors += 1
        line = (section.get_start_line() if hasattr(section, "get_start_line")   # GTK 3
                else section.get_start_location().lines)                          # GTK 4
        src = lines[line].strip() if line < len(lines) else ""
        print(f"{path}:{line + 1}: {error.message}\n    {src}")

    provider.connect("parsing-error", on_error)
    try:
        provider.load_from_path(path)
    except Exception:
        pass  # errors already reported by the signal
print(f"{len(files)} files, {errors} errors")
sys.exit(1 if errors else 0)
