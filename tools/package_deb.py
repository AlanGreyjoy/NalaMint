#!/usr/bin/env python3
"""Build a .deb with everything NalaMint installs system-wide.

Usage: tools/package_deb.py [--version 1.0.0] [--maintainer "Name <email>"]

Runs ./build.py, then packages into build/deb/nalamint_<version>_all.deb:
  /usr/share/themes/NalaMint{,-Dark}         GTK3/GTK4/libadwaita + Cinnamon theme
  /usr/share/icons/NalaMint                  icon theme (inherits Mint-L)
  /usr/share/backgrounds/nalamint/           wallpapers, listed in Backgrounds
  /usr/share/cinnamon/applets/<uuid>/        Launchpad, logo menu, app name
  /usr/share/cinnamon/extensions/<uuid>/     rounded corners, menu-bar blur
  /usr/bin/nalamint-layout                   tools/layout.py (dock / restore)
Nothing is installed here; install the result with `sudo apt install ./<deb>`.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
DEFAULT_MAINTAINER = "NalaMint <4026982+AlanGreyjoy@users.noreply.github.com>"

ap = argparse.ArgumentParser()
ap.add_argument("--version", default="1.0.0")
ap.add_argument("--maintainer", default=DEFAULT_MAINTAINER)
a = ap.parse_args()

subprocess.run([sys.executable, str(ROOT / "build.py")], check=True, stdout=subprocess.DEVNULL)

stage = BUILD / "deb" / f"nalamint_{a.version}_all"
shutil.rmtree(stage, ignore_errors=True)
usr = stage / "usr/share"


def copy(src, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dest, symlinks=True)
    else:
        shutil.copy(src, dest)


for theme in ("NalaMint", "NalaMint-Dark"):
    copy(BUILD / theme, usr / "themes" / theme)
copy(BUILD / "icons/NalaMint", usr / "icons/NalaMint")
for kind, folder in (("applet", "applets"), ("extension", "extensions")):
    for spice in sorted((ROOT / "src" / kind).iterdir()):
        copy(spice, usr / "cinnamon" / folder / spice.name)

walls = sorted((BUILD / "wallpapers").glob("*.jpg"))
for w in walls:
    copy(w, usr / "backgrounds/nalamint" / w.name)
entries = "".join(f"""    <wallpaper deleted="false">
        <name>NalaMint {w.stem.split('-')[-1].title()}</name>
        <filename>/usr/share/backgrounds/nalamint/{w.name}</filename>
        <options>zoom</options>
        <shade_type>solid</shade_type>
        <pcolor>#000000</pcolor>
        <scolor>#000000</scolor>
        <artist>NalaMint</artist>
    </wallpaper>
""" for w in walls)
xml = usr / "cinnamon-background-properties/nalamint.xml"
xml.parent.mkdir(parents=True, exist_ok=True)
xml.write_text('<?xml version="1.0"?>\n<!DOCTYPE wallpapers SYSTEM "cinnamon-wp-list.dtd">\n'
               f"<wallpapers>\n{entries}</wallpapers>\n")

copy(ROOT / "tools/layout.py", stage / "usr/bin/nalamint-layout")

doc = usr / "doc/nalamint"
doc.mkdir(parents=True, exist_ok=True)
(doc / "copyright").write_text(f"""Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: NalaMint
Source: https://github.com/AlanGreyjoy/NalaMint

Files: *
Copyright: NalaMint contributors
License: GPL-3.0-or-later
 Themes, icons (generated with the Codex CLI; prompts in the source tree),
 wallpapers, applets, extensions and tools. On Debian systems the full text
 is in /usr/share/common-licenses/GPL-3.

Files: usr/share/themes/*/libadwaita-1.5/base.css
Copyright: The GNOME Project
License: LGPL-2.1-or-later
 Extracted from the system's libadwaita at build time, with NalaMint rules
 appended. On Debian systems the full text is in
 /usr/share/common-licenses/LGPL-2.1.
""")

# Permissions: dpkg keeps them as they are in the tree
for path in stage.rglob("*"):
    if path.is_symlink():
        continue
    path.chmod(0o755 if path.is_dir() else 0o644)
(stage / "usr/bin/nalamint-layout").chmod(0o755)

size_kb = sum(p.stat().st_size for p in stage.rglob("*") if p.is_file() and not p.is_symlink()) // 1024
control = stage / "DEBIAN/control"
control.parent.mkdir(parents=True)
control.parent.chmod(0o755)
control.write_text(f"""Package: nalamint
Version: {a.version}
Architecture: all
Maintainer: {a.maintainer}
Installed-Size: {size_kb}
Depends: cinnamon (>= 6.0), python3
Recommends: fonts-inter
Suggests: qt5ct
Section: x11
Priority: optional
Homepage: https://github.com/AlanGreyjoy/NalaMint
Description: macOS-inspired theme for Linux Mint Cinnamon
 Light and dark GTK3, GTK4/libadwaita and Cinnamon desktop themes with
 traffic-light window buttons, a transparent blurred menu bar and a dock,
 an icon theme and wallpapers, plus Cinnamon add-ons: rounded window
 corners, menu-bar blur, Launchpad (full-screen app grid with folders),
 a logo menu and the focused app's name in the menu bar.
 .
 Pick the themes in System Settings > Themes; run nalamint-layout dock for
 the menu bar + dock layout (nalamint-layout restore puts yours back).
""")
control.chmod(0o644)

out = stage.parent / f"nalamint_{a.version}_all.deb"
subprocess.run(["dpkg-deb", "--root-owner-group", "-Zxz", "--build", str(stage), str(out)],
               check=True, stdout=subprocess.DEVNULL)
print(f"{out.relative_to(ROOT)}  ({out.stat().st_size // 1024} KiB, {size_kb} KiB installed)")
