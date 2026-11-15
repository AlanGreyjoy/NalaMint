// NalaMint Rounded Corners — clips every normal window to rounded corners.
//
// Muffin rounds only the top corners of the frames it draws and never clips
// app content, so this adds a fragment shader to each window's surface actor.
// The shader works in buffer pixels: it finds the window's visible frame inside
// the buffer (which may also hold invisible resize borders or a client-drawn
// shadow), cuts the four corners, and fills each cut with shadow so the edge
// stays continuous. Pixels that are already transparent (GTK client-side
// windows round themselves) are left alone.

const Clutter = imports.gi.Clutter;
const GLib = imports.gi.GLib;
const Meta = imports.gi.Meta;
const Settings = imports.ui.settings;

const EFFECT_NAME = 'nalamint-corners';
const WINDOW_TYPES = [Meta.WindowType.NORMAL, Meta.WindowType.DIALOG, Meta.WindowType.MODAL_DIALOG];

const SHADER = `
uniform sampler2D tex;
uniform float bw;
uniform float bh;
uniform float x1;
uniform float y1;
uniform float x2;
uniform float y2;
uniform float radius;
uniform float shadow;

float sample_alpha(vec2 q) {
  if (q.x < 0.0 || q.y < 0.0 || q.x > bw || q.y > bh) return 0.0;
  return texture2D(tex, q / vec2(bw, bh)).a;
}

void main() {
  vec2 uv = cogl_tex_coord_in[0].st;
  vec4 t = texture2D(tex, uv);
  vec2 p = uv * vec2(bw, bh);

  bool inside = p.x >= x1 && p.x <= x2 && p.y >= y1 && p.y <= y2;
  float cx = p.x < x1 + radius ? x1 + radius : (p.x > x2 - radius ? x2 - radius : -1.0);
  float cy = p.y < y1 + radius ? y1 + radius : (p.y > y2 - radius ? y2 - radius : -1.0);

  if (inside && cx >= 0.0 && cy >= 0.0 && t.a > 0.95) {
    vec2 c = vec2(cx, cy);
    float dist = distance(p, c);
    float cover = clamp(radius - dist + 0.5, 0.0, 1.0);
    if (cover < 1.0) {
      // Shadow just outside the straight edges next to this corner
      float d = max(dist - radius, 0.0);
      float sx = p.x < cx ? -1.0 : 1.0;
      float sy = p.y < cy ? -1.0 : 1.0;
      float ex = sx < 0.0 ? x1 : x2;
      float ey = sy < 0.0 ? y1 : y2;
      float sampled = 0.5 * (sample_alpha(vec2(ex + sx * (d + 0.5), cy)) +
                             sample_alpha(vec2(cx, ey + sy * (d + 0.5))));
      float fallback = shadow * clamp(1.0 - d / 14.0, 0.0, 1.0);
      float a = max(sampled, fallback);
      t = t * cover + vec4(0.0, 0.0, 0.0, a) * (1.0 - cover);
    }
  }
  cogl_color_out = t * cogl_color_in;
}
`;

// Clutter treats integral JS numbers as ints; uniforms here are floats.
function asFloat(v) {
    return v + 0.00001;
}

function surfaceOf(actor) {
    return actor.get_children().find(c =>
        c.constructor.$gtype && c.constructor.$gtype.name.startsWith('MetaSurfaceActor')) || null;
}

class CornerManager {
    constructor(uuid) {
        this.radius = 12;
        this.shadowFocused = 0.26;
        this.shadowUnfocused = 0.16;
        this.settings = new Settings.ExtensionSettings(this, uuid);
        this.settings.bind('radius', 'radius', () => this.refreshAll());
        this.settings.bind('shadow-focused', 'shadowFocused', () => this.refreshAll());
        this.settings.bind('shadow-unfocused', 'shadowUnfocused', () => this.refreshAll());
        this.tracked = new Map();   // MetaWindowActor -> { win, ids, actorIds }
        this.globalIds = [];
    }

    enable() {
        for (let actor of global.get_window_actors())
            this.track(actor);
        this.globalIds.push(global.display.connect('window-created', (display, win) => {
            // The actor can lag behind the window by a main-loop turn
            GLib.idle_add(GLib.PRIORITY_DEFAULT, () => {
                let actor = win.get_compositor_private();
                if (actor)
                    this.track(actor);
                return GLib.SOURCE_REMOVE;
            });
        }));
    }

    disable() {
        for (let id of this.globalIds)
            global.display.disconnect(id);
        this.globalIds = [];
        for (let actor of [...this.tracked.keys()])
            this.untrack(actor);
        this.settings.finalize();
    }

    track(actor) {
        if (this.tracked.has(actor) || !actor.meta_window)
            return;
        let win = actor.meta_window;
        let update = () => this.update(actor);
        let ids = [
            win.connect('size-changed', update),
            win.connect('notify::maximized-horizontally', update),
            win.connect('notify::maximized-vertically', update),
            win.connect('notify::fullscreen', update),
            win.connect('notify::tile-mode', update),
            win.connect('notify::appears-focused', update),
        ];
        let actorIds = [
            actor.connect('actor-added', update),
            actor.connect('destroy', () => this.untrack(actor, true)),
        ];
        this.tracked.set(actor, { win, ids, actorIds });
        this.update(actor);
    }

    untrack(actor, destroyed = false) {
        let entry = this.tracked.get(actor);
        if (!entry)
            return;
        this.tracked.delete(actor);
        for (let id of entry.ids)
            entry.win.disconnect(id);
        if (!destroyed) {
            for (let id of entry.actorIds)
                actor.disconnect(id);
            this.removeEffect(actor);
        }
    }

    refreshAll() {
        for (let actor of this.tracked.keys())
            this.update(actor);
    }

    eligible(win) {
        if (!WINDOW_TYPES.includes(win.get_window_type()))
            return false;
        if (win.fullscreen || win.get_maximized() === Meta.MaximizeFlags.BOTH)
            return false;
        if (win.tile_mode && win.tile_mode !== 0)
            return false;
        let f = win.get_frame_rect();
        return this.radius > 0 && f.width > 4 * this.radius && f.height > 4 * this.radius;
    }

    removeEffect(actor) {
        let surface = surfaceOf(actor);
        if (surface)
            surface.remove_effect_by_name(EFFECT_NAME);
    }

    update(actor) {
        let entry = this.tracked.get(actor);
        let surface = surfaceOf(actor);
        if (!entry || !surface)
            return;
        let win = entry.win;
        if (!this.eligible(win)) {
            surface.remove_effect_by_name(EFFECT_NAME);
            return;
        }

        let effect = surface.get_effect(EFFECT_NAME);
        if (!effect) {
            effect = new Clutter.ShaderEffect({ shader_type: Clutter.ShaderType.FRAGMENT_SHADER });
            effect.set_shader_source(SHADER);
            effect.set_uniform_value('tex', 0);
            surface.add_effect_with_name(EFFECT_NAME, effect);
        }

        let f = win.get_frame_rect();
        let b = win.get_buffer_rect();
        // Muffin-framed windows: its shadow is not painted under the window,
        // so the shader fills the cut corners itself.
        let shadow = win.decorated
            ? (win.appears_focused ? this.shadowFocused : this.shadowUnfocused)
            : 0;
        effect.set_uniform_value('bw', asFloat(b.width));
        effect.set_uniform_value('bh', asFloat(b.height));
        effect.set_uniform_value('x1', asFloat(f.x - b.x));
        effect.set_uniform_value('y1', asFloat(f.y - b.y));
        effect.set_uniform_value('x2', asFloat(f.x - b.x + f.width));
        effect.set_uniform_value('y2', asFloat(f.y - b.y + f.height));
        effect.set_uniform_value('radius', asFloat(this.radius));
        effect.set_uniform_value('shadow', asFloat(shadow));
    }
}

let manager = null;
let extensionUuid = null;

function init(metadata) {
    extensionUuid = metadata.uuid;
}

function enable() {
    manager = new CornerManager(extensionUuid);
    manager.enable();
}

function disable() {
    if (manager) {
        manager.disable();
        manager = null;
    }
}
