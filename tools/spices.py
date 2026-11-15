#!/usr/bin/env python3
"""Lay out NalaMint as Cinnamon Spices, ready for pull requests.

Usage: tools/spices.py [--author GITHUB_USER]

Runs ./build.py, then writes build/spices/{themes,applets,extensions}/<UUID>/
in the layout the linuxmint/cinnamon-spices-* repositories expect:
  <UUID>/info.json, screenshot.png, README.md, files/<UUID>/...
Each folder is copied as-is into a fork of the matching repository. Check
them with that repository's ./validate-spice <UUID>.

Themes carry the GTK3, GTK4/libadwaita and Cinnamon parts. Icons and
wallpapers are not allowed in theme spices; they ship in the .deb only.
"""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
SPICES = ROOT / "src/spices"
OUT = BUILD / "spices"
URL = "https://github.com/AlanGreyjoy/NalaMint"
LICENSE = "GPL-3.0"

THEMES = {
    "NalaMint": dict(
        name="NalaMint",
        description="A light macOS-inspired theme: traffic-light window buttons, rounded "
                    "windows, a transparent menu bar and a floating dock. GTK3, GTK4/libadwaita "
                    "and Cinnamon.",
        icon="theme-light.png", screenshot="theme-light.png"),
    "NalaMint-Dark": dict(
        name="NalaMint Dark",
        description="A dark macOS-inspired theme: traffic-light window buttons, rounded "
                    "windows, a transparent menu bar and a floating dock. GTK3, GTK4/libadwaita "
                    "and Cinnamon.",
        icon="theme-dark.png", screenshot="theme-dark.png"),
}

XLETS = {
    "nalamint-launchpad@nalamint": dict(
        kind="applet", icon=ROOT / "src/icons/apps/launchpad.png", screenshot="launchpad.png",
        readme="""# NalaMint Launchpad

A full-screen grid of your apps over the blurred wallpaper, like Launchpad on
a Mac. Put it in a panel (the NalaMint layout makes it the first dock icon);
Super opens it too.

- Type to search (word starts: `ter` finds Terminal); Enter opens the first result.
- Arrow keys, Page Up/Down, the scroll wheel or the dots change page.
- Drag icons to rearrange them; rest one on another icon's center to make a
  folder. Click a folder's name to rename it; drag an icon out of the folder
  to take it out.
- Escape clears the search, then closes. Super or a click on empty space closes.

The first time, apps are sorted A-Z, with Administration and Preferences apps
in a *Utilities* folder and games in *Games*. Right-click the applet for
*Reset Launchpad Layout*.

Settings: icon, shortcut (Super by default), blur strength, and whether
System Settings pages appear in the grid (search finds them either way).

If you keep the Mint menu too, give one of the two a different shortcut:
both use Super by default.
"""),
    "nalamint-system@nalamint": dict(
        kind="applet", icon=SPICES / "icons/logo-menu.png", screenshot="logo-menu.png",
        readme="""# NalaMint System Menu

The logo menu at the left of the menu bar, like the one on a Mac:

- About This Computer (System Information)
- System Settings, Software Manager
- Force Quit (System Monitor's process list)
- Sleep, Restart, Shut Down
- Lock Screen, Log Out

Restart, Shut Down and Log Out ask for confirmation first. The icon can be
changed in the applet's settings.
"""),
    "nalamint-appname@nalamint": dict(
        kind="applet", icon=SPICES / "icons/app-name.png", screenshot="app-name.png",
        readme="""# NalaMint App Name

The focused app's name in bold in the menu bar, like on a Mac. Click it for
Show All Windows, Hide and Quit; with no app focused it offers Show Desktop.
"""),
    "nalamint-corners@nalamint": dict(
        kind="extension", icon=SPICES / "icons/rounded-corners.png", screenshot="theme-dark.png",
        readme="""# NalaMint Rounded Corners

Rounds all four corners of every window, including apps that draw their own
title bars (Electron, Chromium) and windows with Muffin frames, whose bottom
corners are otherwise square. The cut corners are filled with the window's
shadow, so the shadow stays continuous.

Maximized, tiled and fullscreen windows stay square. Settings: corner radius
and the shadow strength used for focused and unfocused windows.
"""),
    "nalamint-menubar@nalamint": dict(
        kind="extension", icon=SPICES / "icons/menubar-blur.png", screenshot="menubar.png",
        readme="""# NalaMint Menu Bar

For themes with transparent panels:

- draws a blurred copy of the wallpaper behind each panel, like the macOS
  menu bar;
- adds the `nalamint-on-light` style class to panels over a bright wallpaper,
  so a theme can switch to dark text there (the NalaMint themes do);
- for a bottom panel used as a dock, draws the rounded dock bar behind it
  (`.nalamint-dock-plate` in the theme).

Settings: blur on/off, blur radius, adaptive text and the brightness at which
a wallpaper counts as bright.
"""),
}

THEME_README = """# {name}

{description}

Part of NalaMint, written from scratch for Linux Mint Cinnamon (not a fork of
another theme). Original artwork only.

- **Applications (GTK3 and GTK4/libadwaita)**: rounded controls, accent-blue
  selections, traffic-light window buttons (close, minimize, maximize), and
  window frames drawn by Muffin from the same theme.
- **Desktop (Cinnamon)**: a transparent menu bar, menus and calendar with
  rounded corners, notifications, OSDs, Alt-Tab, and a floating dock when a
  panel sits at the bottom.

Pick it in System Settings > Themes for both *Applications* and *Desktop*.
For the Mac button order, set the title bar buttons to the left in
System Settings > Windows. The *Inter* font (package `fonts-inter`) matches it.

Pairs with these spices: NalaMint Launchpad, NalaMint System Menu and
NalaMint App Name (applets), NalaMint Rounded Corners and NalaMint Menu Bar
(extensions).

libadwaita-1.5/base.css is libadwaita's own stylesheet (LGPL-2.1-or-later)
with NalaMint rules appended; everything else is GPL-3.0.
"""


def write_json(path, data):
    path.write_text(json.dumps(data, indent=4) + "\n")


def save_png(src, dest, size=None):
    im = Image.open(src)
    if size:
        im = im.convert("RGBA").resize((size, size), Image.LANCZOS)
    im.save(dest, optimize=True)


def check(kind, root):
    """The checks of the repositories' validate-spice scripts, so a PR
    passes their CI. Returns a list of problems."""
    uuid, problems = root.name, []
    need = lambda p: problems.append(f"missing {p}") if not (root / p).exists() else None
    files = root / "files"
    if not files.is_dir() or [p.name for p in files.iterdir()] != [uuid]:
        problems.append("files/ must hold exactly the <uuid> folder")
    need("info.json")
    need("screenshot.png")
    info = json.loads((root / "info.json").read_text())
    if any(c.isspace() for c in info.get("author", " ")):
        problems.append("info.json author missing or has whitespace")
    if kind == "themes":
        need(f"files/{uuid}/cinnamon/cinnamon.css")
        for field in ("description", "name"):
            if field not in info:
                problems.append(f"info.json lacks {field}")
        if (root / "metadata.json").exists():
            problems.append("metadata.json not allowed at the top")
        return problems
    main_js = "applet.js" if kind == "applets" else "extension.js"
    for p in (f"files/{uuid}/metadata.json", f"files/{uuid}/icon.png", f"files/{uuid}/{main_js}"):
        need(p)
    if (root / "icon.png").exists():
        problems.append("icon.png not allowed at the top")
    meta = json.loads((files / uuid / "metadata.json").read_text())
    for field in ("uuid", "name", "description"):
        if field not in meta:
            problems.append(f"metadata.json lacks {field}")
    for field in ("icon", "dangerous", "last-edited"):
        if field in meta:
            problems.append(f"metadata.json must not have {field}")
    if meta.get("uuid") != uuid:
        problems.append("metadata.json uuid differs from the folder name")
    for field, value in meta.items():
        if not str(value).isascii():
            problems.append(f"metadata.json {field} has non-ASCII characters")
    w, h = Image.open(files / uuid / "icon.png").size
    if w != h:
        problems.append("icon.png must be square")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--author", default="AlanGreyjoy", help="GitHub username of the spices' author")
    a = ap.parse_args()

    subprocess.run([sys.executable, str(ROOT / "build.py")], check=True, stdout=subprocess.DEVNULL)
    shutil.rmtree(OUT, ignore_errors=True)

    for uuid, t in THEMES.items():
        root = OUT / "themes" / uuid
        files = root / "files" / uuid
        shutil.copytree(BUILD / uuid, files)
        shutil.copy(ROOT / "LICENSE", files / "LICENSE")
        write_json(root / "info.json", {"author": a.author, "name": t["name"],
                                         "description": t["description"], "license": LICENSE, "url": URL})
        save_png(SPICES / "screenshots" / t["screenshot"], root / "screenshot.png")
        save_png(SPICES / "icons" / t["icon"], root / "icon.png", 128)
        (root / "README.md").write_text(THEME_README.format(**t))

    for uuid, x in XLETS.items():
        root = OUT / (x["kind"] + "s") / uuid
        files = root / "files" / uuid
        shutil.copytree(ROOT / "src" / x["kind"] / uuid, files)
        save_png(x["icon"], files / "icon.png", 128)
        write_json(root / "info.json", {"author": a.author, "license": LICENSE})
        save_png(SPICES / "screenshots" / x["screenshot"], root / "screenshot.png")
        (root / "README.md").write_text(x["readme"])

    failed = False
    for kind in ("themes", "applets", "extensions"):
        for spice in sorted((OUT / kind).iterdir()):
            problems = check(kind, spice)
            failed |= bool(problems)
            print(f"{spice.relative_to(ROOT)}: " + ("; ".join(problems) if problems else "ok"))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
