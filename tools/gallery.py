#!/usr/bin/env python3
"""Widget gallery for checking the theme.

  GTK_THEME=NalaMint tools/gallery.py            header-bar window (client-side frame)
  GTK_THEME=NalaMint tools/gallery.py --classic  menubar + toolbar window (Muffin frame)
"""
import sys

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib  # noqa: E402

CLASSIC = "--classic" in sys.argv
TITLE = "NalaMint Gallery Classic" if CLASSIC else "NalaMint Gallery"


def row(*widgets, spacing=8):
    box = Gtk.Box(spacing=spacing)
    for w in widgets:
        box.pack_start(w, False, False, 0)
    return box


def col(*widgets, spacing=10):
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=spacing)
    for w in widgets:
        box.pack_start(w, False, False, 0)
    return box


def button(label, *classes, sensitive=True):
    b = Gtk.Button(label=label)
    for c in classes:
        b.get_style_context().add_class(c)
    b.set_sensitive(sensitive)
    return b


def controls_page():
    # buttons
    tog = Gtk.ToggleButton(label="Toggle")
    tog.set_active(True)
    linked = Gtk.Box()
    linked.get_style_context().add_class("linked")
    for name in ("go-previous-symbolic", "go-next-symbolic"):
        linked.add(Gtk.Button.new_from_icon_name(name, Gtk.IconSize.BUTTON))
    seg = Gtk.Box()
    seg.get_style_context().add_class("linked")
    first = None
    for label in ("Day", "Week", "Month"):
        r = Gtk.RadioButton.new_with_label_from_widget(first, label)
        r.set_mode(False)
        first = first or r
        seg.add(r)
    buttons = col(
        row(button("Button"), button("Default", "suggested-action"),
            button("Delete", "destructive-action"), button("Flat", "flat"),
            button("Disabled", sensitive=False), tog),
        row(linked, seg, Gtk.Button.new_from_icon_name("open-menu-symbolic", Gtk.IconSize.BUTTON),
            button("●", "circular")),
    )

    # entries
    entry = Gtk.Entry(placeholder_text="Placeholder text")
    filled = Gtk.Entry(text="Selected text")
    search = Gtk.SearchEntry(placeholder_text="Search")
    disabled = Gtk.Entry(text="Disabled", sensitive=False)
    spin = Gtk.SpinButton.new_with_range(0, 100, 1)
    spin.set_value(42)
    combo = Gtk.ComboBoxText()
    for t in ("Automatic", "Light", "Dark"):
        combo.append_text(t)
    combo.set_active(0)
    combo_entry = Gtk.ComboBoxText.new_with_entry()
    combo_entry.append_text("Editable")
    combo_entry.set_active(0)
    entries = col(row(entry, filled, search), row(disabled, spin, combo, combo_entry))

    # toggles
    c1 = Gtk.CheckButton(label="Checked"); c1.set_active(True)
    c2 = Gtk.CheckButton(label="Unchecked")
    c3 = Gtk.CheckButton(label="Mixed"); c3.set_inconsistent(True)
    c4 = Gtk.CheckButton(label="Disabled", sensitive=False); c4.set_active(True)
    r1 = Gtk.RadioButton(label="Radio on")
    r2 = Gtk.RadioButton.new_with_label_from_widget(r1, "Radio off")
    s1 = Gtk.Switch(); s1.set_active(True)
    s2 = Gtk.Switch()
    toggles = row(c1, c2, c3, c4, r1, r2, s1, s2, spacing=14)

    # ranges
    scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
    scale.set_value(60); scale.set_draw_value(False); scale.set_size_request(220, -1)
    marks = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 25)
    marks.set_value(25); marks.set_draw_value(False); marks.set_size_request(220, -1)
    for v in range(0, 101, 25):
        marks.add_mark(v, Gtk.PositionType.BOTTOM, None)
    prog = Gtk.ProgressBar(fraction=0.65); prog.set_size_request(220, -1)
    level = Gtk.LevelBar(value=0.7); level.set_size_request(220, -1)
    ranges = col(row(scale, marks), row(prog, level), spacing=14)

    page = col(buttons, Gtk.Separator(), entries, Gtk.Separator(), toggles,
               Gtk.Separator(), ranges, spacing=14)
    page.set_border_width(18)
    return page


def lists_page():
    store = Gtk.ListStore(str, str, int, bool)
    for i, (name, kind) in enumerate([("Documents", "Folder"), ("Photos", "Folder"),
                                       ("notes.txt", "Text"), ("budget.ods", "Spreadsheet"),
                                       ("theme.scss", "Source"), ("song.flac", "Audio")]):
        store.append([name, kind, (i * 37) % 100, i % 2 == 0])
    tree = Gtk.TreeView(model=store)
    tree.append_column(Gtk.TreeViewColumn("Name", Gtk.CellRendererText(), text=0))
    tree.append_column(Gtk.TreeViewColumn("Kind", Gtk.CellRendererText(), text=1))
    tree.append_column(Gtk.TreeViewColumn("Progress", Gtk.CellRendererProgress(), value=2))
    tree.append_column(Gtk.TreeViewColumn("Done", Gtk.CellRendererToggle(), active=3))
    tree.get_selection().select_path(Gtk.TreePath(1))
    sw = Gtk.ScrolledWindow()
    sw.add(tree)
    sw.set_size_request(380, 220)

    sidebar = Gtk.PlacesSidebar()
    sidebar.set_size_request(180, -1)

    nb = Gtk.Notebook()
    for t in ("General", "Appearance", "Advanced"):
        lab = Gtk.Label(label=f"{t} settings")
        lab.set_margin_top(30); lab.set_margin_bottom(30)
        nb.append_page(lab, Gtk.Label(label=t))

    info = Gtk.InfoBar(message_type=Gtk.MessageType.INFO)
    info.get_content_area().add(Gtk.Label(label="An update is available."))
    info.add_button("Install", 1)
    warn = Gtk.InfoBar(message_type=Gtk.MessageType.WARNING)
    warn.get_content_area().add(Gtk.Label(label="Disk almost full."))

    right = col(sw, nb, info, warn)
    page = Gtk.Box(spacing=0)
    page.pack_start(sidebar, False, False, 0)
    right.set_border_width(14)
    page.pack_start(right, True, True, 0)
    return page


def build():
    win = Gtk.Window(title=TITLE)
    win.set_default_size(820, 560)
    outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    win.add(outer)

    stack = Gtk.Stack()
    stack.add_titled(controls_page(), "controls", "Controls")
    stack.add_titled(lists_page(), "lists", "Lists")
    switcher = Gtk.StackSwitcher(stack=stack)

    menu = Gtk.Menu()
    for label in ("New Window", "Open…", "Save"):
        menu.append(Gtk.MenuItem(label=label))
    menu.append(Gtk.SeparatorMenuItem())
    chk = Gtk.CheckMenuItem(label="Show Hidden Files"); chk.set_active(True)
    menu.append(chk)
    menu.append(Gtk.MenuItem(label="Quit"))
    menu.show_all()

    if CLASSIC:
        menubar = Gtk.MenuBar()
        for label in ("File", "Edit", "View", "Help"):
            item = Gtk.MenuItem(label=label)
            if label == "File":
                item.set_submenu(menu)
            menubar.append(item)
        outer.pack_start(menubar, False, False, 0)
        tb = Gtk.Toolbar()
        tb.get_style_context().add_class("primary-toolbar")
        for icon in ("go-previous-symbolic", "go-next-symbolic", "go-up-symbolic", "view-refresh-symbolic"):
            tb.insert(Gtk.ToolButton(icon_name=icon), -1)
        tb.insert(Gtk.SeparatorToolItem(), -1)
        item = Gtk.ToolItem()
        item.add(switcher)
        tb.insert(item, -1)
        outer.pack_start(tb, False, False, 0)
    else:
        hb = Gtk.HeaderBar(show_close_button=True)
        hb.set_custom_title(switcher)
        mb = Gtk.MenuButton(popup=menu)
        mb.add(Gtk.Image.new_from_icon_name("open-menu-symbolic", Gtk.IconSize.BUTTON))
        hb.pack_end(mb)
        if "--popup-menu" in sys.argv:
            GLib.timeout_add(2500, lambda: mb.set_active(True) and False)
        hb.pack_start(button("Add", "suggested-action"))
        win.set_titlebar(hb)

    outer.pack_start(stack, True, True, 0)
    if CLASSIC:
        sb = Gtk.Statusbar()
        sb.push(0, "6 items, 2 selected")
        outer.pack_start(sb, False, False, 0)

    win.set_title(TITLE)
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    page = sys.argv[sys.argv.index("--page") + 1] if "--page" in sys.argv else None
    if page:
        GLib.idle_add(stack.set_visible_child_name, page)


build()
Gtk.main()
