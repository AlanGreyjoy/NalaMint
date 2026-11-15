#!/usr/bin/env python3
"""Build NalaMint and NalaMint-Dark into ./build from ./src.

Usage: ./build.py            build both variants
       ./build.py --install  build, then copy into ~/.themes
"""
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
BUILD = ROOT / "build"
GEN = BUILD / ".gen"
THEMES = {"light": "NalaMint", "dark": "NalaMint-Dark"}


def palette(variant):
    data = tomllib.loads((SRC / "palette.toml").read_text())
    return {**data["common"], **data[variant], "variant": variant}


def write_scss_palette(variant):
    out = GEN / variant
    out.mkdir(parents=True, exist_ok=True)
    lines = [f"// generated from src/palette.toml ({variant}) — do not edit"]
    for key, value in palette(variant).items():
        if key == "variant":
            lines.append(f"$variant: '{value}';")
        else:
            lines.append(f"${key}: {value};")
    (out / "_palette.scss").write_text("\n".join(lines) + "\n")
    return out


def sassc(entry, out_file, variant):
    gen = write_scss_palette(variant)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        ["sassc", "-t", "expanded", "-I", str(gen), "-I", str(entry.parent),
         str(entry), str(out_file)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        sys.exit(f"sassc failed on {entry.relative_to(ROOT)} ({variant}):\n{r.stderr.strip()}")


# ---------- window buttons (traffic lights) ----------

def circle(fill, ring, glyph=None):
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 14 14">',
        f'<circle cx="7" cy="7" r="5.5" fill="{fill}" stroke="{ring}" stroke-width="1"/>',
    ]
    if glyph:
        parts.append(glyph)
    parts.append("</svg>")
    return "".join(parts)


def glyphs(color):
    s = f'stroke="{color}" stroke-width="1.3" stroke-linecap="round" fill="none"'
    return {
        "close": f'<path d="M4.9 4.9 L9.1 9.1 M9.1 4.9 L4.9 9.1" {s}/>',
        "min": f'<path d="M4.2 7 L9.8 7" {s}/>',
        "max": f'<path d="M7 4.2 L7 9.8 M4.2 7 L9.8 7" {s}/>',
    }


def darken(hex_color, amount=0.18):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    r, g, b = (round(c * (1 - amount)) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def write_titlebuttons(out):
    """Traffic-light SVGs for GTK title buttons and Muffin frames."""
    out.mkdir(parents=True, exist_ok=True)
    p = palette("light")  # button colors are shared by both variants
    for name in ("close", "minimize", "maximize"):
        key = {"close": "close", "minimize": "min", "maximize": "max"}[name]
        fill, ring = p[f"wm_{key}"], p[f"wm_{key}_ring"]
        glyph = glyphs(p[f"wm_{key}_glyph"])[key]
        (out / f"titlebutton-{name}.svg").write_text(circle(fill, ring))
        (out / f"titlebutton-{name}-hover.svg").write_text(circle(fill, ring, glyph))
        (out / f"titlebutton-{name}-active.svg").write_text(
            circle(darken(fill), darken(ring), glyph))
    for variant in THEMES:
        q = palette(variant)
        (out / f"titlebutton-backdrop-{variant}.svg").write_text(
            circle(q["wm_unfocused"], q["wm_unfocused_ring"]))


def write_cinnamon_assets(variant, out):
    """Toggle, checkbox and radio images for the Cinnamon desktop theme."""
    out.mkdir(parents=True, exist_ok=True)
    p = palette(variant)
    accent = p["accent"]
    off_track = "#5a5a5e" if variant == "dark" else "#d9d9dc"
    box_border = "#6a6a6e" if variant == "dark" else "#bdbdc1"
    box_fill = "#3a3a3d" if variant == "dark" else "#ffffff"
    svg = lambda w, h, body: (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
                              f'viewBox="0 0 {w} {h}">{body}</svg>')
    knob = '<circle cx="{x}" cy="11" r="9" fill="#ffffff" stroke="rgba(0,0,0,0.12)" stroke-width="0.5"/>'
    (out / "toggle-on.svg").write_text(svg(38, 22,
        f'<rect width="38" height="22" rx="11" fill="{accent}"/>' + knob.format(x=27)))
    (out / "toggle-off.svg").write_text(svg(38, 22,
        f'<rect width="38" height="22" rx="11" fill="{off_track}"/>' + knob.format(x=11)))
    check = '<path d="M4.2 8.3 L6.9 11 L11.9 5.5" fill="none" stroke="#ffffff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
    (out / "checkbox.svg").write_text(svg(16, 16,
        f'<rect x="0.5" y="0.5" width="15" height="15" rx="4" fill="{accent}"/>' + check))
    (out / "checkbox-off.svg").write_text(svg(16, 16,
        f'<rect x="0.5" y="0.5" width="15" height="15" rx="4" fill="{box_fill}" stroke="{box_border}"/>'))
    (out / "radio.svg").write_text(svg(16, 16,
        f'<circle cx="8" cy="8" r="7.5" fill="{accent}"/><circle cx="8" cy="8" r="3" fill="#ffffff"/>'))
    (out / "radio-off.svg").write_text(svg(16, 16,
        f'<circle cx="8" cy="8" r="7" fill="{box_fill}" stroke="{box_border}"/>'))
    dot = "rgba(255,255,255,0.75)" if variant == "dark" else "rgba(0,0,0,0.55)"
    (out / "dock-dot.svg").write_text(svg(4, 4, f'<circle cx="2" cy="2" r="2" fill="{dot}"/>'))


# ---------- GTK4 / libadwaita ----------

def installed_libadwaita():
    """(library path, 'major.minor') of the system libadwaita, or (None, None)."""
    lib = Path("/usr/lib/x86_64-linux-gnu/libadwaita-1.so.0")
    if not lib.exists():
        return None, None
    ver = subprocess.run(["dpkg-query", "-W", "-f=${Version}", "libadwaita-1-0"],
                         capture_output=True, text=True).stdout
    major_minor = ".".join(ver.split("-")[0].split(".")[:2]) or "1.5"
    return lib.resolve(), major_minor


def gresource(lib, path):
    r = subprocess.run(["gresource", "extract", str(lib), path], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"gresource extract {path} failed: {r.stderr.strip()}")
    return r.stdout


def build_gtk4(variant, theme_dir):
    """libadwaita apps (Mint's libadwaita reads <theme>/libadwaita-X.Y/) and
    plain GTK4 apps (<theme>/gtk-4.0/). Both use libadwaita's own stylesheet,
    taken from the installed library, with NalaMint colors and overrides."""
    lib, version = installed_libadwaita()
    if not lib:
        print("  (no libadwaita installed; skipping GTK4)")
        return
    tmp = GEN / "gtk4"
    tmp.mkdir(parents=True, exist_ok=True)
    defaults = {}
    for v in THEMES:
        sassc(SRC / "libadwaita" / "defaults.scss", tmp / f"defaults-{v}.css", v)
        defaults[v] = (tmp / f"defaults-{v}.css").read_text()
    sassc(SRC / "libadwaita" / "overrides.scss", tmp / "overrides.css", variant)
    base = (f"/* libadwaita {version} stylesheet (LGPL-2.1+), extracted from {lib.name} by build.py */\n"
            + gresource(lib, "/org/gnome/Adwaita/styles/base.css")
            + "\n/* ---- NalaMint overrides (src/libadwaita/overrides.scss) ---- */\n"
            + (tmp / "overrides.css").read_text())

    adw = theme_dir / f"libadwaita-{version}"
    adw.mkdir(parents=True)
    (adw / "base.css").write_text(base)
    (adw / "defaults-light.css").write_text(defaults["light"])
    (adw / "defaults-dark.css").write_text(defaults["dark"])
    write_titlebuttons(adw / "assets")

    # Flatpak apps run a newer libadwaita that ignores themes but still reads
    # named colors; tools/flatpak.py copies this into each app's config dir as
    # user CSS (light colors, dark ones under prefers-color-scheme, overrides).
    flat = BUILD / "flatpak" / "gtk-4.0"
    flat.mkdir(parents=True, exist_ok=True)
    (flat / "gtk.css").write_text(
        "/* NalaMint for Flatpak libadwaita apps — generated by build.py */\n"
        + defaults["light"]
        + "\n@media (prefers-color-scheme: dark) {\n" + defaults["dark"] + "}\n\n"
        + (tmp / "overrides.css").read_text())
    write_titlebuttons(flat / "assets")

    gtk4 = theme_dir / "gtk-4.0"
    gtk4.mkdir(parents=True)
    # Plain GTK4 apps don't follow the color-scheme setting: gtk.css is this
    # variant, gtk-dark.css is for apps that ask for dark.
    (gtk4 / "gtk.css").write_text(defaults[variant] + base)
    (gtk4 / "gtk-dark.css").write_text(defaults["dark"] + base)
    write_titlebuttons(gtk4 / "assets")


# ---------- icon theme ----------

ICON_THEME = "NalaMint"
ICON_BASE = "Mint-L,Mint-Y,Adwaita,hicolor"     # everything we don't draw comes from here

# All icons are generated images (Codex CLI; prompts and sources in each
# folder's PROMPTS.md), cut from sheets by tools/slice_sheet.py and scaled to
# fixed sizes here. Map: (context dir, source file) -> icon names.
ICONS = {
    ("places", "folder"): ["folder", "folder-open", "folder-drag-accept", "folder-visiting"],
    ("places", "documents"): ["folder-documents"],
    ("places", "download"): ["folder-download"],
    ("places", "music"): ["folder-music"],
    ("places", "pictures"): ["folder-pictures"],
    ("places", "videos"): ["folder-videos"],
    ("places", "templates"): ["folder-templates"],
    ("places", "public"): ["folder-publicshare"],
    ("places", "desktop"): ["user-desktop"],
    ("places", "home"): ["user-home"],
    ("places", "network"): ["folder-remote"],
    ("places", "search"): ["folder-saved-search"],
    ("places", "trash"): ["user-trash"],
    ("places", "trash-full"): ["user-trash-full"],
    ("mimetypes", "folder"): ["inode-directory"],
    ("apps", "files"): ["system-file-manager", "nemo", "org.gnome.Nautilus"],
    ("apps", "settings"): ["preferences-desktop", "preferences-system", "cinnamon-settings"],
    ("apps", "software"): ["mintinstall", "system-software-install", "org.gnome.Software"],
    ("apps", "update"): ["mintupdate", "system-software-update"],
    ("apps", "terminal"): ["org.gnome.Terminal", "utilities-terminal", "terminal"],
    ("apps", "text-editor"): ["org.x.editor", "accessories-text-editor", "xed", "org.gnome.TextEditor"],
    ("apps", "calculator"): ["org.gnome.Calculator", "accessories-calculator"],
    ("apps", "system-monitor"): ["org.gnome.SystemMonitor", "utilities-system-monitor"],
    # second sheet (app-icons-sheet2-v1.png)
    ("apps", "document-viewer"): ["xreader", "org.gnome.Evince"],
    ("apps", "image-viewer"): ["xviewer", "org.gnome.eog"],
    ("apps", "media-player"): ["io.github.celluloid_player.Celluloid"],
    ("apps", "archive-manager"): ["org.gnome.FileRoller", "file-roller"],
    ("apps", "backup"): ["mintbackup"],
    ("apps", "snapshots"): ["timeshift"],
    ("apps", "drivers"): ["mintdrivers", "cs-drivers"],
    ("apps", "sources"): ["mintsources", "cs-sources"],
    ("apps", "system-info"): ["mintreport"],
    ("apps", "file-transfer"): ["org.x.Warpinator", "warpinator"],
    ("apps", "notes"): ["sticky"],
    ("apps", "screenshot"): ["org.gnome.Screenshot", "applets-screenshooter"],
    ("apps", "disks"): ["org.gnome.DiskUtility", "gnome-disks"],
    ("apps", "disk-usage"): ["org.gnome.baobab", "baobab"],
    ("apps", "calendar"): ["org.gnome.Calendar"],
    ("apps", "web-apps"): ["webapp-manager"],
    ("apps", "printers"): ["printer", "system-config-printer", "cs-printer"],
    ("apps", "passwords"): ["org.gnome.seahorse.Application", "seahorse"],
    ("apps", "scanner"): ["org.gnome.SimpleScan", "simple-scan"],
    ("apps", "renamer"): ["bulky"],
    ("apps", "launchpad"): ["nalamint-launchpad"],     # dock item, launchpad-source-v1.png
    # app-icons-sheet3-v1.png: remaining Mint apps + System Settings section headers
    ("apps", "fingerprints"): ["fingwit"],
    ("apps", "system-admin"): ["mintsysadm"],
    ("apps", "network-config"): ["preferences-system-network"],
    ("apps", "character-map"): ["accessories-character-map", "gucharmap"],
    ("apps", "power-stats"): ["org.gnome.PowerStats"],
    ("apps", "onscreen-keyboard"): ["onboard", "cinnamon-virtual-keyboard"],
    ("apps", "usb-writer"): ["mintstick"],
    ("apps", "welcome"): ["mintwelcome"],
    ("apps", "library"): ["thingy"],
    ("apps", "photos"): ["pix"],
    ("apps", "tv"): ["hypnotix"],
    ("apps", "theme-settings"): ["preferences-desktop-theme"],
    ("apps", "cat-appearance"): ["cs-cat-appearance"],
    ("apps", "cat-prefs"): ["cs-cat-prefs"],
    ("apps", "cat-hardware"): ["cs-cat-hardware"],
    ("apps", "cat-admin"): ["cs-cat-admin"],
    # System Settings pages (settings-icons-sheet{1,2}-v1.png); Mint-L keeps the
    # cs-* names under categories/, but lookup ignores the context directory
    **{("apps", n): [n] for n in [
        "cs-backgrounds", "cs-desktop-effects", "cs-fonts", "cs-themes", "cs-universal-access",
        "cs-user", "cs-actions", "cs-applets", "cs-date-time", "cs-desklets", "cs-desktop",
        "cs-extensions", "cs-general", "cs-gestures", "cs-overview", "cs-nightlight",
        "cs-notifications", "cs-panel", "cs-default-applications", "cs-privacy", "cs-screensaver",
        "cs-startup-programs", "cs-windows", "cs-workspaces", "cs-color", "cs-display", "cs-tablet",
        "cs-keyboard", "cs-mouse", "cs-network", "cs-power", "cs-sound", "cs-thunderbolt"]},
    ("apps", "input-method"): ["cs-input-method", "input-keyboard"],
    ("apps", "languages"): ["cs-language", "preferences-desktop-locale"],
    ("apps", "online-accounts"): ["gnome-online-accounts-gtk"],
    ("apps", "bluetooth"): ["cs-bluetooth", "blueman", "blueman-device"],
    ("apps", "firewall"): ["cs-firewall", "gufw"],
    ("apps", "login-window"): ["cs-login", "lightdm-settings"],
    ("apps", "users"): ["cs-user-accounts", "system-users"],
}
ICON_SIZES = [16, 22, 24, 32, 48, 64, 96, 128, 256]
CONTEXTS = {"places": "Places", "mimetypes": "MimeTypes", "apps": "Applications"}


def icon_source(context, name):
    """Generated PNG for an icon; mimetypes reuse the places art."""
    folder = "places" if context == "mimetypes" else context
    return SRC / "icons" / folder / f"{name}.png"


def scale_png(src, size, dest):
    import gi
    gi.require_version("GdkPixbuf", "2.0")
    from gi.repository import GdkPixbuf
    pb = GdkPixbuf.Pixbuf.new_from_file(str(src)).scale_simple(size, size, GdkPixbuf.InterpType.HYPER)
    pb.savev(str(dest), "png", [], [])


def build_icons():
    out = BUILD / "icons" / ICON_THEME
    shutil.rmtree(out, ignore_errors=True)
    used = {k: v for k, v in ICONS.items() if icon_source(*k).exists()}
    contexts = sorted({ctx for ctx, _ in used})
    dirs = {f"{ctx}/{n}": (str(n), CONTEXTS[ctx]) for ctx in contexts for n in ICON_SIZES}
    for d in dirs:
        (out / d).mkdir(parents=True)

    for (ctx, src_name), names in used.items():
        for n in ICON_SIZES:
            first = out / f"{ctx}/{n}" / f"{names[0]}.png"
            scale_png(icon_source(ctx, src_name), n, first)
            for alias in names[1:]:
                (out / f"{ctx}/{n}" / f"{alias}.png").symlink_to(first.name)

    index = ["[Icon Theme]", f"Name={ICON_THEME}",
             "Comment=macOS-style folders, trash and core app icons; the rest from " + ICON_BASE,
             f"Inherits={ICON_BASE}", "Directories=" + ",".join(dirs), ""]
    for d, (size, context) in dirs.items():
        index += [f"[{d}]", f"Size={size}", "Type=Fixed", f"Context={context}", ""]
    (out / "index.theme").write_text("\n".join(index))
    print(f"built {out.relative_to(ROOT)}")


def install_icons(names=(ICON_THEME,)):
    root = Path.home() / ".local/share/icons"
    for name in names:
        dest = root / name
        shutil.rmtree(dest, ignore_errors=True)
        shutil.copytree(BUILD / "icons" / ICON_THEME, dest)
        if name != ICON_THEME:
            idx = dest / "index.theme"
            idx.write_text(idx.read_text().replace(f"Name={ICON_THEME}", f"Name={name}", 1))
        subprocess.run(["gtk-update-icon-cache", "-q", "-f", "-t", str(dest)], check=False)
        print(f"installed {dest}")


# ---------- Qt (qt5ct color schemes) ----------

def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _hex(c):
    return "#" + "".join(f"{max(0, min(255, round(v))):02x}" for v in c)


def _mix(a, b, t):          # t = share of b
    a, b = _rgb(a), _rgb(b)
    return _hex([x + (y - x) * t for x, y in zip(a, b)])


def qt_scheme(variant):
    """qt5ct/qt6ct color scheme: 21 colors per state, in QPalette::ColorRole order."""
    p = palette(variant)
    dark = variant == "dark"
    fg, bg, base, accent = p["fg"], p["bg"], p["base"], p["accent"]
    # Fusion paints tab panels and group frames from Button, so in dark mode use
    # a value between the window and GTK's raised-button grey.
    button = _mix(bg, p["button"], 0.5) if dark else p["button"]
    roles = {
        "WindowText": fg, "Button": button,
        "Light": _mix(button, "#ffffff", 0.15 if dark else 0.6),
        "Midlight": _mix(button, "#ffffff", 0.07 if dark else 0.3),
        "Dark": _mix(bg, "#000000", 0.45 if dark else 0.25),
        "Mid": _mix(bg, "#000000", 0.25 if dark else 0.15),
        "Text": fg, "BrightText": "#ffffff", "ButtonText": fg, "Base": base, "Window": bg,
        "Shadow": "#000000" if dark else "#76767a",
        "Highlight": accent, "HighlightedText": p["accent_fg"],
        "Link": _mix(accent, "#ffffff", 0.2) if dark else accent,
        "LinkVisited": "#bf8cff" if dark else "#7346c9",
        "AlternateBase": _mix(base, fg, 0.03), "NoRole": "#000000",
        "ToolTipBase": p["popover"], "ToolTipText": fg,
        "PlaceholderText": _mix(bg, fg, 0.45),
    }
    disabled = dict(roles)
    for role in ("WindowText", "Text", "ButtonText", "PlaceholderText"):
        disabled[role] = _mix(bg, fg, 0.35)
    disabled["Highlight"] = _mix(bg, fg, 0.25)
    inactive = dict(roles)
    inactive["Highlight"] = p["selected_backdrop"]
    inactive["HighlightedText"] = fg
    line = lambda d: ", ".join(d.values())
    return ("[ColorScheme]\n"
            f"active_colors={line(roles)}\n"
            f"disabled_colors={line(disabled)}\n"
            f"inactive_colors={line(inactive)}\n")


def build_qt():
    out = BUILD / "qt"
    out.mkdir(parents=True, exist_ok=True)
    for variant, name in THEMES.items():
        (out / f"{name}.conf").write_text(qt_scheme(variant))
    print(f"built {out.relative_to(ROOT)}")


# ---------- theme previews (System Settings → Themes) ----------

def svg_to_png(svg, out):
    import gi
    gi.require_version("GdkPixbuf", "2.0")
    from gi.repository import GdkPixbuf
    loader = GdkPixbuf.PixbufLoader.new_with_type("svg")
    loader.write(svg.encode())
    loader.close()
    out.parent.mkdir(parents=True, exist_ok=True)
    loader.get_pixbuf().savev(str(out), "png", [], [])


def write_thumbnails(variant, theme_dir):
    import base64
    p = palette(variant)
    dark = variant == "dark"
    lights = "".join(
        f'<circle cx="{8 + i * 11}" cy="17.5" r="4.2" fill="{p[k]}" stroke="{p[k + "_ring"]}" stroke-width="0.6"/>'
        for i, k in enumerate(("wm_close", "wm_min", "wm_max")))
    button_fill, button_stroke = (p["button"], "none") if dark else ("#ffffff", "#c8c8cc")
    gtk = f"""<svg xmlns="http://www.w3.org/2000/svg" width="120" height="35" viewBox="0 0 120 35">
  {lights}
  <rect x="38.5" y="9.5" width="40" height="16" rx="4" fill="{button_fill}" stroke="{button_stroke}"/>
  <text x="58.5" y="21" font-family="Inter" font-size="8.5" text-anchor="middle" fill="{p['fg']}">Button</text>
  <rect x="84" y="11.5" width="12" height="12" rx="3" fill="{p['accent']}"/>
  <path d="M86.8 17.6l2.2 2.2 4.2-4.6" fill="none" stroke="#fff" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
  <rect x="99" y="11.5" width="19" height="12" rx="6" fill="{p['accent']}"/>
  <circle cx="112" cy="17.5" r="4.8" fill="#ffffff"/>
</svg>"""
    svg_to_png(gtk, theme_dir / "gtk-3.0" / "thumbnail.png")

    png = lambda f: base64.b64encode((SRC / "icons/apps" / f"{f}.png").read_bytes()).decode()
    plate = "rgba(40,40,43,0.85)" if dark else "rgba(246,246,248,0.9)"
    edge = "rgba(255,255,255,0.15)" if dark else "rgba(0,0,0,0.12)"
    dot = "rgba(255,255,255,0.75)" if dark else "rgba(0,0,0,0.55)"
    cin = f"""<svg xmlns="http://www.w3.org/2000/svg" width="247" height="60" viewBox="0 0 247 60">
  <rect x="38.5" y="6.5" width="170" height="47" rx="14" fill="{plate}" stroke="{edge}"/>
  <image x="48" y="11" width="34" height="34" href="data:image/png;base64,{png('files')}"/>
  <image x="89" y="11" width="34" height="34" href="data:image/png;base64,{png('terminal')}"/>
  <image x="130" y="11" width="34" height="34" href="data:image/png;base64,{png('settings')}"/>
  <image x="171" y="11" width="34" height="34" href="data:image/png;base64,{base64.b64encode((SRC / "icons/places/folder.png").read_bytes()).decode()}"/>
  <circle cx="65" cy="49" r="1.6" fill="{dot}"/>
  <circle cx="107" cy="49" r="1.6" fill="{dot}"/>
</svg>"""
    svg_to_png(cin, theme_dir / "cinnamon" / "thumbnail.png")


# ---------- wallpapers ----------

WALLPAPER_SIZE = (2560, 1440)
WALLPAPER_DIR = Path.home() / ".local/share/backgrounds/nalamint"


def build_wallpapers():
    """Generated wallpapers (src/wallpapers, provenance in PROMPTS.md) scaled to
    WALLPAPER_SIZE as JPEG. The newest -vN of each variant wins."""
    import gi
    gi.require_version("GdkPixbuf", "2.0")
    from gi.repository import GdkPixbuf
    out = BUILD / "wallpapers"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    for variant in THEMES:
        sources = sorted((SRC / "wallpapers").glob(f"nalamint-{variant}-v*.png"),
                         key=lambda f: int(f.stem.rsplit("-v", 1)[1]))
        if not sources:
            continue
        pb = GdkPixbuf.Pixbuf.new_from_file(str(sources[-1]))
        pb = pb.scale_simple(*WALLPAPER_SIZE, GdkPixbuf.InterpType.HYPER)
        pb.savev(str(out / f"nalamint-{variant}.jpg"), "jpeg", ["quality"], ["92"])
    print(f"built {out.relative_to(ROOT)}")


# ---------- assemble ----------

def build_theme(variant):
    name = THEMES[variant]
    theme_dir = BUILD / name
    shutil.rmtree(theme_dir, ignore_errors=True)
    theme_dir.mkdir(parents=True)

    # GTK 3
    gtk3 = SRC / "gtk-3.0"
    sassc(gtk3 / "gtk.scss", theme_dir / "gtk-3.0" / "gtk.css", variant)
    sassc(gtk3 / "gtk.scss", theme_dir / "gtk-3.0" / "gtk-dark.css", "dark")
    shutil.copytree(gtk3 / "assets", theme_dir / "gtk-3.0" / "assets")
    write_titlebuttons(theme_dir / "gtk-3.0" / "assets")

    # GTK 4 and libadwaita
    build_gtk4(variant, theme_dir)

    # Cinnamon desktop
    cin = SRC / "cinnamon"
    if (cin / "cinnamon.scss").exists():
        sassc(cin / "cinnamon.scss", theme_dir / "cinnamon" / "cinnamon.css", variant)
        write_cinnamon_assets(variant, theme_dir / "cinnamon" / "assets")

    write_thumbnails(variant, theme_dir)

    (theme_dir / "index.theme").write_text(
        "[Desktop Entry]\n"
        "Type=X-GNOME-Metatheme\n"
        f"Name={name}\n"
        "Comment=A rounded, macOS-inspired theme for Cinnamon\n"
        "Encoding=UTF-8\n\n"
        "[X-GNOME-Metatheme]\n"
        f"GtkTheme={name}\n"
        f"MetacityTheme={name}\n"
        "ButtonLayout=close,minimize,maximize:\n"
    )
    print(f"built {theme_dir.relative_to(ROOT)}")


def install():
    dest_root = Path.home() / ".themes"
    dest_root.mkdir(exist_ok=True)
    for name in THEMES.values():
        dest = dest_root / name
        shutil.rmtree(dest, ignore_errors=True)
        shutil.copytree(BUILD / name, dest)
        print(f"installed {dest}")
    ext_root = Path.home() / ".local/share/cinnamon/extensions"
    ext_root.mkdir(parents=True, exist_ok=True)
    for ext in (SRC / "extension").iterdir():
        dest = ext_root / ext.name
        shutil.rmtree(dest, ignore_errors=True)
        shutil.copytree(ext, dest)
        print(f"installed {dest}")
    applet_root = Path.home() / ".local/share/cinnamon/applets"
    applet_root.mkdir(parents=True, exist_ok=True)
    for applet in (SRC / "applet").iterdir():
        dest = applet_root / applet.name
        shutil.rmtree(dest, ignore_errors=True)
        shutil.copytree(applet, dest)
        print(f"installed {dest}")


if __name__ == "__main__":
    # The live watcher and a manual run can start at the same moment; take
    # turns instead of deleting each other's output mid-build.
    import fcntl
    BUILD.mkdir(exist_ok=True)
    lock = open(BUILD / ".build.lock", "w")
    fcntl.flock(lock, fcntl.LOCK_EX)
    for v in THEMES:
        build_theme(v)
    build_icons()
    build_qt()
    build_wallpapers()
    if "--install" in sys.argv:
        install()
        install_icons()
        WALLPAPER_DIR.mkdir(parents=True, exist_ok=True)
        for f in (BUILD / "wallpapers").glob("*.jpg"):
            shutil.copy(f, WALLPAPER_DIR / f.name)
            print(f"installed {WALLPAPER_DIR / f.name}")
