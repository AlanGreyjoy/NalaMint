const Clutter = imports.gi.Clutter, GLib = imports.gi.GLib;
let seat = Clutter.get_default_backend().get_default_seat();
let kb = seat.create_virtual_device(Clutter.InputDeviceType.KEYBOARD_DEVICE);
let t = GLib.get_monotonic_time();
kb.notify_keyval(t, Clutter.KEY_Alt_L, Clutter.KeyState.PRESSED);
kb.notify_keyval(t + 1000, Clutter.KEY_Tab, Clutter.KeyState.PRESSED);
kb.notify_keyval(t + 2000, Clutter.KEY_Tab, Clutter.KeyState.RELEASED);
global._nalamintKb = kb;
'pressed';
