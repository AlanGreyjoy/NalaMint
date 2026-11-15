#!/usr/bin/env bash
# Restore the appearance settings saved by tools/apply.sh.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -f build/original-settings.sh ]; then
  echo "nothing to restore: build/original-settings.sh not found" >&2
  exit 1
fi
bash build/original-settings.sh
python3 tools/extlist.py remove nalamint-corners@nalamint
python3 tools/extlist.py remove nalamint-menubar@nalamint
# Put the panel layout back if tools/layout.py dock changed it
[ -f build/original-layout.json ] && python3 tools/layout.py restore
python3 tools/qt.py revert
python3 tools/flatpak.py revert
python3 tools/wallpaper.py unregister
echo "restored settings from build/original-settings.sh"
