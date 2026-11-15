// NalaMint Launchpad: a full-screen grid of apps over the blurred wallpaper,
// opened from the dock icon or the Super key, like Launchpad on macOS.
// Pages flip with the scroll wheel, arrow keys or the dots; typing searches.
// Icons can be dragged to a new place, onto another icon to make a folder,
// and out of a folder again. The order is kept in the applet's settings.

const Applet = imports.ui.applet;
const Main = imports.ui.main;
const PopupMenu = imports.ui.popupMenu;
const Settings = imports.ui.settings;
const { CMenu, Clutter, Cinnamon, GLib, Gtk, Pango, St } = imports.gi;

// Two-pass gaussian blur, same as the menu-bar extension (25 taps, clamped
// to the texture so the screen edges don't fade).
const BLUR_SHADER = `
uniform sampler2D tex;
uniform float w;
uniform float h;
uniform float radius;
uniform float dirx;
uniform float diry;
void main() {
  vec2 uv = cogl_tex_coord_in[0].st;
  vec2 stepv = vec2(dirx / w, diry / h) * (radius / 12.0);
  vec2 lo = vec2(0.5 / w, 0.5 / h);
  vec2 hi = vec2(1.0) - lo;
  vec4 sum = vec4(0.0);
  float total = 0.0;
  for (int i = -12; i <= 12; i++) {
    float x = float(i);
    float wt = exp(-x * x / 72.0);
    sum += texture2D(tex, clamp(uv + stepv * x, lo, hi)) * wt;
    total += wt;
  }
  // The X11 background texture can carry alpha 0; the wallpaper is opaque
  cogl_color_out = vec4((sum / total).rgb, 1.0) * cogl_color_in;
}
`;

// Clutter treats integral JS numbers as ints; these uniforms are floats.
function asFloat(v) {
    return v + 0.00001;
}

function blurEffect(dirX, dirY, w, h, radius) {
    let effect = new Clutter.ShaderEffect({ shader_type: Clutter.ShaderType.FRAGMENT_SHADER });
    effect.set_shader_source(BLUR_SHADER);
    effect.set_uniform_value('tex', 0);
    effect.set_uniform_value('dirx', asFloat(dirX));
    effect.set_uniform_value('diry', asFloat(dirY));
    effect.set_uniform_value('w', asFloat(w));
    effect.set_uniform_value('h', asFloat(h));
    effect.set_uniform_value('radius', asFloat(radius));
    return effect;
}

const ANIM_MS = 200;
const ZOOM = 1.06;            // content starts slightly larger and settles
const EASE = Clutter.AnimationMode.EASE_OUT_QUAD;

const DRAG_START = 10;        // px the pointer moves before a press becomes a drag
const REORDER_MS = 250;       // pointer rests this long before icons make room
const FOLDER_MS = 450;        // ... over an icon's center before a folder forms
const EDGE_MS = 650;          // ... at the left/right edge before the page flips
const EDGE_PX = 70;

// First run: Mint menu categories that start out as folders
const DEFAULT_FOLDERS = { Administration: 'Utilities', Preferences: 'Utilities', Games: 'Games' };
const KEEP_TOP = new Set(['cinnamon-settings.desktop', 'mintinstall.desktop', 'mintupdate.desktop']);

function isSettingsPage(app) {
    let info = app.get_app_info();
    return app.get_id().startsWith('cinnamon-settings-') ||
        (info.get_categories() || '').includes('X-Cinnamon-Settings-Panel');
}

const WORDS = /[\s\-_.,:;/()]+/;

function startsWord(text, q) {
    return !!text && text.toLowerCase().split(WORDS).some(word => word.startsWith(q));
}

// Lower is better; -1 = no match. Only word starts match ("ter" finds
// Terminal, not Character Map), like Spotlight.
function matchScore(app, q) {
    let name = app.get_name().toLowerCase();
    if (name.startsWith(q))
        return 0;
    if (startsWord(name, q))
        return 1;
    let info = app.get_app_info();
    if (startsWord(info.get_generic_name(), q) || (info.get_keywords() || []).some(k => startsWord(k, q)))
        return 2;
    if ((info.get_executable() || '').toLowerCase().startsWith(q))
        return 3;
    return -1;
}

function clamp(v, lo, hi) {
    return Math.max(lo, Math.min(hi, v));
}

// Cell positions for items laid out in pages of cols x rows; page p starts
// at x = p * pageW. Items are (cellW - 12) x (cellH - 12), 6 px inside their cell.
class Grid {
    constructor(cols, rows, cellW, cellH, pageW, areaH) {
        Object.assign(this, { cols, rows, cellW, cellH, pageW, areaH });
        this.per = cols * rows;
        this.x0 = Math.round((pageW - cols * cellW) / 2);
        this.y0 = Math.max(0, Math.round((areaH - rows * cellH) / 2));
    }

    pages(n) {
        return Math.max(1, Math.ceil(n / this.per));
    }

    slot(i) {
        let p = Math.floor(i / this.per), k = i % this.per;
        return [p * this.pageW + this.x0 + (k % this.cols) * this.cellW + 6,
                this.y0 + Math.floor(k / this.cols) * this.cellH + 6];
    }

    // Cell under a point (strip coordinates) and that cell's center
    cellAt(x, y) {
        let p = Math.max(0, Math.floor(x / this.pageW));
        let col = clamp(Math.floor((x - p * this.pageW - this.x0) / this.cellW), 0, this.cols - 1);
        let row = clamp(Math.floor((y - this.y0) / this.cellH), 0, this.rows - 1);
        let index = p * this.per + row * this.cols + col;
        let [sx, sy] = this.slot(index);
        return { index, cx: sx + (this.cellW - 12) / 2, cy: sy + (this.cellH - 12) / 2 };
    }
}

class Launchpad {
    constructor(applet) {
        this.applet = applet;
        this.appSys = Cinnamon.AppSystem.get_default();
        this.actor = null;
        this.isOpen = false;
        this.dirty = true;
        this.timers = {};
        this.signals = [
            [this.appSys, this.appSys.connect('installed-changed', () => {
                this.dirty = true;
                this.appCache = null;
            })],
            [Main.layoutManager, Main.layoutManager.connect('monitors-changed', () => {
                this.close(true);
                this.dirty = true;
            })],
        ];
    }

    // ---- apps and the saved layout ----

    // The same apps the Mint menu lists: its menu tree, minus NoDisplay
    // entries. Also notes each app's top-level menu category.
    apps() {
        if (this.appCache)
            return this.appCache;
        let seen = new Set();
        this.category = new Map();       // app id -> [menu id, display name]
        let walk = (dir, top) => {
            let iter = dir.iter(), type;
            while ((type = iter.next()) !== CMenu.TreeItemType.INVALID) {
                if (type === CMenu.TreeItemType.ENTRY) {
                    let app = this.appSys.lookup_app(iter.get_entry().get_desktop_file_id());
                    if (app && !app.get_nodisplay()) {
                        seen.add(app);
                        if (top && !this.category.has(app.get_id()))
                            this.category.set(app.get_id(), [top.get_menu_id(), top.get_name()]);
                    }
                } else if (type === CMenu.TreeItemType.DIRECTORY) {
                    let sub = iter.get_directory();
                    if (!sub.get_is_nodisplay())
                        walk(sub, top || sub);
                }
            }
        };
        walk(this.appSys.get_tree().get_root_directory(), null);
        return this.appCache = [...seen];
    }

    gridApps() {
        let hide = this.applet.hideSettingsPages;
        return this.apps().filter(app => !(hide && isSettingsPage(app)))
            .sort((a, b) => a.get_name().localeCompare(b.get_name()));
    }

    entryName(entry) {
        return entry.type === 'folder' ? entry.name : this.byId.get(entry.id).get_name();
    }

    // Saved order and folders; apps that are new since then go at the end
    loadEntries() {
        let apps = this.gridApps();
        this.byId = new Map(apps.map(app => [app.get_id(), app]));
        let saved = this.applet.settings.getValue('layout');
        if (!saved || !Array.isArray(saved.items))
            return this.defaultEntries(apps);
        let used = new Set(), entries = [];
        let fresh = id => this.byId.has(id) && !used.has(id) && used.add(id);
        for (let item of saved.items) {
            if (typeof item === 'string') {
                if (fresh(item))
                    entries.push({ type: 'app', id: item });
            } else if (item && Array.isArray(item.apps)) {
                let ids = item.apps.filter(fresh);
                if (ids.length > 1)
                    entries.push({ type: 'folder', name: item.name || 'Folder', apps: ids });
                else if (ids.length === 1)
                    entries.push({ type: 'app', id: ids[0] });
            }
        }
        for (let app of apps)
            if (fresh(app.get_id()))
                entries.push({ type: 'app', id: app.get_id() });
        return entries;
    }

    // First run: A–Z, with system tools and games gathered in folders
    defaultEntries(apps) {
        let folders = new Map(), entries = [];
        for (let app of apps) {
            let id = app.get_id();
            let name = DEFAULT_FOLDERS[(this.category.get(id) || [])[0]];
            if (!name || KEEP_TOP.has(id)) {
                entries.push({ type: 'app', id });
                continue;
            }
            if (!folders.has(name)) {
                let folder = { type: 'folder', name, apps: [] };
                folders.set(name, folder);
                entries.push(folder);
            }
            folders.get(name).apps.push(id);
        }
        entries = entries.flatMap(e => e.type === 'folder' && e.apps.length < 2
            ? e.apps.map(id => ({ type: 'app', id })) : [e]);
        return entries.sort((a, b) => this.entryName(a).localeCompare(this.entryName(b)));
    }

    save() {
        let items = this.entries.map(e => e.type === 'app' ? e.id : { name: e.name, apps: e.apps.slice() });
        this.applet.settings.setValue('layout', { version: 1, items });
    }

    // New folder from a drop: named after the apps' shared menu category
    folderName(ids) {
        let names = ids.map(id => (this.category.get(id) || [])[1]);
        return names[0] && names.every(n => n === names[0]) ? names[0] : 'Folder';
    }

    // ---- building ----

    layout(mon) {
        let W = mon.width, H = mon.height;
        let iconSize = H >= 1300 ? 96 : H >= 1000 ? 80 : 64;
        let searchY = Math.round(H * 0.045);
        let gridY = searchY + 80;
        let dotsY = H - 70;
        let gridH = dotsY - 30 - gridY;
        let cols = Math.max(3, Math.min(7, Math.floor(W * 0.86 / (iconSize * 1.7))));
        let rows = Math.max(2, Math.min(5, Math.floor(gridH / (iconSize * 1.6))));
        let cellW = Math.min(Math.floor(W * 0.86 / cols), Math.round(iconSize * 2.6));
        let cellH = Math.min(Math.floor(gridH / rows), Math.round(iconSize * 2.2));
        return { W, H, iconSize, searchY, gridY, gridH, dotsY, cols, rows, cellW, cellH };
    }

    build(mon) {
        this.destroyActor();
        this.apps();
        let g = this.geo = this.layout(mon);
        this.monitorKey = [mon.x, mon.y, mon.width, mon.height].join(',');
        this.radius = this.applet.blurRadius;

        let actor = this.actor = new St.Widget({
            name: 'nalamint-launchpad', style_class: 'nalamint-launchpad', reactive: true,
            visible: false, x: mon.x, y: mon.y, width: g.W, height: g.H,
        });

        // Opaque base: windows, desktop icons and panels must not show through
        actor.add_child(new St.Widget({ style: 'background-color: black;', width: g.W, height: g.H }));
        // Wallpaper copy, blurred in two passes. Every level clips, otherwise
        // the offscreen textures cover the whole (multi-monitor) background.
        let clone = new Clutter.Clone({ source: global.background_actor, x: -mon.x, y: -mon.y });
        let outer = new Clutter.Actor({ clip_to_allocation: true, width: g.W, height: g.H });
        if (this.radius > 0) {
            let horiz = new Clutter.Actor({ clip_to_allocation: true, width: g.W, height: g.H });
            let vert = new Clutter.Actor({ clip_to_allocation: true, width: g.W, height: g.H });
            vert.add_child(clone);
            horiz.add_child(vert);
            outer.add_child(horiz);
            horiz.add_effect(blurEffect(1, 0, g.W, g.H, this.radius));
            vert.add_effect(blurEffect(0, 1, g.W, g.H, this.radius));
        } else {
            outer.add_child(clone);
        }
        actor.add_child(outer);
        actor.add_child(new St.Widget({ style_class: 'nalamint-launchpad-shade', width: g.W, height: g.H }));

        this.content = new Clutter.Actor({ width: g.W, height: g.H });
        this.content.set_pivot_point(0.5, 0.5);
        actor.add_child(this.content);

        // Search field, centered at the top
        let top = new St.Widget({ layout_manager: new Clutter.BinLayout(), width: g.W, y: g.searchY });
        this.entry = new St.Entry({
            style_class: 'nalamint-launchpad-search', hint_text: 'Search', can_focus: true,
            x_align: Clutter.ActorAlign.CENTER, y_align: Clutter.ActorAlign.START,
        });
        this.entry.set_primary_icon(new St.Icon({
            icon_name: 'edit-find-symbolic', style_class: 'nalamint-launchpad-search-icon',
        }));
        this.entry.clutter_text.connect('text-changed', () => this.onSearch());
        this.entry.clutter_text.connect('key-press-event', (a, event) => this.onKey(event));
        this.entry.clutter_text.connect('key-release-event', (a, event) => this.onKeyRelease(event));
        top.add_child(this.entry);
        this.content.add_child(top);

        // Pages slide inside a clipped viewport
        this.viewport = new Clutter.Actor({ clip_to_allocation: true, y: g.gridY, width: g.W, height: g.gridH });
        this.strip = new Clutter.Actor();
        this.results = new Clutter.Actor({ visible: false });
        this.viewport.add_child(this.strip);
        this.viewport.add_child(this.results);
        this.content.add_child(this.viewport);
        this.grid = new Grid(g.cols, g.rows, g.cellW, g.cellH, g.W, g.gridH);

        this.entries = this.loadEntries();
        this.actorOf = new Map();
        for (let entry of this.entries)
            this.addActor(entry);

        // Page dots
        let bottom = new St.Widget({ layout_manager: new Clutter.BinLayout(), width: g.W, y: g.dotsY });
        this.dots = new St.BoxLayout({ style_class: 'nalamint-launchpad-dots', x_align: Clutter.ActorAlign.CENTER });
        bottom.add_child(this.dots);
        this.content.add_child(bottom);

        this.noResults = new St.Label({ style_class: 'nalamint-launchpad-empty', text: 'No Results', visible: false });
        let middle = new St.Widget({ layout_manager: new Clutter.BinLayout(), width: g.W, height: g.H });
        this.noResults.x_align = Clutter.ActorAlign.CENTER;
        this.noResults.y_align = Clutter.ActorAlign.CENTER;
        middle.add_child(this.noResults);
        this.content.add_child(middle);

        // Open folder, then the icon being dragged, above everything else
        this.folderLayer = new Clutter.Actor({ width: g.W, height: g.H, visible: false });
        this.content.add_child(this.folderLayer);
        this.dragLayer = new Clutter.Actor({ width: g.W, height: g.H });
        this.content.add_child(this.dragLayer);

        actor.connect('button-press-event', (a, event) => this.onPress(event));
        actor.connect('motion-event', (a, event) => this.onMotion(event));
        actor.connect('button-release-event', (a, event) => this.onRelease(event));
        actor.connect('scroll-event', (a, event) => this.onScroll(event));
        actor.connect('key-press-event', (a, event) => this.onKey(event));
        actor.connect('key-release-event', (a, event) => this.onKeyRelease(event));

        Main.uiGroup.add_child(actor);
        this.page = 0;
        this.pageCount = 0;
        this.searchItems = [];
        this.selected = -1;
        this.folder = null;
        this.drag = null;
        this.press = null;
        this.relayout(false);
        this.dirty = false;
    }

    itemBox(width) {
        return new St.BoxLayout({
            vertical: true, width,
            x_align: Clutter.ActorAlign.CENTER, y_align: Clutter.ActorAlign.CENTER,
        });
    }

    itemLabel(text) {
        let label = new St.Label({ text, style_class: 'nalamint-launchpad-label', x_align: Clutter.ActorAlign.CENTER });
        label.clutter_text.ellipsize = Pango.EllipsizeMode.END;
        return label;
    }

    appIcon(app, size) {
        // Apps whose icon can't be found get a generic one instead of a gap
        let gicon = app.get_app_info().get_icon();
        let icon = gicon && Gtk.IconTheme.get_default().lookup_by_gicon(gicon, size, 0)
            ? app.create_icon_texture(size)
            : new St.Icon({ icon_name: 'application-x-executable', icon_size: size });
        icon.x_align = Clutter.ActorAlign.CENTER;
        return icon;
    }

    makeItem(app) {
        let g = this.geo;
        let item = new St.Widget({
            style_class: 'nalamint-launchpad-item', reactive: true, track_hover: true,
            layout_manager: new Clutter.BinLayout(), width: g.cellW - 12, height: g.cellH - 12,
        });
        let box = this.itemBox(g.cellW - 28);
        box.add_child(this.appIcon(app, g.iconSize));
        box.add_child(this.itemLabel(app.get_name()));
        item.add_child(box);
        item.set_pivot_point(0.5, 0.5);
        item._nalamintApp = app;
        return item;
    }

    // A folder looks like a translucent tile with up to nine small icons
    makeFolderItem(entry) {
        let g = this.geo;
        let item = new St.Widget({
            style_class: 'nalamint-launchpad-item', reactive: true, track_hover: true,
            layout_manager: new Clutter.BinLayout(), width: g.cellW - 12, height: g.cellH - 12,
        });
        let box = this.itemBox(g.cellW - 28);
        let tile = new St.Widget({
            style_class: 'nalamint-launchpad-folder-icon', width: g.iconSize, height: g.iconSize,
            x_align: Clutter.ActorAlign.CENTER,
        });
        let mini = Math.round(g.iconSize * 0.24);
        let gap = Math.round((g.iconSize - 3 * mini) / 4);
        entry.apps.slice(0, 9).forEach((id, i) => {
            let icon = this.appIcon(this.byId.get(id), mini);
            icon.set_position(gap + (i % 3) * (mini + gap), gap + Math.floor(i / 3) * (mini + gap));
            tile.add_child(icon);
        });
        box.add_child(tile);
        box.add_child(this.itemLabel(entry.name));
        item.add_child(box);
        item.set_pivot_point(0.5, 0.5);
        item._nalamintFolder = entry;
        return item;
    }

    addActor(entry) {
        let actor = entry.type === 'folder' ? this.makeFolderItem(entry) : this.makeItem(this.byId.get(entry.id));
        actor._nalamintEntry = entry;
        this.actorOf.set(entry, actor);
        this.strip.add_child(actor);
        return actor;
    }

    // Rebuild one item in place (folder contents or name changed)
    refreshActor(entry, old) {
        let pos = old ? old.get_position() : null;
        if (old) {
            this.actorOf.delete(old._nalamintEntry);
            old.destroy();
        }
        let actor = this.addActor(entry);
        if (pos)
            actor.set_position(...pos);
        return actor;
    }

    destroyActor() {
        this.cancelTimers();
        if (this.actor) {
            this.actor.destroy();
            this.actor = null;
        }
    }

    // Move every item (except the dragged one) to its slot
    relayout(animate) {
        this.entries.forEach((entry, i) => {
            let actor = this.actorOf.get(entry);
            if (!actor || (this.drag && this.drag.actor === actor))
                return;
            let [x, y] = this.grid.slot(i);
            actor.remove_transition('x');
            actor.remove_transition('y');
            if (animate)
                actor.ease({ x, y, duration: 180, mode: EASE });
            else
                actor.set_position(x, y);
        });
        let count = this.grid.pages(this.entries.length);
        if (count !== this.pageCount) {
            this.pageCount = count;
            this.dots.destroy_all_children();
            for (let p = 0; p < count; p++) {
                let dot = new St.Button({ style_class: 'nalamint-launchpad-dot', reactive: true });
                dot.connect('clicked', () => this.goToPage(p));
                this.dots.add_child(dot);
            }
        }
        this.dots.visible = this.pageCount > 1 && !this.searching();
        this.goToPage(Math.min(this.page, this.pageCount - 1), animate);
    }

    // ---- open / close ----

    toggle(monitorIndex) {
        this.isOpen ? this.close() : this.open(monitorIndex);
    }

    open(monitorIndex) {
        if (this.isOpen || Main.overview.visible || Main.expo.visible)
            return;
        let mon = Main.layoutManager.monitors[monitorIndex] || Main.layoutManager.primaryMonitor;
        let key = [mon.x, mon.y, mon.width, mon.height].join(',');
        if (this.dirty || !this.actor || key !== this.monitorKey || this.radius !== this.applet.blurRadius)
            this.build(mon);

        let actor = this.actor;
        actor.remove_all_transitions();
        this.content.remove_all_transitions();
        Main.uiGroup.set_child_above_sibling(actor, null);
        actor.show();
        if (!Main.pushModal(actor)) {
            actor.hide();
            return;
        }
        this.isOpen = true;
        this.press = null;
        this.applet.actor.add_style_pseudo_class('checked');
        this.entry.set_text('');
        this.onSearch();
        this.goToPage(0, false);
        global.stage.set_key_focus(this.entry.clutter_text);

        actor.opacity = 0;
        this.content.set_scale(ZOOM, ZOOM);
        actor.ease({ opacity: 255, duration: ANIM_MS, mode: EASE });
        this.content.ease({ scale_x: 1, scale_y: 1, duration: ANIM_MS, mode: EASE });
    }

    close(immediate) {
        if (!this.isOpen)
            return;
        if (this.drag)
            this.endDrag();
        if (this.folder)
            this.closeFolder(true);
        this.isOpen = false;
        this.applet.actor.remove_style_pseudo_class('checked');
        let actor = this.actor;
        Main.popModal(actor);
        if (immediate) {
            actor.hide();
            return;
        }
        actor.ease({
            opacity: 0, duration: ANIM_MS, mode: EASE,
            onComplete: () => {
                if (!this.isOpen)
                    actor.hide();
            },
        });
        this.content.ease({ scale_x: ZOOM, scale_y: ZOOM, duration: ANIM_MS, mode: EASE });
    }

    launch(app) {
        this.close();
        app.activate();
    }

    activateItem(item) {
        if (item._nalamintFolder)
            this.openFolder(item._nalamintFolder);
        else if (item._nalamintApp)
            this.launch(item._nalamintApp);
    }

    // ---- pages, search, selection ----

    searching() {
        return this.results.visible;
    }

    goToPage(p, animate = true) {
        p = clamp(p, 0, this.pageCount - 1);
        this.page = p;
        this.strip.remove_transition('translation-x');
        if (animate)
            this.strip.ease({ translation_x: -p * this.geo.W, duration: 260, mode: Clutter.AnimationMode.EASE_OUT_CUBIC });
        else
            this.strip.translation_x = -p * this.geo.W;
        this.dots.get_children().forEach((dot, i) => {
            if (i === p)
                dot.add_style_pseudo_class('checked');
            else
                dot.remove_style_pseudo_class('checked');
        });
    }

    // Page change by the user: a keyboard selection follows to the new page
    flip(step) {
        if (this.folder) {
            this.goToFolderPage(this.folderPage + step);
            return;
        }
        if (this.searching())
            return;
        this.goToPage(this.page + step);
        if (this.selected >= 0)
            this.select(this.page * this.grid.per);
    }

    onSearch() {
        let q = this.entry.get_text().trim().toLowerCase();
        this.searchItems.forEach(item => item.destroy());
        this.searchItems = [];
        let searching = q.length > 0;
        this.strip.visible = !searching;
        this.dots.visible = !searching && this.pageCount > 1;
        this.results.visible = searching;
        this.noResults.visible = false;
        this.select(-1);
        if (!searching)
            return;

        // Search covers every app, also those in folders and settings pages
        let found = this.apps()
            .map(app => [matchScore(app, q), app])
            .filter(([score]) => score >= 0)
            .sort((a, b) => a[0] - b[0] || a[1].get_name().localeCompare(b[1].get_name()))
            .slice(0, this.grid.per)
            .map(([, app]) => app);
        this.searchItems = found.map(app => this.makeItem(app));
        this.searchItems.forEach((item, i) => {
            item.set_position(...this.grid.slot(i));
            this.results.add_child(item);
        });
        this.noResults.visible = found.length === 0;
        this.select(found.length ? 0 : -1);
    }

    items() {
        if (this.folder)
            return this.folderEntries.map(e => this.folderActorOf.get(e));
        return this.searching() ? this.searchItems : this.entries.map(e => this.actorOf.get(e));
    }

    select(i) {
        let items = this.items();
        for (let item of items)
            item.remove_style_pseudo_class('selected');
        this.selected = i;
        if (i < 0 || i >= items.length)
            return;
        items[i].add_style_pseudo_class('selected');
        if (this.folder) {
            let page = Math.floor(i / this.folderGrid.per);
            if (page !== this.folderPage)
                this.goToFolderPage(page);
        } else if (!this.searching()) {
            let page = Math.floor(i / this.grid.per);
            if (page !== this.page)
                this.goToPage(page);
        }
    }

    move(delta) {
        let n = this.items().length;
        if (!n)
            return;
        if (this.selected < 0) {
            // First arrow press picks the first icon on the current page
            let first = this.folder ? this.folderPage * this.folderGrid.per
                : this.searching() ? 0 : this.page * this.grid.per;
            this.select(Math.min(n - 1, first));
            return;
        }
        this.select(clamp(this.selected + delta, 0, n - 1));
    }

    // ---- keyboard ----

    onKey(event) {
        let sym = event.get_key_symbol();
        let enter = sym === Clutter.KEY_Return || sym === Clutter.KEY_KP_Enter;
        if (this.drag) {
            if (sym === Clutter.KEY_Escape)
                this.cancelDrag();
            return Clutter.EVENT_STOP;
        }
        if (this.folder && this.renaming) {
            if (sym === Clutter.KEY_Escape || enter) {
                this.finishRename(sym !== Clutter.KEY_Escape);
                return Clutter.EVENT_STOP;
            }
            return Clutter.EVENT_PROPAGATE;      // typing the folder name
        }
        let cols = this.folder ? this.folderGrid.cols : this.grid.cols;
        switch (sym) {
        case Clutter.KEY_Escape:
            if (this.folder)
                this.closeFolder();
            else if (this.entry.get_text())
                this.entry.set_text('');
            else
                this.close();
            return Clutter.EVENT_STOP;
        case Clutter.KEY_Return:
        case Clutter.KEY_KP_Enter: {
            let item = this.items()[this.selected];
            if (item)
                this.activateItem(item);
            return Clutter.EVENT_STOP;
        }
        case Clutter.KEY_Left:
            this.move(-1);
            return Clutter.EVENT_STOP;
        case Clutter.KEY_Right:
            this.move(1);
            return Clutter.EVENT_STOP;
        case Clutter.KEY_Up:
            this.move(-cols);
            return Clutter.EVENT_STOP;
        case Clutter.KEY_Down:
            this.move(cols);
            return Clutter.EVENT_STOP;
        case Clutter.KEY_Page_Up:
            this.flip(-1);
            return Clutter.EVENT_STOP;
        case Clutter.KEY_Page_Down:
            this.flip(1);
            return Clutter.EVENT_STOP;
        }
        if (this.folder)
            return Clutter.EVENT_STOP;
        if (!this.entry.clutter_text.has_key_focus()) {
            // Typing anywhere goes to the search field
            global.stage.set_key_focus(this.entry.clutter_text);
            return this.entry.clutter_text.event(event, false);
        }
        return Clutter.EVENT_PROPAGATE;
    }

    // The modal grab keeps the Super binding from firing, so Super closes here.
    // On release: closing on press would let the release reach the window
    // manager and open Launchpad again.
    onKeyRelease(event) {
        let sym = event.get_key_symbol();
        if (sym === Clutter.KEY_Super_L || sym === Clutter.KEY_Super_R) {
            this.close();
            return Clutter.EVENT_STOP;
        }
        return Clutter.EVENT_PROPAGATE;
    }

    onScroll(event) {
        if (this.searching() || this.drag)
            return Clutter.EVENT_STOP;
        let dir = event.get_scroll_direction();
        let step = 0;
        if (dir === Clutter.ScrollDirection.SMOOTH) {
            let [dx, dy] = event.get_scroll_delta();
            this.scrollAcc = (this.scrollAcc || 0) + (Math.abs(dx) > Math.abs(dy) ? dx : dy);
            if (Math.abs(this.scrollAcc) >= 1) {
                step = Math.sign(this.scrollAcc);
                this.scrollAcc = 0;
            }
        } else if (dir === Clutter.ScrollDirection.DOWN || dir === Clutter.ScrollDirection.RIGHT) {
            step = 1;
        } else if (dir === Clutter.ScrollDirection.UP || dir === Clutter.ScrollDirection.LEFT) {
            step = -1;
        }
        let now = GLib.get_monotonic_time();
        if (step && now - (this.lastFlip || 0) > 250000) {   // one page per gesture
            this.lastFlip = now;
            this.flip(step);
        }
        return Clutter.EVENT_STOP;
    }

    // ---- pointer: click, drag, drop ----

    // Walks up from an event source; stops at the overlay
    find(source, test) {
        for (let a = source; a && a !== this.actor; a = a.get_parent())
            if (test(a))
                return a;
        return null;
    }

    itemAt(source) {
        return this.find(source, a => a._nalamintApp || a._nalamintFolder);
    }

    inFolderPanel(source) {
        return !!this.folder && !!this.find(source, a => a === this.folderPanel);
    }

    // Only a click that started on the overlay counts: the dock icon opens
    // Launchpad on press, and that click's release lands here.
    onPress(event) {
        if (event.get_button() !== 1)
            return Clutter.EVENT_PROPAGATE;
        let source = event.get_source();
        let [x, y] = event.get_coords();
        let item = this.itemAt(source);
        this.press = { item, x, y, inPanel: this.inFolderPanel(source) };
        if (item)
            item.add_style_pseudo_class('active');
        return Clutter.EVENT_STOP;
    }

    onMotion(event) {
        let [x, y] = event.get_coords();
        if (this.drag) {
            this.dragMove(x, y);
            return Clutter.EVENT_STOP;
        }
        let p = this.press;
        if (p && p.item && !this.searching() && Math.hypot(x - p.x, y - p.y) > DRAG_START &&
            (event.get_state() & Clutter.ModifierType.BUTTON1_MASK)) {
            p.item.remove_style_pseudo_class('active');
            this.startDrag(p.item, x, y);
            return Clutter.EVENT_STOP;
        }
        return Clutter.EVENT_PROPAGATE;
    }

    onRelease(event) {
        if (event.get_button() !== 1)
            return Clutter.EVENT_PROPAGATE;
        let press = this.press;
        this.press = null;
        if (press && press.item)
            press.item.remove_style_pseudo_class('active');
        if (this.drag) {
            this.endDrag();
            return Clutter.EVENT_STOP;
        }
        if (!press)
            return Clutter.EVENT_PROPAGATE;
        let source = event.get_source();
        if (press.item) {
            if (this.itemAt(source) === press.item)
                this.activateItem(press.item);
            return Clutter.EVENT_STOP;
        }
        if (this.folder) {
            if (this.find(source, a => a === this.folderTitle))
                this.startRename();
            else if (!press.inPanel && !this.inFolderPanel(source))
                this.closeFolder();
            return Clutter.EVENT_STOP;
        }
        // The search field and the dots handle their own clicks; empty space closes
        if (this.find(source, a => a === this.entry || a === this.dots))
            return Clutter.EVENT_PROPAGATE;
        this.close();
        return Clutter.EVENT_STOP;
    }

    // What a drag works on: the main grid, or the open folder's grid
    context() {
        if (this.folder) {
            return {
                list: this.folderEntries, grid: this.folderGrid, strip: this.folderStrip,
                viewport: this.folderViewport, actorOf: this.folderActorOf, folders: false,
            };
        }
        return {
            list: this.entries, grid: this.grid, strip: this.strip,
            viewport: this.viewport, actorOf: this.actorOf, folders: true,
        };
    }

    startDrag(item, x, y) {
        let ctx = this.context();
        let entry = item._nalamintEntry;
        // Lift the icon out of its page into the drag layer, where it follows the pointer
        let [sx, sy] = item.get_transformed_position();
        let [, lx, ly] = this.dragLayer.transform_stage_point(sx, sy);
        let [, px, py] = this.dragLayer.transform_stage_point(x, y);
        item.remove_all_transitions();
        item.get_parent().remove_child(item);
        this.dragLayer.add_child(item);
        item.set_position(lx, ly);
        item.reactive = false;
        item.ease({ scale_x: 1.1, scale_y: 1.1, opacity: 220, duration: 120, mode: EASE });
        this.select(-1);
        this.drag = {
            ctx, entry, actor: item, offX: px - lx, offY: py - ly,
            original: ctx.list.slice(), pendingIndex: -1, candidate: null, into: null, edge: 0,
            x, y,
        };
    }

    dragMove(x, y) {
        let d = this.drag, ctx = d.ctx;
        d.x = x;
        d.y = y;
        let [, px, py] = this.dragLayer.transform_stage_point(x, y);
        d.actor.set_position(px - d.offX, py - d.offY);

        // Out of an open folder: the app leaves it and the drag goes on in the main grid
        if (this.folder) {
            let [px1, py1] = this.folderPanel.get_transformed_position();
            let [pw, ph] = this.folderPanel.get_transformed_size();
            if (x < px1 || y < py1 || x > px1 + pw || y > py1 + ph) {
                this.dragOutOfFolder();
                return;
            }
        }

        // Near the left/right edge: flip the page after a moment
        let [, vx, vy] = ctx.viewport.transform_stage_point(x, y);
        let edge = vx < EDGE_PX ? -1 : vx > ctx.viewport.width - EDGE_PX ? 1 : 0;
        if (edge !== d.edge) {
            d.edge = edge;
            this.setTimer('edge', edge ? EDGE_MS : 0, () => {
                this.flip(d.edge);
                return GLib.SOURCE_CONTINUE;         // keep flipping while held there
            });
        }

        let [, sx, sy] = ctx.strip.transform_stage_point(x, y);
        // Like the Mac: an icon's center makes a folder; its left or right side
        // moves the dragged icon before or after it
        let cell = ctx.grid.cellAt(sx, sy);
        let target = cell.index < ctx.list.length ? ctx.list[cell.index] : null;
        let dx = sx - cell.cx, dy = sy - (cell.cy - 15), r = this.geo.iconSize;
        let center = target && target !== d.entry && Math.abs(dx) < r * 0.32 && Math.abs(dy) < r * 0.45;
        if (center && ctx.folders && d.entry.type === 'app') {
            this.setTimer('reorder', 0);
            d.pendingIndex = -1;
            if (d.candidate !== target) {
                this.clearInto();
                d.candidate = target;
                this.setTimer('into', FOLDER_MS, () => {
                    d.into = target;
                    let actor = ctx.actorOf.get(target);
                    if (actor)
                        actor.add_style_pseudo_class('drop');
                    return GLib.SOURCE_REMOVE;
                });
            }
            return;
        }
        this.clearInto();
        let from = ctx.list.indexOf(d.entry);
        let before = target ? cell.index + (dx > 0 ? 1 : 0) : ctx.list.length;
        let index = clamp(before > from ? before - 1 : before, 0, ctx.list.length - 1);
        if (index === from) {
            this.setTimer('reorder', 0);
            d.pendingIndex = -1;
            return;
        }
        if (index !== d.pendingIndex) {
            d.pendingIndex = index;
            this.setTimer('reorder', REORDER_MS, () => {
                this.moveEntry(ctx, d.entry, index);
                d.pendingIndex = -1;
                return GLib.SOURCE_REMOVE;
            });
        }
    }

    moveEntry(ctx, entry, index) {
        let from = ctx.list.indexOf(entry);
        if (from < 0 || from === index)
            return;
        ctx.list.splice(from, 1);
        ctx.list.splice(index, 0, entry);
        this.relayoutContext(ctx, true);
    }

    relayoutContext(ctx, animate) {
        if (ctx.list === this.entries)
            this.relayout(animate);
        else
            this.relayoutFolder(animate);
    }

    clearInto() {
        let d = this.drag;
        this.setTimer('into', 0);
        if (d && d.candidate) {
            let actor = d.ctx.actorOf.get(d.candidate);
            if (actor)
                actor.remove_style_pseudo_class('drop');
        }
        if (d) {
            d.candidate = null;
            d.into = null;
        }
    }

    endDrag() {
        let d = this.drag;
        let ctx = d.ctx;
        this.setTimer('edge', 0);
        this.setTimer('reorder', 0);
        let into = d.into;
        this.clearInto();
        if (!into && d.pendingIndex >= 0)
            this.moveEntry(ctx, d.entry, d.pendingIndex);
        this.drag = null;

        if (into) {
            this.dropInto(d.entry, d.actor, into);
        } else {
            // Back into the page, gliding from where it was dropped to its slot
            let [sx, sy] = d.actor.get_transformed_position();
            this.dragLayer.remove_child(d.actor);
            ctx.strip.add_child(d.actor);
            let [, lx, ly] = ctx.strip.transform_stage_point(sx, sy);
            d.actor.set_position(lx, ly);
            d.actor.reactive = true;
            d.actor.ease({ scale_x: 1, scale_y: 1, opacity: 255, duration: 150, mode: EASE });
            this.relayoutContext(ctx, true);
            let [x, y] = ctx.grid.slot(ctx.list.indexOf(d.entry));
            d.actor.ease({ x, y, duration: 180, mode: EASE });
        }
        this.save();
    }

    cancelDrag() {
        let d = this.drag;
        d.ctx.list.splice(0, d.ctx.list.length, ...d.original);
        d.pendingIndex = -1;
        d.into = null;
        d.candidate = null;
        this.endDrag();
    }

    // Dropped onto an icon: a new folder with both, or into an existing folder
    dropInto(entry, actor, target) {
        actor.destroy();
        this.actorOf.delete(entry);
        this.entries.splice(this.entries.indexOf(entry), 1);
        let i = this.entries.indexOf(target);
        let old = this.actorOf.get(target);
        let folder = target;
        if (target.type === 'folder') {
            target.apps.push(entry.id);
        } else {
            folder = { type: 'folder', name: this.folderName([target.id, entry.id]), apps: [target.id, entry.id] };
            this.entries[i] = folder;
        }
        this.refreshActor(folder, old);
        this.relayout(true);
    }

    dragOutOfFolder() {
        let d = this.drag;
        let folder = this.folder;
        let app = this.byId.get(d.entry.id);
        // Leave the folder (its own drag ends here)
        this.setTimer('edge', 0);
        this.setTimer('reorder', 0);
        this.drag = null;
        d.actor.destroy();
        this.folderEntries.splice(this.folderEntries.indexOf(d.entry), 1);
        // Closing may turn a folder with one app left back into that app, in place
        let at = this.entries.indexOf(folder) + 1;
        this.closeFolder(true);

        // The app goes right after the folder, and the drag continues there
        let entry = { type: 'app', id: app.get_id() };
        this.entries.splice(at, 0, entry);
        let item = this.addActor(entry);
        this.relayout(true);
        item.set_position(...this.grid.slot(at));
        this.startDrag(item, d.x, d.y);
        // Center the icon under the pointer
        this.drag.offX = (this.geo.cellW - 12) / 2;
        this.drag.offY = (this.geo.cellH - 12) / 2;
        this.dragMove(d.x, d.y);
    }

    // A folder with one app left becomes that app; an empty one goes away
    unwrapSmallFolder(folder) {
        let i = this.entries.indexOf(folder);
        if (i < 0 || folder.apps.length > 1) {
            if (i >= 0)
                this.refreshActor(folder, this.actorOf.get(folder));
            return;
        }
        let old = this.actorOf.get(folder);
        if (folder.apps.length === 1) {
            let entry = { type: 'app', id: folder.apps[0] };
            this.entries[i] = entry;
            this.actorOf.delete(folder);
            let actor = this.addActor(entry);
            if (old)
                actor.set_position(...old.get_position());
        } else {
            this.entries.splice(i, 1);
            this.actorOf.delete(folder);
        }
        if (old)
            old.destroy();
    }

    // ---- folders ----

    openFolder(folder) {
        let g = this.geo;
        this.select(-1);
        this.folder = folder;
        this.folderEntries = folder.apps.map(id => ({ type: 'app', id }));
        this.folderActorOf = new Map();
        this.folderPage = 0;

        let n = this.folderEntries.length;
        let cols = Math.min(5, Math.max(3, n));
        let rows = clamp(Math.ceil(n / cols), 1, 3);
        let gridW = cols * g.cellW, gridH = rows * g.cellH;
        let pad = 24, titleH = 64, pages = Math.ceil(n / (cols * rows)), dotsH = pages > 1 ? 36 : 0;
        let panelW = gridW + 2 * pad, panelH = titleH + gridH + dotsH + pad;

        this.folderLayer.destroy_all_children();
        let backdrop = new St.Widget({ style_class: 'nalamint-launchpad-folder-backdrop', width: g.W, height: g.H });
        this.folderLayer.add_child(backdrop);
        let panel = this.folderPanel = new St.Widget({
            style_class: 'nalamint-launchpad-folder', reactive: true, width: panelW, height: panelH,
            x: Math.round((g.W - panelW) / 2), y: Math.round((g.H - panelH) / 2),
        });
        panel.set_pivot_point(0.5, 0.5);
        this.folderLayer.add_child(panel);

        // Name: a label; click it to rename
        let titleBox = new St.Widget({ layout_manager: new Clutter.BinLayout(), width: panelW, height: titleH });
        this.folderTitle = new St.Label({
            style_class: 'nalamint-launchpad-folder-title', text: folder.name, reactive: true,
            x_align: Clutter.ActorAlign.CENTER, y_align: Clutter.ActorAlign.CENTER,
        });
        this.folderTitleEntry = new St.Entry({
            style_class: 'nalamint-launchpad-folder-title-entry', text: folder.name, visible: false,
            x_align: Clutter.ActorAlign.CENTER, y_align: Clutter.ActorAlign.CENTER,
        });
        this.folderTitleEntry.clutter_text.connect('key-press-event', (a, event) => this.onKey(event));
        this.folderTitleEntry.clutter_text.connect('key-focus-out', () => {
            if (this.renaming)
                this.finishRename(true);
        });
        titleBox.add_child(this.folderTitle);
        titleBox.add_child(this.folderTitleEntry);
        panel.add_child(titleBox);
        this.renaming = false;

        this.folderViewport = new Clutter.Actor({ clip_to_allocation: true, x: pad, y: titleH, width: gridW, height: gridH });
        this.folderStrip = new Clutter.Actor();
        this.folderViewport.add_child(this.folderStrip);
        panel.add_child(this.folderViewport);
        this.folderGrid = new Grid(cols, rows, g.cellW, g.cellH, gridW, gridH);
        for (let entry of this.folderEntries) {
            let item = this.makeItem(this.byId.get(entry.id));
            item._nalamintEntry = entry;
            this.folderActorOf.set(entry, item);
            this.folderStrip.add_child(item);
        }
        this.folderDots = new St.BoxLayout({ style_class: 'nalamint-launchpad-dots', x_align: Clutter.ActorAlign.CENTER });
        let dotsBox = new St.Widget({ layout_manager: new Clutter.BinLayout(), width: panelW, y: titleH + gridH + 8 });
        dotsBox.add_child(this.folderDots);
        panel.add_child(dotsBox);
        this.folderPageCount = 0;
        this.relayoutFolder(false);

        this.folderLayer.show();
        global.stage.set_key_focus(this.actor);
        this.folderLayer.opacity = 0;
        panel.set_scale(0.9, 0.9);
        this.folderLayer.ease({ opacity: 255, duration: 180, mode: EASE });
        panel.ease({ scale_x: 1, scale_y: 1, duration: 180, mode: EASE });
        // The main grid steps back so only the folder's icons are seen
        for (let a of [this.viewport, this.dots])
            a.ease({ opacity: 0, duration: 180, mode: EASE });
    }

    relayoutFolder(animate) {
        this.folderEntries.forEach((entry, i) => {
            let actor = this.folderActorOf.get(entry);
            if (!actor || (this.drag && this.drag.actor === actor))
                return;
            let [x, y] = this.folderGrid.slot(i);
            if (animate)
                actor.ease({ x, y, duration: 180, mode: EASE });
            else
                actor.set_position(x, y);
        });
        let count = this.folderGrid.pages(this.folderEntries.length);
        if (count !== this.folderPageCount) {
            this.folderPageCount = count;
            this.folderDots.destroy_all_children();
            for (let p = 0; p < count; p++) {
                let dot = new St.Button({ style_class: 'nalamint-launchpad-dot', reactive: true });
                dot.connect('clicked', () => this.goToFolderPage(p));
                this.folderDots.add_child(dot);
            }
            this.folderDots.visible = count > 1;
        }
        this.goToFolderPage(Math.min(this.folderPage, count - 1), animate);
    }

    goToFolderPage(p, animate = true) {
        p = clamp(p, 0, this.folderPageCount - 1);
        this.folderPage = p;
        let x = -p * this.folderGrid.pageW;
        if (animate)
            this.folderStrip.ease({ translation_x: x, duration: 240, mode: Clutter.AnimationMode.EASE_OUT_CUBIC });
        else
            this.folderStrip.translation_x = x;
        this.folderDots.get_children().forEach((dot, i) => {
            if (i === p)
                dot.add_style_pseudo_class('checked');
            else
                dot.remove_style_pseudo_class('checked');
        });
    }

    closeFolder(immediate) {
        let folder = this.folder;
        if (!folder)
            return;
        if (this.renaming)
            this.finishRename(true);
        this.select(-1);
        folder.apps = this.folderEntries.map(e => e.id);
        this.folder = null;
        this.unwrapSmallFolder(folder);
        this.relayout(!immediate);
        this.save();

        let layer = this.folderLayer;
        for (let a of [this.viewport, this.dots]) {
            a.remove_transition('opacity');
            if (immediate)
                a.opacity = 255;
            else
                a.ease({ opacity: 255, duration: 180, mode: EASE });
        }
        if (immediate) {
            layer.hide();
            layer.destroy_all_children();
        } else {
            layer.ease({
                opacity: 0, duration: 180, mode: EASE,
                onComplete: () => {
                    if (!this.folder) {
                        layer.hide();
                        layer.destroy_all_children();
                    }
                },
            });
        }
        global.stage.set_key_focus(this.entry.clutter_text);
    }

    startRename() {
        this.renaming = true;
        this.folderTitle.hide();
        let entry = this.folderTitleEntry;
        entry.set_text(this.folder.name);
        entry.show();
        global.stage.set_key_focus(entry.clutter_text);
        entry.clutter_text.set_selection(0, -1);
    }

    finishRename(keep) {
        if (!this.renaming)
            return;
        this.renaming = false;
        let name = this.folderTitleEntry.get_text().trim();
        if (keep && name)
            this.folder.name = name;
        this.folderTitle.set_text(this.folder.name);
        this.folderTitleEntry.hide();
        this.folderTitle.show();
        global.stage.set_key_focus(this.actor);
        this.save();
    }

    // ---- timers ----

    // Replaces the named timer; ms = 0 just cancels it
    setTimer(name, ms, callback) {
        if (this.timers[name]) {
            GLib.source_remove(this.timers[name]);
            delete this.timers[name];
        }
        if (!ms)
            return;
        this.timers[name] = GLib.timeout_add(GLib.PRIORITY_DEFAULT, ms, () => {
            let again = callback();
            if (again !== GLib.SOURCE_CONTINUE)
                delete this.timers[name];
            return again;
        });
    }

    cancelTimers() {
        for (let name of Object.keys(this.timers))
            this.setTimer(name, 0);
    }

    destroy() {
        this.close(true);
        this.cancelTimers();
        for (let [obj, id] of this.signals)
            obj.disconnect(id);
        this.signals = [];
        this.destroyActor();
    }
}

class LaunchpadApplet extends Applet.IconApplet {
    constructor(metadata, orientation, panelHeight, instanceId) {
        super(orientation, panelHeight, instanceId);
        this.setAllowedLayout(Applet.AllowedLayout.BOTH);
        this.set_applet_tooltip('Launchpad');
        this.settings = new Settings.AppletSettings(this, metadata.uuid, instanceId);
        this.settings.bind('menu-icon', 'menuIcon', () => this.updateIcon());
        this.settings.bind('overlay-key', 'overlayKey', () => this.updateKeybinding());
        this.settings.bind('blur-radius', 'blurRadius');
        this.settings.bind('hide-settings-pages', 'hideSettingsPages', () => {
            if (this.launchpad)
                this.launchpad.dirty = true;
        });
        this.launchpad = new Launchpad(this);
        this.updateIcon();
        this.updateKeybinding();

        let reset = new PopupMenu.PopupMenuItem('Reset Launchpad Layout');
        reset.connect('activate', () => {
            this.settings.setValue('layout', {});
            this.launchpad.dirty = true;
        });
        this._applet_context_menu.addMenuItem(reset);
    }

    updateIcon() {
        let icon = this.menuIcon || 'nalamint-launchpad';
        if (GLib.path_is_absolute(icon))
            this.set_applet_icon_path(icon);
        else if (icon.endsWith('-symbolic'))
            this.set_applet_icon_symbolic_name(icon);
        else
            this.set_applet_icon_name(icon);
    }

    updateKeybinding() {
        Main.keybindingManager.addXletHotKey(this, 'overlay-key', this.overlayKey, () => {
            // The pointer's monitor, like the macOS Launchpad gesture
            this.launchpad.toggle(Main.layoutManager.currentMonitor.index);
        });
    }

    on_applet_clicked() {
        this.launchpad.toggle(this.panel.monitorIndex);
    }

    on_applet_removed_from_panel() {
        Main.keybindingManager.removeXletHotKey(this, 'overlay-key');
        this.settings.finalize();
        this.launchpad.destroy();
    }
}

function main(metadata, orientation, panelHeight, instanceId) {
    return new LaunchpadApplet(metadata, orientation, panelHeight, instanceId);
}
