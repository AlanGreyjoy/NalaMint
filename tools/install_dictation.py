#!/usr/bin/python3
"""Install the NalaMint Dictation companion app for the current user."""

import argparse
import os
from pathlib import Path
import shutil

from gi.repository import GLib


ROOT = Path(__file__).resolve().parents[1]
APP_ID = "io.github.AlanGreyjoy.NalaMint.Dictation"
DATA = Path(GLib.get_user_data_dir())
TARGET = DATA / "nalamint" / "dictation"
ICON = "nalamint-dictation.png"
MODEL = "ggml-base.en-q5_1.bin"


def install(engine, model):
    TARGET.mkdir(parents=True, exist_ok=True)
    source = ROOT / "src" / "apps" / "dictation"
    for name in ("app.py", "desktop.py", "speech.py", "style.css"):
        shutil.copy(source / name, TARGET / name)
    shutil.copy(ROOT / "src" / "icons" / "apps" / ICON, TARGET / ICON)
    if engine:
        shutil.copy(engine, TARGET / "whisper-cli")
    if model:
        shutil.copy(model, TARGET / MODEL)

    launcher = GLib.KeyFile.new()
    group = "Desktop Entry"
    for key, value in (
        ("Type", "Application"),
        ("Name", "NalaMint Dictation"),
        ("Comment", "Hold a shortcut to dictate into the focused app"),
        ("Icon", str(TARGET / ICON)),
        ("Categories", "Utility;Accessibility;"),
        ("Keywords", "voice;speech;dictation;"),
        ("StartupWMClass", APP_ID),
    ):
        launcher.set_string(group, key, value)
    # Exec has its own quoting syntax, processed after Desktop Entry escaping.
    path = str(TARGET / "app.py")
    path = "".join("\\" + c if c in '\\"`$' else c for c in path).replace("%", "%%")
    launcher.set_string(group, "Exec", f'/usr/bin/python3 "{path}"')
    launcher.set_boolean(group, "StartupNotify", True)
    launcher.set_boolean(group, "Terminal", False)
    applications = DATA / "applications"
    applications.mkdir(parents=True, exist_ok=True)
    launcher.save_to_file(str(applications / f"{APP_ID}.desktop"))
    print(f"Installed NalaMint Dictation in {applications}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", type=Path, help="copy an existing whisper-cli executable")
    parser.add_argument("--model", type=Path, help=f"copy an existing {MODEL} file")
    args = parser.parse_args()
    if args.engine and (not args.engine.is_file() or not os.access(args.engine, os.X_OK)):
        parser.error("--engine must be an executable file")
    if args.model and not args.model.is_file():
        parser.error("--model must be a local model file")
    install(args.engine, args.model)
