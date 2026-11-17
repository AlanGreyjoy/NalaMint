#!/usr/bin/python3
"""NalaMint Dictation, a GTK companion for Cinnamon."""

import math
import os
from pathlib import Path
import shutil
import sys
import time

import gi

APP_ID = "io.github.AlanGreyjoy.NalaMint.Dictation"
from gi.repository import GLib

GLib.set_prgname(APP_ID)
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkX11", "3.0")
gi.require_version("XApp", "1.0")
from gi.repository import Gdk, GdkPixbuf, GdkX11, Gtk, XApp
from Xlib import error

from desktop import Desktop, SHORTCUT
from speech import MAX_SECONDS, RATE, engine_paths, level, record, transcribe


HERE = Path(__file__).resolve().parent
NAME = "NalaMint Dictation"
ICON = "nalamint-dictation"


def label(text, css=None):
    widget = Gtk.Label(label=text, xalign=0)
    widget.set_line_wrap(True)
    if css:
        widget.get_style_context().add_class(css)
    return widget


class Indicator(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.set_name("dictation-indicator")
        self.set_accept_focus(False)
        self.set_focus_on_map(False)
        visual = self.get_screen().get_rgba_visual()
        if visual:
            self.set_visual(visual)
        self.connect("realize", lambda window: window.get_window().set_pass_through(True))
        self.message = label("")
        self.meter = Gtk.DrawingArea(width_request=30, height_request=18)
        self.meter.connect("draw", self.draw_meter)
        self.meter_level = 0
        self.hide_timer = 0
        content = Gtk.Box(spacing=8)
        content.get_style_context().add_class("dictation-indicator-content")
        content.add(self.meter)
        content.add(self.message)
        self.add(content)
        content.show_all()

    def draw_meter(self, widget, cr):
        color = widget.get_style_context().get_color(Gtk.StateFlags.NORMAL)
        cr.set_source_rgba(color.red, color.green, color.blue, color.alpha)
        cr.set_line_width(2.4)
        cr.set_line_cap(1)
        for index, scale in enumerate((0.48, 0.75, 1, 0.67, 0.4)):
            height = 1.2 + scale * 6.1 * self.meter_level
            x = 3 + 6 * index
            cr.move_to(x, 9 - height)
            cr.line_to(x, 9 + height)
        cr.stroke()

    def update_level(self, value):
        self.meter_level = min(1, math.sqrt(value * 7))
        self.meter.queue_draw()

    def show_message(self, text, target=None, listening=False, transient=False):
        self.dismiss()
        self.message.set_text(text)
        self.meter.set_visible(listening)
        self.update_level(0)
        screen = self.get_display()
        monitor = screen.get_primary_monitor() or screen.get_monitor(0)
        if target:
            foreign = GdkX11.X11Window.foreign_new_for_display(screen, target[1])
            if foreign:
                monitor = screen.get_monitor_at_window(foreign) or monitor
        if monitor:
            work = monitor.get_workarea()
            size = self.get_child().get_preferred_size()[1]
            self.resize(size.width, size.height)
            self.move(work.x + (work.width - size.width) // 2, work.y + 16)
        self.show()
        if transient:
            self.hide_timer = GLib.timeout_add(2600, self.expire)

    def expire(self):
        self.hide_timer = 0
        self.hide()
        return GLib.SOURCE_REMOVE

    def dismiss(self):
        if self.hide_timer:
            GLib.source_remove(self.hide_timer)
            self.hide_timer = 0
        self.hide()


class Dictation(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)
        self.window = self.desktop = self.capture = self.job = None
        self.capture_timer = self.job_timer = self.paste_timer = 0
        self.indicator = self.panel_icon = None
        self.target = None
        self.transcript = ""
        self.auto_paste = True
        self.status = "Dictation is off"
        self.engine, self.model = engine_paths()

    def do_startup(self):
        Gtk.Application.do_startup(self)
        GLib.set_application_name(NAME)
        icon = HERE / f"{ICON}.png"
        if not icon.is_file():
            icon = HERE.parents[1] / "icons" / "apps" / f"{ICON}.png"
        self.icon = str(icon)
        Gtk.Window.set_default_icon_from_file(self.icon)
        styles = Gtk.CssProvider()
        styles.load_from_path(str(HERE / "style.css"))
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), styles,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.indicator = Indicator()

    def do_activate(self):
        if self.window is None:
            self.build_window()
        self.window.present()

    def build_window(self):
        window = Gtk.ApplicationWindow(application=self, title=NAME, default_width=476)
        window.set_resizable(False)
        window.connect("destroy", self.window_closed)
        self.window = window

        header = Gtk.HeaderBar(title=NAME, show_close_button=True)
        window.set_titlebar(header)
        quit_button = Gtk.Button(label="Quit")
        quit_button.set_tooltip_text("Quit NalaMint Dictation")
        quit_button.get_accessible().set_name("Quit NalaMint Dictation")
        quit_button.connect("clicked", lambda *_: self.quit())
        header.pack_end(quit_button)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20, margin=22)
        window.add(body)
        intro = Gtk.Box(spacing=12)
        icon = GdkPixbuf.Pixbuf.new_from_file_at_scale(self.icon, 48, 48, True)
        intro.add(Gtk.Image.new_from_pixbuf(icon))
        intro_text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, valign=Gtk.Align.CENTER)
        intro_text.add(label("Voice dictation", "dictation-title"))
        intro_text.add(label("Hold the shortcut, speak, then release.", "dim-label"))
        intro.pack_start(intro_text, True, True, 0)
        body.add(intro)

        settings = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        settings.get_style_context().add_class("dictation-card")
        body.add(settings)

        row = self.settings_row(settings, "Push to talk", "Press Esc to cancel while recording")
        shortcut = label(SHORTCUT.replace("+", "  +  "), "dictation-key")
        row.pack_end(shortcut, False, False, 0)
        settings.add(Gtk.Separator())

        row = self.settings_row(settings, "Auto-paste", "Uses the clipboard to insert the transcript")
        toggle = Gtk.Switch(active=self.auto_paste, valign=Gtk.Align.CENTER)
        toggle.get_accessible().set_name("Auto-paste")
        toggle.connect("notify::active", lambda widget, _: setattr(self, "auto_paste", widget.get_active()))
        row.pack_end(toggle, False, False, 0)
        settings.add(Gtk.Separator())

        self.setup_problem = self.check_setup()
        self.settings_row(settings, "On-device transcription", self.setup_problem or "Whisper · English")

        row = Gtk.Box(spacing=10)
        self.status_label = label(self.status, "dim-label")
        row.pack_start(self.status_label, True, True, 0)
        self.enable_button = Gtk.Button()
        self.enable_button.connect("clicked", self.toggle_enabled)
        row.pack_end(self.enable_button, False, False, 0)
        body.add(row)
        self.refresh_enable_button()

        transcript = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        heading = Gtk.Box(spacing=6)
        heading.pack_start(label("Last transcript", "dictation-heading"), True, True, 0)
        self.copy_button = Gtk.Button(label="Copy")
        self.copy_button.connect("clicked", self.copy_transcript)
        heading.add(self.copy_button)
        transcript.add(heading)
        scroller = Gtk.ScrolledWindow(min_content_height=88, shadow_type=Gtk.ShadowType.IN)
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.preview = Gtk.TextView(editable=False, cursor_visible=False, wrap_mode=Gtk.WrapMode.WORD_CHAR,
                                    left_margin=10, right_margin=10, top_margin=10, bottom_margin=10)
        self.preview.get_accessible().set_name("Last transcript")
        scroller.add(self.preview)
        transcript.add(scroller)
        body.add(transcript)
        self.refresh_transcript()
        window.show_all()

    @staticmethod
    def settings_row(container, title, detail):
        row = Gtk.Box(spacing=8, margin=11)
        description = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        description.add(label(title, "dictation-heading"))
        description.add(label(detail, "dim-label"))
        row.pack_start(description, True, True, 0)
        container.add(row)
        return row

    def window_closed(self, _window):
        self.window = None

    def check_setup(self):
        if os.environ.get("XDG_SESSION_TYPE") == "wayland" or not isinstance(Gdk.Display.get_default(), GdkX11.X11Display):
            return "Requires a Cinnamon X11 session."
        if not shutil.which("parec"):
            return "Install pulseaudio-utils to use your microphone."
        if not os.access(self.engine, os.X_OK) or not self.model.is_file():
            return "Set up whisper-cli and the English model first. See the NalaMint README."
        return None

    def refresh_enable_button(self):
        if not self.window:
            return
        button_style = self.enable_button.get_style_context()
        if self.desktop:
            self.enable_button.set_label("Disable Dictation")
            button_style.remove_class("suggested-action")
        else:
            self.enable_button.set_label("Enable Dictation")
            button_style.add_class("suggested-action")
        self.enable_button.set_sensitive(self.setup_problem is None)

    def toggle_enabled(self, _button):
        if self.desktop:
            self.disable()
            return
        try:
            self.desktop = Desktop(self.begin, self.finish, self.cancel, self.disable)
        except (RuntimeError, error.DisplayError) as exc:
            self.set_status(str(exc))
            return
        self.hold()
        self.panel_icon = XApp.StatusIcon.new_with_name(APP_ID)
        self.panel_icon.set_icon_name(self.icon)
        self.panel_icon.set_tooltip_text(f"{NAME} · {SHORTCUT}")
        menu = Gtk.Menu()
        for title, action in (("Open Dictation", self.activate), ("Quit Dictation", self.quit)):
            item = Gtk.MenuItem(label=title)
            item.connect("activate", lambda _, fn=action: fn())
            menu.append(item)
        menu.show_all()
        self.panel_icon.set_primary_menu(menu)
        self.panel_icon.set_secondary_menu(menu)
        self.refresh_enable_button()
        self.set_status("Ready to dictate")

    def disable(self):
        self.cancel(report=False)
        if self.desktop:
            self.desktop.close()
            self.desktop = None
            self.panel_icon.set_visible(False)
            self.panel_icon = None
            self.release()
        self.indicator.dismiss()
        self.refresh_enable_button()
        self.set_status("Dictation is off")

    def set_status(self, message, overlay=False, transient=False):
        self.status = message
        if self.window:
            self.status_label.set_text(message)
        if overlay:
            self.indicator.show_message(message, self.target, listening=message == "Listening…", transient=transient)

    def begin(self):
        if self.capture or self.job or self.paste_timer:
            return
        self.target = self.desktop.focus()
        self.pcm = bytearray()
        self.loudest = 0
        try:
            self.capture = record()
        except GLib.Error:
            self.set_status("Could not open the microphone", overlay=True, transient=True)
            return
        self.set_status("Listening…", overlay=True)
        self.capture_timer = GLib.timeout_add_seconds(MAX_SECONDS, self.capture_limit)
        self.read_audio(self.capture)

    def read_audio(self, capture):
        capture.get_stdout_pipe().read_bytes_async(1280, GLib.PRIORITY_DEFAULT, None, self.audio_chunk, capture)

    def audio_chunk(self, stream, result, capture):
        if capture is not self.capture:
            return
        try:
            chunk = stream.read_bytes_finish(result).get_data()
        except GLib.Error:
            chunk = b""
        if not chunk:
            self.stop_capture()
            self.pcm.clear()
            self.set_status("Microphone disconnected or unavailable", overlay=True, transient=True)
            return
        offset = len(self.pcm) & ~1
        self.pcm.extend(chunk)
        samples = self.pcm[offset:len(self.pcm) & ~1]
        if samples:
            volume = level(samples)
            self.loudest = max(self.loudest, volume)
            self.indicator.update_level(volume)
        self.read_audio(capture)

    def stop_capture(self):
        self.capture.force_exit()
        self.capture = None
        if self.capture_timer:
            GLib.source_remove(self.capture_timer)
            self.capture_timer = 0

    def capture_limit(self):
        self.capture_timer = 0
        self.finish()
        return GLib.SOURCE_REMOVE

    def finish(self):
        if not self.capture:
            return
        self.stop_capture()
        pcm, self.pcm = self.pcm, bytearray()
        if len(pcm) < 2 * RATE * 0.3 or self.loudest < 0.003:
            self.set_status("No speech detected", overlay=True, transient=True)
            return
        self.set_status("Transcribing…", overlay=True)
        try:
            self.job = transcribe(self.engine, self.model, pcm[:len(pcm) & ~1], self.transcription_ready)
        except GLib.Error:
            self.set_status("Could not start Whisper", overlay=True, transient=True)
            return
        self.job_timer = GLib.timeout_add_seconds(90, self.transcription_timeout)

    def transcription_timeout(self):
        self.job_timer = 0
        self.job.force_exit()
        self.job = None
        self.set_status("Transcription timed out", overlay=True, transient=True)
        return GLib.SOURCE_REMOVE

    def transcription_ready(self, job, transcript):
        if job is not self.job:
            return
        self.job = None
        GLib.source_remove(self.job_timer)
        self.job_timer = 0
        if transcript is None:
            self.set_status("Whisper could not transcribe the recording", overlay=True, transient=True)
            return
        if not transcript:
            self.set_status("No speech detected", overlay=True, transient=True)
            return
        self.transcript = transcript
        self.refresh_transcript()
        deadline = time.monotonic() + 2
        self.paste_timer = GLib.timeout_add(40, self.maybe_paste, deadline)

    def maybe_paste(self, deadline):
        if self.auto_paste and self.target and self.desktop.focus() == self.target:
            if self.desktop.ready_to_paste():
                self.copy_transcript()
                if self.desktop.paste():
                    self.set_status("Ready to dictate")
                    self.indicator.dismiss()
                    self.paste_timer = 0
                    return GLib.SOURCE_REMOVE
            elif time.monotonic() < deadline:
                return GLib.SOURCE_CONTINUE
        self.paste_timer = 0
        self.set_status("Transcript ready to copy", overlay=True, transient=True)
        return GLib.SOURCE_REMOVE

    def refresh_transcript(self):
        if self.window:
            self.preview.get_buffer().set_text(self.transcript or "Your latest dictation will appear here.")
            self.copy_button.set_sensitive(bool(self.transcript))

    def copy_transcript(self, _button=None):
        if self.transcript:
            Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).set_text(self.transcript, -1)

    def cancel(self, report=True):
        if self.capture:
            self.stop_capture()
            self.pcm.clear()
        if self.job:
            self.job.force_exit()
            self.job = None
            GLib.source_remove(self.job_timer)
            self.job_timer = 0
        if self.paste_timer:
            GLib.source_remove(self.paste_timer)
            self.paste_timer = 0
        if report:
            self.set_status("Dictation cancelled", overlay=True, transient=True)

    def do_shutdown(self):
        self.disable()
        Gtk.Application.do_shutdown(self)


if __name__ == "__main__":
    sys.exit(Dictation().run())
