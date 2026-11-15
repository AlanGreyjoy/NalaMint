#!/usr/bin/env python3
"""Make Qt5 apps follow NalaMint through qt5ct (Fusion style + NalaMint palette).

  tools/qt.py apply dark|light   write ~/.config/qt5ct, set QT_QPA_PLATFORMTHEME=qt5ct
  tools/qt.py revert             undo both

Qt5's built-in GTK3 integration passes on fonts, icons and dialogs but not
colors, so Qt5 apps stay light. qt5ct (sudo apt install qt5ct) fills that gap.
The variable goes into ~/.xsessionrc (next login) and into the running
Cinnamon and D-Bus environments (apps started from now on).
Qt6 apps can't load qt5ct; they keep Qt's GTK3 integration.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOME = Path.home()
QT5CT = HOME / ".config/qt5ct"
XSESSIONRC = HOME / ".xsessionrc"
BACKUP = ROOT / "build/qt5ct.conf.orig"
STATE = ROOT / "build/qt-state.json"
PLUGIN = Path("/usr/lib/x86_64-linux-gnu/qt5/plugins/platformthemes/libqt5ct.so")
MARK_BEGIN, MARK_END = "# >>> NalaMint Qt >>>", "# <<< NalaMint Qt <<<"
THEMES = {"dark": "NalaMint-Dark", "light": "NalaMint"}


def gsetting(schema, key):
    out = subprocess.run(["gsettings", "get", schema, key], capture_output=True, text=True).stdout
    return out.strip().strip("'")


def qt_font(spec, fallback):
    """'Inter Bold 10' -> 'Inter,10,-1,5,75,0,0,0,0,0' (QFont::toString)."""
    parts = (spec or fallback).rsplit(" ", 1)
    family, size = (parts[0], parts[1]) if len(parts) == 2 and parts[1].isdigit() else (spec, "10")
    return f'"{family},{size},-1,5,50,0,0,0,0,0"'


def set_session_env(value):
    js = (f"imports.gi.GLib.setenv('QT_QPA_PLATFORMTHEME', '{value}', true); 'set'" if value
          else "imports.gi.GLib.unsetenv('QT_QPA_PLATFORMTHEME'); 'unset'")
    subprocess.run([sys.executable, str(ROOT / "tools/ceval.py"), js], capture_output=True)
    subprocess.run(["dbus-update-activation-environment", "--systemd",
                    f"QT_QPA_PLATFORMTHEME={value}"], capture_output=True)


def xsessionrc(add):
    text = XSESSIONRC.read_text() if XSESSIONRC.exists() else ""
    if MARK_BEGIN in text:
        start = text.index(MARK_BEGIN)
        end = text.index(MARK_END) + len(MARK_END)
        text = (text[:start] + text[end:]).strip("\n")
        text = text + "\n" if text else ""
    if add:
        text += f"{MARK_BEGIN}\nexport QT_QPA_PLATFORMTHEME=qt5ct\n{MARK_END}\n"
    if text:
        XSESSIONRC.write_text(text)
    elif XSESSIONRC.exists():
        XSESSIONRC.unlink()


def apply(variant):
    if not PLUGIN.exists():
        print("qt5ct is not installed; Qt5 apps keep their default colors.\n"
              "  sudo apt install qt5ct   then run: tools/qt.py apply " + variant)
        return
    theme = THEMES[variant]
    (QT5CT / "colors").mkdir(parents=True, exist_ok=True)
    conf = QT5CT / "qt5ct.conf"
    if not STATE.exists():                      # remember what was there before us
        if conf.exists():
            shutil.copy(conf, BACKUP)
        STATE.write_text(json.dumps({"had_conf": conf.exists()}))
    for name in THEMES.values():
        shutil.copy(ROOT / "build/qt" / f"{name}.conf", QT5CT / "colors" / f"{name}.conf")

    conf.write_text(f"""[Appearance]
color_scheme_path={QT5CT}/colors/{theme}.conf
custom_palette=true
icon_theme=NalaMint
standard_dialogs=gtk3
style=Fusion

[Fonts]
fixed={qt_font(gsetting('org.gnome.desktop.interface', 'monospace-font-name'), 'Monospace 10')}
general={qt_font(gsetting('org.cinnamon.desktop.interface', 'font-name'), 'Inter 10')}

[Interface]
buttonbox_layout=1
dialog_buttons_have_icons=0
menus_have_icons=true
underline_shortcut=1
""")
    xsessionrc(add=True)
    set_session_env("qt5ct")
    print(f"Qt5 apps: {theme} colors via qt5ct (restart open Qt apps to see it)")


def revert():
    conf = QT5CT / "qt5ct.conf"
    if STATE.exists():
        state = json.loads(STATE.read_text())
        if state.get("had_conf") and BACKUP.exists():
            shutil.copy(BACKUP, conf)
        elif conf.exists():
            conf.unlink()
        STATE.unlink()
    for name in THEMES.values():
        f = QT5CT / "colors" / f"{name}.conf"
        if f.exists():
            f.unlink()
    for d in (QT5CT / "colors", QT5CT):        # remove folders we created, if now empty
        if d.exists() and not any(d.iterdir()):
            d.rmdir()
    xsessionrc(add=False)
    set_session_env("")
    print("Qt settings reverted")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("apply", "revert"):
        sys.exit(__doc__)
    apply(sys.argv[2] if len(sys.argv) > 2 else "dark") if sys.argv[1] == "apply" else revert()
