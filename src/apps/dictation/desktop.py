"""Cinnamon X11 shortcut and text insertion."""

from gi.repository import GLib
from Xlib import X, XK, display, error
from Xlib.ext import xtest


SHORTCUT = "Ctrl+Alt+V"


class Desktop:
    def __init__(self, start, finish, cancel, disconnected):
        self.connection = display.Display()
        self.root = self.connection.screen().root
        self.trigger = self.keycode("v")
        self.escape = self.keycode("Escape")
        self.active_window = self.connection.intern_atom("_NET_ACTIVE_WINDOW")
        num_lock = self.keycode("Num_Lock")
        masks = self.connection.get_modifier_mapping()
        num_mask = next((1 << i for i, keys in enumerate(masks) if num_lock in keys), 0)
        modifiers = X.ControlMask | X.Mod1Mask
        self.grabs = {modifiers | locks for locks in (0, X.LockMask, num_mask, X.LockMask | num_mask)}
        self.held = False
        if not self.connection.has_extension("XTEST") or not self.trigger:
            self.connection.close()
            raise RuntimeError("This X11 session does not support the dictation shortcut.")

        failures = []
        for mask in self.grabs:
            failure = error.CatchError(error.BadAccess)
            self.root.grab_key(self.trigger, mask, False, X.GrabModeAsync, X.GrabModeAsync,
                               onerror=failure)
            failures.append(failure)
        self.connection.sync()
        if any(failure.get_error() for failure in failures):
            self.connection.close()
            raise RuntimeError(f"{SHORTCUT} is already in use by another shortcut.")

        def receive(_fd, condition):
            if condition & (GLib.IOCondition.HUP | GLib.IOCondition.ERR):
                self.watch = 0
                disconnected()
                return GLib.SOURCE_REMOVE
            while self.connection.pending_events():
                event = self.connection.next_event()
                if event.type not in (X.KeyPress, X.KeyRelease):
                    continue
                if event.detail == self.trigger and event.type == X.KeyPress and not self.held:
                    self.held = True
                    start()
                elif event.detail == self.trigger and event.type == X.KeyRelease and self.held:
                    # X11 may emit a release/press pair while the trigger is repeating.
                    if self.pressed(self.trigger):
                        continue
                    self.held = False
                    finish()
                elif event.detail == self.escape and event.type == X.KeyPress and self.held:
                    cancel()
            return GLib.SOURCE_CONTINUE

        self.watch = GLib.io_add_watch(self.connection.fileno(), GLib.PRIORITY_DEFAULT,
                                       GLib.IOCondition.IN | GLib.IOCondition.HUP
                                       | GLib.IOCondition.ERR, receive)

    def keycode(self, name):
        return self.connection.keysym_to_keycode(XK.string_to_keysym(name))

    def pressed(self, code):
        keys = self.connection.query_keymap()
        return bool(keys[code // 8] & (1 << (code % 8)))

    def ready_to_paste(self):
        if self.held:
            return False
        keys = self.connection.query_keymap()
        modifiers = self.connection.get_modifier_mapping()
        return not any(keys[code // 8] & (1 << (code % 8))
                       for index in (0, 2, 3, 6) for code in modifiers[index] if code)

    def focus(self):
        focus = self.connection.get_input_focus().focus
        xid = getattr(focus, "id", 0)
        if not xid or xid == self.root.id:
            return None
        active = self.root.get_full_property(self.active_window, X.AnyPropertyType)
        return (xid, int(active.value[0]) if active and len(active.value) else xid)

    def paste(self):
        ctrl = self.keycode("Control_L")
        if not ctrl:
            return False
        for kind, code in ((X.KeyPress, ctrl), (X.KeyPress, self.trigger),
                           (X.KeyRelease, self.trigger), (X.KeyRelease, ctrl)):
            xtest.fake_input(self.connection, kind, code)
        self.connection.flush()
        return True

    def close(self):
        if self.watch:
            GLib.source_remove(self.watch)
        try:
            self.connection.close()
        except error.ConnectionClosedError:
            pass
