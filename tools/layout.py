#!/usr/bin/env python3
"""Switch the Cinnamon panel layout to a macOS-style menu bar + dock, or back.

  tools/layout.py dock [--height 64] [--icons 40]
      Adds a bottom panel on the same monitor as the top panel and moves the
      grouped window list (with its pinned apps) into its center. The NalaMint
      desktop theme draws that center zone as a floating dock. In the top bar,
      the focused app's name (nalamint-appname applet) replaces the separator
      next to the menu. The Mint menu becomes a Mac-style logo menu
      (nalamint-system: settings, sleep, restart, shut down, lock, log out)
      and the dock starts with Launchpad (nalamint-launchpad: full-screen app
      grid, also on Super). --keep-menu keeps the Mint menu and no Launchpad.
  tools/layout.py restore
      Puts back the layout saved the first time `dock` ran.

The first `dock` run saves the current layout to build/original-layout.json
(in a source checkout) or ~/.local/share/nalamint/original-layout.json (when
installed from the .deb as `nalamint-layout`). `dock` also turns on the
rounded-corners and menu-bar extensions if they are installed.
"""
import argparse
import ast
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAVED = (ROOT / "build" / "original-layout.json" if (ROOT / "build.py").exists()
         else Path.home() / ".local/share/nalamint/original-layout.json")
# Cinnamon deletes an applet instance's settings file when the applet leaves
# the panel, so the ones dock replaces are copied here and put back on restore
SPICES = Path.home() / ".config/cinnamon/spices"
SETTINGS_BACKUP = SAVED.parent / "applet-settings"
EXTENSIONS = ["nalamint-corners@nalamint", "nalamint-menubar@nalamint"]
EXTENSION_DIRS = [Path.home() / ".local/share/cinnamon/extensions", Path("/usr/share/cinnamon/extensions")]
SCHEMA = "org.cinnamon"
LIST_KEYS = ["panels-enabled", "panels-height", "panels-autohide", "panels-hide-delay",
             "panels-show-delay", "enabled-applets", "enabled-extensions"]
JSON_KEYS = ["panel-zone-icon-sizes", "panel-zone-symbolic-icon-sizes", "panel-zone-text-sizes"]
WINDOW_LIST = "grouped-window-list@cinnamon.org"
APP_NAME = "nalamint-appname@nalamint"           # bold focused-app name, src/applet/
LAUNCHPAD = "nalamint-launchpad@nalamint"        # full-screen app grid, src/applet/
SYSTEM = "nalamint-system@nalamint"              # logo menu: settings, sleep, shut down…
MENU = "menu@cinnamon.org"


def get(key):
    raw = subprocess.run(["gsettings", "get", SCHEMA, key], capture_output=True,
                         text=True, check=True).stdout.strip()
    return ast.literal_eval(raw.removeprefix("@as ").strip())


def put(key, value):
    if isinstance(value, list):
        value = "[" + ", ".join("'" + v + "'" for v in value) + "]"
    else:
        value = "'" + value + "'"
    subprocess.run(["gsettings", "set", SCHEMA, key, value], check=True)


def backup_settings(uuid, instance):
    src = SPICES / uuid / f"{instance}.json"
    dest = SETTINGS_BACKUP / uuid / f"{instance}.json"
    if src.exists() and not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dest)


def save_once():
    if SAVED.exists():
        return
    SAVED.parent.mkdir(parents=True, exist_ok=True)
    SAVED.write_text(json.dumps({k: get(k) for k in LIST_KEYS + JSON_KEYS}, indent=2))
    print(f"saved current layout to {SAVED}")


def dock(height, icons, keep_menu=False):
    save_once()
    panels = get("panels-enabled")                     # "id:monitor:position"
    parsed = [p.split(":") for p in panels]
    top = next((p for p in parsed if p[2] == "top"), parsed[0])
    monitor = top[1]
    existing = next((p for p in parsed if p[2] == "bottom" and p[1] == monitor), None)
    dock_id = existing[0] if existing else str(max(int(p[0]) for p in parsed) + 1)

    def upsert(key, value):
        items = [i for i in get(key) if not i.startswith(dock_id + ":")]
        put(key, items + [f"{dock_id}:{value}"])

    # Sizes first, so the panel is created with them
    upsert("panels-height", str(height))
    upsert("panels-autohide", "false")
    upsert("panels-hide-delay", "0")
    upsert("panels-show-delay", "0")
    for key, center in (("panel-zone-icon-sizes", icons), ("panel-zone-symbolic-icon-sizes", 28),
                        ("panel-zone-text-sizes", 0.0)):
        zones = [z for z in json.loads(get(key)) if str(z.get("panelId")) != dock_id]
        zones.append({"panelId": int(dock_id), "left": 0, "center": center, "right": 0})
        put(key, json.dumps(zones))
    if not existing:
        put("panels-enabled", panels + [f"{dock_id}:{monitor}:bottom"])

    applets = get("enabled-applets")                   # "panelN:zone:order:uuid:instance"
    top_panel = f"panel{top[0]}"
    next_id = max(int(a.split(":")[4]) for a in applets) + 1
    dock_panel = f"panel{dock_id}"
    moved = []
    for a in applets:
        f = a.split(":")
        if f[0] == top_panel and f[1] == "left" and f[3] in (MENU, LAUNCHPAD, SYSTEM):
            want = MENU if keep_menu else SYSTEM       # the logo menu, top left
            if f[3] != want:
                backup_settings(f[3], f[4])
                f[3], f[4] = want, str(next_id)
                next_id += 1
        elif f[3] == LAUNCHPAD:
            if keep_menu or f[0] != dock_panel:
                continue                               # re-added as the dock's first item
            f[1], f[2] = "center", "0"
        elif f[3] == WINDOW_LIST:
            f[0], f[1], f[2] = dock_panel, "center", "1"
        elif f[3] == "separator@cinnamon.org" and f[0] == top_panel and f[1] == "left":
            backup_settings(f[3], f[4])
            continue                                   # the app name takes its place
        moved.append(":".join(f))
    if not keep_menu and not any(a.split(":")[3] == LAUNCHPAD for a in moved):
        moved.append(f"{dock_panel}:center:0:{LAUNCHPAD}:{next_id}")
        next_id += 1
    if not any(a.split(":")[3] == APP_NAME for a in moved):
        moved.append(f"{top_panel}:left:1:{APP_NAME}:{next_id}")
    put("enabled-applets", moved)
    extensions = get("enabled-extensions")
    for uuid in EXTENSIONS:
        if uuid not in extensions and any((d / uuid).is_dir() for d in EXTENSION_DIRS):
            extensions.append(uuid)
    put("enabled-extensions", extensions)
    print(f"dock: panel {dock_id} at the bottom of monitor {monitor}, {height}px, {icons}px icons")


def restore():
    if not SAVED.exists():
        sys.exit(f"nothing to restore: {SAVED} not found")
    saved = json.loads(SAVED.read_text())
    # Settings files first, so the returning applets load them instead of defaults
    for backup in SETTINGS_BACKUP.glob("*/*.json"):
        dest = SPICES / backup.parent.name / backup.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(backup, dest)
    # Move applets back before the dock panel disappears
    put("enabled-applets", saved["enabled-applets"])
    put("panels-enabled", saved["panels-enabled"])
    for key in LIST_KEYS + JSON_KEYS:
        if key not in ("enabled-applets", "panels-enabled") and key in saved:
            put(key, saved[key])   # layouts saved before a key was added lack it
    print("layout restored")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["dock", "restore"])
    ap.add_argument("--height", type=int, default=64)
    ap.add_argument("--icons", type=int, default=40)
    ap.add_argument("--keep-menu", action="store_true", help="keep the Mint menu; no logo menu or Launchpad")
    a = ap.parse_args()
    dock(a.height, a.icons, a.keep_menu) if a.action == "dock" else restore()
