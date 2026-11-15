#!/usr/bin/env python3
"""Make Flatpak apps follow NalaMint (no root needed).

  tools/flatpak.py apply     theme access + per-app libadwaita colors
  tools/flatpak.py revert    undo both

- GTK3 apps (Lutris, GIMP…) already get the theme *name* from the settings
  portal; a user-level override gives them read-only access to ~/.themes and
  ~/.local/share/icons so they can load it.
- libadwaita apps use the runtime's own libadwaita, which ignores themes. Each
  one gets build/flatpak/gtk-4.0/gtk.css as user CSS in its own config dir
  (~/.var/app/<id>/config/gtk-4.0/), so host apps are not affected.
Anything that was there before is backed up to build/flatpak-backup/.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOME = Path.home()
SRC_CSS = ROOT / "build/flatpak/gtk-4.0"
BACKUP = ROOT / "build/flatpak-backup"
STATE = BACKUP / "state.json"
OVERRIDE = HOME / ".local/share/flatpak/overrides/global"
MARK = "/* NalaMint for Flatpak libadwaita apps"
FILESYSTEMS = ["~/.themes:ro", "xdg-data/icons:ro"]


def apps():
    out = subprocess.run(["flatpak", "list", "--app", "--columns=application,runtime"],
                         capture_output=True, text=True).stdout
    return [line.split("\t") for line in out.splitlines() if "\t" in line]


def state():
    return json.loads(STATE.read_text()) if STATE.exists() else {"apps": {}, "had_override": None}


def apply():
    if not shutil.which("flatpak"):
        return print("flatpak not installed; nothing to do")
    if not (SRC_CSS / "gtk.css").exists():
        sys.exit("run ./build.py first")
    BACKUP.mkdir(parents=True, exist_ok=True)
    st = state()

    if st["had_override"] is None:
        st["had_override"] = OVERRIDE.exists()
        if OVERRIDE.exists():
            shutil.copy(OVERRIDE, BACKUP / "global-override")
    subprocess.run(["flatpak", "override", "--user"] + [f"--filesystem={f}" for f in FILESYSTEMS],
                   check=True)

    themed = []
    for app_id, runtime in apps():
        if not runtime.startswith("org.gnome.Platform"):   # only GNOME runtimes ship libadwaita
            continue
        dest = HOME / ".var/app" / app_id / "config/gtk-4.0"
        css = dest / "gtk.css"
        if app_id not in st["apps"]:
            had = css.exists() and not css.read_text().startswith(MARK)
            if had:
                shutil.copy(css, BACKUP / f"{app_id}.css")
            st["apps"][app_id] = {"had_css": had}
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy(SRC_CSS / "gtk.css", css)
        shutil.rmtree(dest / "assets", ignore_errors=True)
        shutil.copytree(SRC_CSS / "assets", dest / "assets")
        themed.append(app_id)
    STATE.write_text(json.dumps(st, indent=2))
    print("Flatpak: theme folders shared read-only; libadwaita colors for " + (", ".join(themed) or "no apps"))


def revert():
    if not STATE.exists():
        return print("Flatpak: nothing to revert")
    st = state()
    for app_id, info in st["apps"].items():
        dest = HOME / ".var/app" / app_id / "config/gtk-4.0"
        if info.get("had_css") and (BACKUP / f"{app_id}.css").exists():
            shutil.copy(BACKUP / f"{app_id}.css", dest / "gtk.css")
        elif (dest / "gtk.css").exists():
            (dest / "gtk.css").unlink()
        shutil.rmtree(dest / "assets", ignore_errors=True)
        if dest.exists() and not any(dest.iterdir()):
            dest.rmdir()
    if st["had_override"] and (BACKUP / "global-override").exists():
        shutil.copy(BACKUP / "global-override", OVERRIDE)
    elif OVERRIDE.exists():
        OVERRIDE.unlink()
    shutil.rmtree(BACKUP, ignore_errors=True)
    print("Flatpak settings reverted")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("apply", "revert"):
        sys.exit(__doc__)
    apply() if sys.argv[1] == "apply" else revert()
