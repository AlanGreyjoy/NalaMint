// NalaMint Menu Bar — frosted, wallpaper-aware panels.
//
// 1. Blur (and the dock plate, see PanelBackdrop): puts a blurred copy of the wallpaper under each panel — or, for a
//    bottom panel drawn as a dock, under just the rounded dock bar (its center
//    zone). The copy is a Clutter.Clone of the desktop background, cropped to
//    the target plus a margin (kept inside the monitor so the blur never pulls
//    in empty space), blurred by two Gaussian shader passes, and clipped back
//    to the target with its CSS corner radius. It is registered as Cinnamon
//    "chrome" so it hides with the panel in fullscreen.
// 2. Adaptive text: measures the wallpaper under each panel from the image
//    file and adds the `nalamint-on-light` style class to panels over bright
//    wallpaper; the NalaMint desktop theme turns their text and icons dark.

const Clutter = imports.gi.Clutter;
const GdkPixbuf = imports.gi.GdkPixbuf;
const Gio = imports.gi.Gio;
const GLib = imports.gi.GLib;
const GObject = imports.gi.GObject;
const Main = imports.ui.main;
const Settings = imports.ui.settings;
const St = imports.gi.St;

const LIGHT_CLASS = 'nalamint-on-light';
const LOG_PREFIX = '[nalamint-menubar]';

const BLUR_SHADER = `
uniform sampler2D tex;
uniform float w;
uniform float h;
uniform float radius;
uniform float dirx;
uniform float diry;
uniform float mx1;
uniform float my1;
uniform float mx2;
uniform float my2;
uniform float mr;
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
  // Rounded mask (dock bar); mr = 0 means a plain rectangle
  vec2 p = uv * vec2(w, h);
  vec2 c = clamp(p, vec2(mx1 + mr, my1 + mr), vec2(mx2 - mr, my2 - mr));
  float cover = mr > 0.5 ? clamp(mr - distance(p, c) + 0.5, 0.0, 1.0) : 1.0;
  cogl_color_out = (sum / total) * cogl_color_in * cover;
}
`;

// Clutter treats integral JS numbers as ints; these uniforms are floats.
function asFloat(v) {
    return v + 0.00001;
}

function blurEffect(dirX, dirY) {
    let effect = new Clutter.ShaderEffect({ shader_type: Clutter.ShaderType.FRAGMENT_SHADER });
    effect.set_shader_source(BLUR_SHADER);
    effect.set_uniform_value('tex', 0);
    effect.set_uniform_value('dirx', asFloat(dirX));
    effect.set_uniform_value('diry', asFloat(dirY));
    effect.set_uniform_value('mr', asFloat(0));
    return effect;
}

const DOCK_CLASS = 'nalamint-dock';

function isDock(panel) {
    return panel.actor.has_style_class_name('panel-bottom') && !!panel._centerBox;
}

// Layers drawn just below one panel: a blurred wallpaper copy (if blur is on)
// and, for the dock, a themed plate (.nalamint-dock-plate). The window list
// forces its items to the full panel height, so the dock bar cannot be the
// panel's own background; the plate is inset from the panel edges by the
// -nalamint-inset-top/-bottom and -nalamint-outset-x lengths in the theme.
class PanelBackdrop {
    constructor(panel, blurRadius, onDestroyed) {
        this.panel = panel;
        this.onDestroyed = onDestroyed;
        this.radius = blurRadius;              // 0 = no blur
        this.layers = [];
        this.bindings = [];
        let actor = panel.actor;
        this.center = isDock(panel) ? panel._centerBox : null;

        if (blurRadius > 0) {
            this.outer = new Clutter.Actor({ name: 'nalamint-panel-blur', clip_to_allocation: true, reactive: false });
            this.horiz = new Clutter.Actor({ clip_to_allocation: true });
            this.vert = new Clutter.Actor({ clip_to_allocation: true });
            this.clone = new Clutter.Clone({ source: global.background_actor });
            this.vert.add_child(this.clone);
            this.horiz.add_child(this.vert);
            this.outer.add_child(this.horiz);
            this.hEffect = blurEffect(1, 0);
            this.vEffect = blurEffect(0, 1);
            this.horiz.add_effect(this.hEffect);
            this.vert.add_effect(this.vEffect);
            this.addLayer(this.outer);
        }
        if (this.center) {
            this.plate = new St.Widget({ style_class: 'nalamint-dock-plate', reactive: false });
            this.addLayer(this.plate);            // above the blur, below the panel
            this.styleId = this.plate.connect('style-changed', () => this.sync());
            actor.add_style_class_name(DOCK_CLASS);
        }

        this.allocId = actor.connect('notify::allocation', () => this.sync());
        this.centerAllocId = this.center
            ? this.center.connect('notify::allocation', () => this.sync()) : 0;
        this.destroyId = actor.connect('destroy', () => {
            this.allocId = this.destroyId = this.centerAllocId = 0;
            this.destroy();
            onDestroyed(this);
        });
        this.sync();
        // A freshly created panel may not be laid out yet
        GLib.idle_add(GLib.PRIORITY_LOW, () => {
            this.sync();
            return GLib.SOURCE_REMOVE;
        });
    }

    addLayer(layer) {
        let actor = this.panel.actor;
        actor.get_parent().insert_child_below(layer, actor);
        Main.layoutManager.trackChrome(layer, {
            visibleInFullscreen: false, affectsInputRegion: false, affectsStruts: false,
        });
        for (let prop of ['visible', 'opacity', 'translation-x', 'translation-y'])
            this.bindings.push(actor.bind_property(prop, layer, prop, GObject.BindingFlags.SYNC_CREATE));
        this.layers.push(layer);
    }

    setRadius(radius) {
        this.radius = radius;
        this.sync();
    }

    sync() {
        if (this.destroyed)
            return;
        try {
            if (!this.panel.actor.get_stage())
                throw new Error('panel left the stage');
            this._sync();
        } catch (e) {
            // The panel is being torn down (its zones go first): drop out and
            // let the manager rebuild for whatever panel replaces it.
            this.destroy();
            this.onDestroyed(this);
        }
    }

    _sync() {
        let a = this.panel.actor;
        let mon = Main.layoutManager.monitors[this.panel.monitorIndex];
        if (!mon || !a.get_stage() || a.width < 1 || a.height < 1)
            return;
        if (this.center && !this.center.get_stage())
            return;

        let x = a.x, y = a.y, w = a.width, h = a.height, r = 0;
        if (this.plate) {
            let node = this.plate.get_theme_node();
            let top = node.get_length('-nalamint-inset-top');
            let bottom = node.get_length('-nalamint-inset-bottom');
            let side = node.get_length('-nalamint-outset-x');
            x = a.x + this.center.x - side;
            w = this.center.width + 2 * side;
            y = a.y + top;
            h = Math.max(1, a.height - top - bottom);
            r = Math.min(node.get_border_radius(St.Corner.TOPLEFT), h / 2);
            this.plate.set_position(x, y);
            this.plate.set_size(w, h);
            this.plate.visible = this.center.width > 0 && a.visible;
        }
        if (!this.outer)
            return;

        this.outer.set_position(x, y);
        this.outer.set_size(w, h);
        // Blur source: target + margin, but never outside the monitor
        let m = Math.ceil(this.radius);
        let x1 = Math.max(x - m, mon.x), y1 = Math.max(y - m, mon.y);
        let x2 = Math.min(x + w + m, mon.x + mon.width), y2 = Math.min(y + h + m, mon.y + mon.height);
        let W = Math.max(1, x2 - x1), H = Math.max(1, y2 - y1);
        this.horiz.set_position(x1 - x, y1 - y);
        this.horiz.set_size(W, H);
        this.vert.set_size(W, H);
        this.clone.set_position(-x1, -y1);
        for (let effect of [this.hEffect, this.vEffect]) {
            effect.set_uniform_value('w', asFloat(W));
            effect.set_uniform_value('h', asFloat(H));
            effect.set_uniform_value('radius', asFloat(this.radius));
        }
        // Rounded mask in the final (horizontal) pass, in its texture's pixels
        this.hEffect.set_uniform_value('mx1', asFloat(x - x1));
        this.hEffect.set_uniform_value('my1', asFloat(y - y1));
        this.hEffect.set_uniform_value('mx2', asFloat(x - x1 + w));
        this.hEffect.set_uniform_value('my2', asFloat(y - y1 + h));
        this.hEffect.set_uniform_value('mr', asFloat(r));
    }

    destroy() {
        if (this.destroyed)
            return;
        this.destroyed = true;
        // Layers first: everything below may touch actors Cinnamon already destroyed
        for (let layer of this.layers)
            layer.destroy();
        this.layers = [];
        this.outer = this.plate = null;
        let quietly = f => { try { f(); } catch (e) { /* already gone */ } };
        for (let b of this.bindings)
            quietly(() => b.unbind());
        this.bindings = [];
        let actor = this.panel.actor;
        if (this.allocId)
            quietly(() => actor.disconnect(this.allocId));
        if (this.centerAllocId)
            quietly(() => this.center.disconnect(this.centerAllocId));
        if (this.destroyId)
            quietly(() => actor.disconnect(this.destroyId));
        quietly(() => actor.remove_style_class_name(DOCK_CLASS));
        this.allocId = this.destroyId = this.centerAllocId = 0;
    }
}

// ---------- wallpaper brightness ----------

function parseColor(str) {
    let hex = (str || '').replace('#', '');
    if (hex.length === 12)   // 16 bits per channel, as gsettings stores it
        return [0, 4, 8].map(i => parseInt(hex.substr(i, 4), 16) / 65535);
    if (hex.length === 6)
        return [0, 2, 4].map(i => parseInt(hex.substr(i, 2), 16) / 255);
    return [0, 0, 0];
}

function luma(r, g, b) {
    return 0.299 * r + 0.587 * g + 0.114 * b;
}

class WallpaperSampler {
    constructor() {
        this.key = null;
        this.pix = null;
    }

    // Average brightness (0..1) of the wallpaper under `rect` (stage coords)
    measure(bg, rect, monitor, screen) {
        let uri = bg.get_string('picture-uri');
        let options = bg.get_string('picture-options');
        let fallback = luma(...parseColor(bg.get_string('primary-color')));
        if (!uri || options === 'none')
            return fallback;
        let path = Gio.File.new_for_uri(uri).get_path();
        if (!path)
            return fallback;

        let key = uri;
        if (this.key !== key) {
            try {
                let [, origW] = GdkPixbuf.Pixbuf.get_file_info(path);
                this.pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, 1600, -1, true);
                this.origW = origW;
                this.bytes = this.pix.get_pixels();
                this.key = key;
            } catch (e) {
                global.logError(`${LOG_PREFIX} could not read wallpaper ${path}: ${e.message}`);
                this.key = null;
                return fallback;
            }
        }
        let pix = this.pix;
        let iw = pix.get_width(), ih = pix.get_height();
        let k = iw / this.origW;                  // loaded pixels per original pixel
        let area = options === 'spanned' ? screen : monitor;

        // screen = area.x + ox + image * s
        let sx, sy, ox = 0, oy = 0, tile = false;
        switch (options) {
            case 'stretched':
                sx = area.width / iw; sy = area.height / ih;
                break;
            case 'scaled':
                sx = sy = Math.min(area.width / iw, area.height / ih);
                break;
            case 'centered':
                sx = sy = 1 / k;
                break;
            case 'wallpaper':
                sx = sy = 1 / k; tile = true;
                break;
            default:                              // zoom, spanned
                sx = sy = Math.max(area.width / iw, area.height / ih);
        }
        if (!tile) {
            ox = (area.width - iw * sx) / 2;
            oy = (area.height - ih * sy) / 2;
        }

        let nch = pix.get_n_channels(), stride = pix.get_rowstride(), data = this.bytes;
        let total = 0, n = 0, nx = 96, ny = 4;
        for (let j = 0; j < ny; j++) {
            for (let i = 0; i < nx; i++) {
                let px = rect.x + (i + 0.5) * rect.width / nx;
                let py = rect.y + (j + 0.5) * rect.height / ny;
                let ix = Math.floor((px - area.x - ox) / sx);
                let iy = Math.floor((py - area.y - oy) / sy);
                if (tile) {
                    ix = ((ix % iw) + iw) % iw;
                    iy = ((iy % ih) + ih) % ih;
                }
                if (ix < 0 || iy < 0 || ix >= iw || iy >= ih) {
                    total += fallback;
                } else {
                    let o = iy * stride + ix * nch;
                    total += luma(data[o] / 255, data[o + 1] / 255, data[o + 2] / 255);
                }
                n++;
            }
        }
        return total / n;
    }
}

// ---------- manager ----------

class MenubarManager {
    constructor(uuid) {
        this.blur = true;
        this.blurRadius = 40;
        this.adaptiveText = true;
        this.lightThreshold = 0.62;
        this.settings = new Settings.ExtensionSettings(this, uuid);
        this.settings.bind('blur', 'blur', () => this.rebuild());
        this.settings.bind('blur-radius', 'blurRadius', () => this.rebuild());
        this.settings.bind('adaptive-text', 'adaptiveText', () => this.updateText());
        this.settings.bind('light-threshold', 'lightThreshold', () => this.updateText());
        this.blurs = [];
        this.sampler = new WallpaperSampler();
        this.timeoutId = 0;
        this.lateId = 0;
        this.ids = [];
    }

    enable() {
        this.bg = new Gio.Settings({ schema_id: 'org.cinnamon.desktop.background' });
        this.ids.push([this.bg, this.bg.connect('changed', () => this.schedule(false))]);
        this.ids.push([Main.layoutManager, Main.layoutManager.connect('monitors-changed', () => this.schedule(true))]);
        this.ids.push([global.settings, global.settings.connect('changed::panels-enabled', () => {
            this.destroyBlurs();
            this.schedule(true);
            if (this.lateId)
                GLib.source_remove(this.lateId);
            this.lateId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 1500, () => {
                this.lateId = 0;
                this.rebuild();
                return GLib.SOURCE_REMOVE;
            });
        })]);
        this.ids.push([global.settings, global.settings.connect('changed::panels-height', () => this.schedule(false))]);
        this.rebuild();
    }

    disable() {
        if (this.timeoutId)
            GLib.source_remove(this.timeoutId);
        if (this.lateId)
            GLib.source_remove(this.lateId);
        this.timeoutId = this.lateId = 0;
        for (let [obj, id] of this.ids)
            obj.disconnect(id);
        this.ids = [];
        this.destroyBlurs();
        for (let panel of this.panels())
            panel.actor.remove_style_class_name(LIGHT_CLASS);
        this.settings.finalize();
    }

    panels() {
        return Main.panelManager.getPanels().filter(p => p && p.actor);
    }

    // Panels are rebuilt by Cinnamon on some changes; wait for that to settle.
    schedule(rebuild) {
        if (this.timeoutId)
            GLib.source_remove(this.timeoutId);
        this.timeoutId = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 400, () => {
            this.timeoutId = 0;
            if (rebuild)
                this.rebuild();
            else
                this.updateText();
            return GLib.SOURCE_REMOVE;
        });
    }

    destroyBlurs() {
        for (let b of this.blurs) {
            try {
                b.destroy();
            } catch (e) {
                global.logError(`${LOG_PREFIX} cleanup: ${e.message}`);
            }
        }
        this.blurs = [];
    }

    rebuild() {
        this.destroyBlurs();
        for (let panel of this.panels()) {
            if (!this.blur && !isDock(panel))
                continue;
            this.blurs.push(new PanelBackdrop(panel, this.blur ? this.blurRadius : 0, gone => {
                this.blurs = this.blurs.filter(b => b !== gone);
                this.schedule(true);              // its panel may have been re-created
            }));
        }
        this.updateText();
    }

    updateText() {
        let monitors = Main.layoutManager.monitors;
        let screen = {
            x: Math.min(...monitors.map(m => m.x)),
            y: Math.min(...monitors.map(m => m.y)),
        };
        screen.width = Math.max(...monitors.map(m => m.x + m.width)) - screen.x;
        screen.height = Math.max(...monitors.map(m => m.y + m.height)) - screen.y;

        for (let panel of this.panels()) {
            let actor = panel.actor;
            let light = false;
            if (this.adaptiveText && !isDock(panel)) {   // the dock has its own background
                let monitor = monitors[panel.monitorIndex];
                let rect = { x: actor.x, y: actor.y, width: actor.width, height: actor.height };
                if (monitor && rect.width > 0) {
                    let lum = this.sampler.measure(this.bg, rect, monitor, screen);
                    light = lum >= this.lightThreshold;
                    global.log(`${LOG_PREFIX} panel ${panel.panelId}: wallpaper brightness ${lum.toFixed(2)} ` +
                               `(threshold ${this.lightThreshold}) -> ${light ? 'dark' : 'light'} text`);
                }
            }
            if (light)
                actor.add_style_class_name(LIGHT_CLASS);
            else
                actor.remove_style_class_name(LIGHT_CLASS);
        }
    }
}

let manager = null;
let extensionUuid = null;

function init(metadata) {
    extensionUuid = metadata.uuid;
}

function enable() {
    manager = new MenubarManager(extensionUuid);
    manager.enable();
}

function disable() {
    if (manager) {
        manager.disable();
        manager = null;
    }
}
