#!/usr/bin/env python3
"""NalaMint wallpapers in System Settings → Backgrounds.

  tools/wallpaper.py register     list ~/.local/share/backgrounds/nalamint in Backgrounds
  tools/wallpaper.py unregister   remove it from that list (files stay)
  tools/wallpaper.py set dark|light   make one the desktop background

Cinnamon reads user wallpaper folders from ~/.config/cinnamon/backgrounds/user-folders.lst.
"""
import subprocess
import sys
from pathlib import Path

FOLDER = Path.home() / ".local/share/backgrounds/nalamint"
LIST = Path.home() / ".config/cinnamon/backgrounds/user-folders.lst"


def lines():
    return LIST.read_text().splitlines() if LIST.exists() else []


def register():
    current = lines()
    if not LIST.exists():                       # Cinnamon's default is the Pictures folder
        current = [str(Path.home() / "Pictures")]
    if str(FOLDER) not in current:
        LIST.parent.mkdir(parents=True, exist_ok=True)
        LIST.write_text("\n".join(current + [str(FOLDER)]) + "\n")
    print(f"Backgrounds lists {FOLDER}")


def unregister():
    if LIST.exists():
        kept = [l for l in lines() if l != str(FOLDER)]
        LIST.write_text("\n".join(kept) + ("\n" if kept else ""))
    print("NalaMint wallpapers removed from Backgrounds (files kept)")


def set_wallpaper(variant):
    f = FOLDER / f"nalamint-{variant}.jpg"
    if not f.exists():
        sys.exit(f"{f} missing; run ./build.py --install")
    for key, value in (("picture-uri", f.as_uri()), ("picture-options", "zoom")):
        subprocess.run(["gsettings", "set", "org.cinnamon.desktop.background", key, value], check=True)
    print(f"wallpaper: {f.name}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "register":
        register()
    elif cmd == "unregister":
        unregister()
    elif cmd == "set" and len(sys.argv) == 3 and sys.argv[2] in ("dark", "light"):
        set_wallpaper(sys.argv[2])
    else:
        sys.exit(__doc__)
