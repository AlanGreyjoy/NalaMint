#!/usr/bin/env python3
"""Live edit mode: watch src/, rebuild on save, reload the running desktop.

Usage: tools/dev.py [dark|light]      Ctrl+C to stop (the theme stays applied;
                                      tools/revert.sh puts your old one back)

What reloads, and how:
  src/gtk-3.0/**,
  src/libadwaita/**  GTK3/GTK4/libadwaita apps + Muffin window frames. GTK only re-reads a theme
                     when the theme *name* changes, so the build is installed
                     under two names (<theme> and <theme>-dev) and each reload
                     switches between them.
  src/cinnamon/**    Desktop (panel, menus, OSDs) via org.Cinnamon.ReloadTheme.
  src/extension/X/** Extension X via org.Cinnamon.ReloadXlet.
  src/applet/X/**    Applet X via org.Cinnamon.ReloadXlet.
  src/icons/**       Icon theme (switches between NalaMint and NalaMint-dev).
  src/palette.toml   GTK, desktop and Qt colors.
"""
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from gi.repository import Gio, GLib

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
THEMES = Path.home() / ".themes"
EXTENSIONS = Path.home() / ".local/share/cinnamon/extensions"
APPLETS = Path.home() / ".local/share/cinnamon/applets"
ICONS = Path.home() / ".local/share/icons"
ICON_SLOTS = ("NalaMint", "NalaMint-dev")
XSESSION_LOG = Path.home() / ".xsession-errors"

variant = sys.argv[1] if len(sys.argv) > 1 else "dark"
if variant not in ("dark", "light"):
    sys.exit(__doc__)
THEME = "NalaMint-Dark" if variant == "dark" else "NalaMint"
SLOTS = (THEME, f"{THEME}-dev")

RED, GREEN, DIM, RESET = "\033[31m", "\033[32m", "\033[2m", "\033[0m"


def log(msg, color=""):
    print(f"{DIM}{datetime.now():%H:%M:%S}{RESET} {color}{msg}{RESET}", flush=True)


def gsettings(*args):
    return subprocess.run(["gsettings", *args], capture_output=True, text=True).stdout.strip()


def cinnamon_call(method, args=None, sig=None):
    bus = Gio.bus_get_sync(Gio.BusType.SESSION)
    params = GLib.Variant(sig, args) if sig else None
    bus.call_sync("org.Cinnamon", "/org/Cinnamon", "org.Cinnamon", method, params,
                  None, Gio.DBusCallFlags.NONE, 5000, None)


def log_size():
    return XSESSION_LOG.stat().st_size if XSESSION_LOG.exists() else 0


def new_log_lines(since, needle):
    if not XSESSION_LOG.exists():
        return []
    with XSESSION_LOG.open("rb") as f:
        f.seek(since)
        text = f.read().decode(errors="replace")
    return [line for line in text.splitlines() if needle(line)]


def snapshot():
    return {p: p.stat().st_mtime for p in SRC.rglob("*") if p.is_file()}


def build():
    r = subprocess.run([sys.executable, str(ROOT / "build.py")], capture_output=True, text=True)
    if r.returncode != 0:
        log("build failed:\n" + (r.stderr or r.stdout).strip(), RED)
        return False
    return True


def install_theme():
    for slot in SLOTS:
        dest = THEMES / slot
        shutil.rmtree(dest, ignore_errors=True)
        shutil.copytree(ROOT / "build" / THEME, dest)


def reload_gtk():
    css = ROOT / "build" / THEME / "gtk-3.0" / "gtk.css"
    r = subprocess.run([sys.executable, str(ROOT / "tools/check_css.py"), str(css)],
                       capture_output=True, text=True)
    errors = [l for l in r.stdout.splitlines() if l.startswith(str(ROOT))]
    current = gsettings("get", "org.cinnamon.desktop.interface", "gtk-theme").strip("'")
    target = SLOTS[1] if current == SLOTS[0] else SLOTS[0]
    gsettings("set", "org.cinnamon.desktop.interface", "gtk-theme", target)
    if errors:
        log(f"gtk      reloaded with {len(errors)} CSS error(s):", RED)
        for e in errors[:8]:
            print("         " + e.replace(str(ROOT) + "/", ""))
    else:
        log("gtk      reloaded (apps + window frames)", GREEN)


def reload_icons():
    for slot in ICON_SLOTS:
        dest = ICONS / slot
        shutil.rmtree(dest, ignore_errors=True)
        shutil.copytree(ROOT / "build" / "icons" / "NalaMint", dest)
        idx = dest / "index.theme"
        idx.write_text(idx.read_text().replace("Name=NalaMint", f"Name={slot}", 1))
        subprocess.run(["gtk-update-icon-cache", "-q", "-f", "-t", str(dest)])
    current = gsettings("get", "org.cinnamon.desktop.interface", "icon-theme").strip("'")
    target = ICON_SLOTS[1] if current == ICON_SLOTS[0] else ICON_SLOTS[0]
    gsettings("set", "org.cinnamon.desktop.interface", "icon-theme", target)
    log("icons    reloaded", GREEN)


def reload_shell():
    mark = log_size()
    cinnamon_call("ReloadTheme")
    time.sleep(0.6)
    bad = new_log_lines(mark, lambda l: "problem parsing the theme" in l)
    if bad:
        log("desktop  CSS failed to parse — Cinnamon fell back to its default theme", RED)
    else:
        log("desktop  reloaded (panel, menus, OSDs)", GREEN)


def reload_extension(uuid, kind="extension"):
    src = SRC / kind / uuid
    dest = (EXTENSIONS if kind == "extension" else APPLETS) / uuid
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(src, dest)
    mark = log_size()
    cinnamon_call("ReloadXlet", (uuid, kind.upper()), "(ss)")
    time.sleep(0.8)
    bad = new_log_lines(mark, lambda l: uuid in l and ("rror" in l or "Could not" in l))
    if bad:
        log(f"{uuid} failed to load:", RED)
        for line in bad[:6]:
            print("         " + line.strip())
    else:
        log(f"{kind} {uuid} reloaded", GREEN)


def classify(paths):
    parts = set()
    for p in paths:
        rel = p.relative_to(SRC).parts
        if rel[0] == "palette.toml":
            parts |= {"gtk", "shell", "qt"}
        elif rel[0] in ("gtk-3.0", "libadwaita"):
            parts.add("gtk")
        elif rel[0] == "cinnamon":
            parts.add("shell")
        elif rel[0] == "icons":
            parts.add("icons")
        elif rel[0] in ("extension", "applet") and len(rel) > 1:
            parts.add(rel[0] + ":" + rel[1])
    return parts


def cleanup():
    if gsettings("get", "org.cinnamon.desktop.interface", "gtk-theme").strip("'") == SLOTS[1]:
        gsettings("set", "org.cinnamon.desktop.interface", "gtk-theme", THEME)
    shutil.rmtree(THEMES / SLOTS[1], ignore_errors=True)
    if gsettings("get", "org.cinnamon.desktop.interface", "icon-theme").strip("'") == ICON_SLOTS[1]:
        gsettings("set", "org.cinnamon.desktop.interface", "icon-theme", ICON_SLOTS[0])
    shutil.rmtree(ICONS / ICON_SLOTS[1], ignore_errors=True)
    log(f"stopped; {THEME} stays applied (tools/revert.sh to undo)")


def main():
    subprocess.run([str(ROOT / "tools/apply.sh"), variant], check=True,
                   stdout=subprocess.DEVNULL)
    install_theme()
    log(f"watching src/ — {THEME} applied. Save a file to reload. Ctrl+C to stop.")
    seen = snapshot()
    try:
        while True:
            time.sleep(0.4)
            now = snapshot()
            changed = [p for p in now if seen.get(p) != now[p]]
            changed += [p for p in seen if p not in now]
            if not changed:
                continue
            time.sleep(0.25)  # let editors finish writing
            now = snapshot()
            seen = now
            parts = classify(changed)
            names = ", ".join(sorted(str(p.relative_to(SRC)) for p in changed)[:4])
            log(f"changed  {names}")
            if not build():
                continue
            install_theme()
            if "gtk" in parts:
                reload_gtk()
                subprocess.run([sys.executable, str(ROOT / "tools/flatpak.py"), "apply"],
                               stdout=subprocess.DEVNULL)   # Flatpak apps pick it up on restart
            if "shell" in parts:
                reload_shell()
            if "icons" in parts:
                reload_icons()
            if "qt" in parts:
                subprocess.run([sys.executable, str(ROOT / "tools/qt.py"), "apply", variant],
                               stdout=subprocess.DEVNULL)
                log("qt       colors updated (restart Qt apps to see them)", GREEN)
            for part in sorted(parts):
                kind, _, uuid = part.partition(":")
                if kind in ("extension", "applet"):
                    reload_extension(uuid, kind)
    except KeyboardInterrupt:
        print()
    finally:
        cleanup()


if __name__ == "__main__":
    import signal
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt))
    main()
