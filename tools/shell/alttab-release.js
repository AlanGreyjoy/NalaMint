const Clutter = imports.gi.Clutter, GLib = imports.gi.GLib;
let kb = global._nalamintKb;
if (kb) {
  let t = GLib.get_monotonic_time();
  kb.notify_keyval(t, Clutter.KEY_Escape, Clutter.KeyState.PRESSED);
  kb.notify_keyval(t + 1000, Clutter.KEY_Escape, Clutter.KeyState.RELEASED);
  kb.notify_keyval(t + 2000, Clutter.KEY_Alt_L, Clutter.KeyState.RELEASED);
  delete global._nalamintKb;
}
'released';
