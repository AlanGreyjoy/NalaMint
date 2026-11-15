#!/usr/bin/env bash
# Switch this desktop to NalaMint.   Usage: tools/apply.sh [dark|light]
# Saves your current appearance settings once to build/original-settings.sh;
# run tools/revert.sh to restore them.
set -euo pipefail
cd "$(dirname "$0")/.."

variant="${1:-dark}"
case "$variant" in
  dark) theme="NalaMint-Dark" ;;
  light) theme="NalaMint" ;;
  *) echo "usage: $0 [dark|light]" >&2; exit 1 ;;
esac

mkdir -p build
if [ ! -f build/original-settings.sh ]; then
  {
    for k in gtk-theme icon-theme cursor-theme font-name; do
      echo "gsettings set org.cinnamon.desktop.interface $k \"$(gsettings get org.cinnamon.desktop.interface $k)\""
    done
    echo "gsettings set org.cinnamon.desktop.wm.preferences theme \"$(gsettings get org.cinnamon.desktop.wm.preferences theme)\""
    echo "gsettings set org.cinnamon.desktop.wm.preferences button-layout \"$(gsettings get org.cinnamon.desktop.wm.preferences button-layout)\""
    echo "gsettings set org.cinnamon.theme name \"$(gsettings get org.cinnamon.theme name)\""
  } > build/original-settings.sh
  echo "saved current settings to build/original-settings.sh"
fi

# Keys added after the first save: record each once, so revert.sh restores them
remember() {
  grep -q "$1 $2 " build/original-settings.sh ||
    echo "gsettings set $1 $2 \"$(gsettings get "$1" "$2")\"" >> build/original-settings.sh
}
remember org.x.apps.portal color-scheme
remember org.cinnamon.desktop.wm.preferences titlebar-font
remember org.gnome.desktop.interface font-name
remember org.gnome.desktop.interface document-font-name
remember org.nemo.desktop font
remember org.cinnamon.desktop.background picture-uri
remember org.cinnamon.desktop.background picture-options

./build.py --install
# Muffin draws window frames from the GTK theme, so one key covers apps and frames.
gsettings set org.cinnamon.desktop.interface gtk-theme "$theme"
gsettings set org.cinnamon.theme name "$theme"
gsettings set org.cinnamon.desktop.wm.preferences button-layout 'close,minimize,maximize:'
# libadwaita apps pick light or dark colors from this (via the XApp portal)
gsettings set org.x.apps.portal color-scheme "prefer-$variant"
# Icons: NalaMint folders/places on top of Mint-L. Font: Inter (closest free match to SF Pro)
gsettings set org.cinnamon.desktop.interface icon-theme 'NalaMint'
gsettings set org.cinnamon.desktop.interface font-name 'Inter 10'
gsettings set org.gnome.desktop.interface font-name 'Inter 10'
gsettings set org.gnome.desktop.interface document-font-name 'Inter 10'
gsettings set org.cinnamon.desktop.wm.preferences titlebar-font 'Inter Bold 10'
gsettings set org.nemo.desktop font 'Inter 10'
# Rounds the bottom corners Muffin leaves square (and frameless apps' corners)
python3 tools/extlist.py add nalamint-corners@nalamint
# Blur behind the panel + dark panel text on bright wallpaper
python3 tools/extlist.py add nalamint-menubar@nalamint
# Qt5 apps: NalaMint palette through qt5ct (prints a hint if qt5ct isn't installed)
python3 tools/qt.py apply "$variant"
# Flatpak apps: theme folders shared read-only + libadwaita colors per app
python3 tools/flatpak.py apply
# NalaMint wallpapers appear in System Settings → Backgrounds (not set automatically;
# tools/wallpaper.py set dark|light does that)
python3 tools/wallpaper.py register
echo "applied $theme"
