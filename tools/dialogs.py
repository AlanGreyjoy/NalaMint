#!/usr/bin/env python3
"""Open one GTK3 dialog for theme checks.  Usage: tools/dialogs.py file|message|question"""
import sys

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk  # noqa: E402

kind = sys.argv[1] if len(sys.argv) > 1 else "file"
if kind == "file":
    d = Gtk.FileChooserDialog(title="Open File", action=Gtk.FileChooserAction.OPEN)
    d.add_buttons("_Cancel", Gtk.ResponseType.CANCEL, "_Open", Gtk.ResponseType.OK)
    d.set_current_folder(sys.argv[2] if len(sys.argv) > 2 else "/home")
elif kind == "message":
    d = Gtk.MessageDialog(message_type=Gtk.MessageType.INFO, buttons=Gtk.ButtonsType.OK,
                          text="Software updates are available")
    d.format_secondary_text("Restart your computer to finish installing them.")
else:
    d = Gtk.MessageDialog(message_type=Gtk.MessageType.QUESTION, buttons=Gtk.ButtonsType.NONE,
                          text="Save changes before closing?")
    d.format_secondary_text("Your changes will be lost if you don't save them.")
    d.add_buttons("Close without Saving", Gtk.ResponseType.REJECT, "_Cancel", Gtk.ResponseType.CANCEL,
                  "_Save", Gtk.ResponseType.OK)
    d.set_default_response(Gtk.ResponseType.OK)
d.run()
