"""Single-instance GTK application: settings, fullscreen display and idle watcher."""

import logging
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gio, GLib, Gtk

from .config import load_settings, save_settings
from .desktop import DesktopState
from .fullscreen import FullscreenSession
from .integration import write_autostart
from .ui import SettingsWindow
from .watcher import IdleWatcher

APPLICATION_ID = "org.mandelbot.Screensaver"
GUARD_SECONDS = 1
STYLE = b"""
.mandelbot { background-color: #111c26; color: #e3edef; }
.mandelbot-text { color: #e3edef; }
.mandelbot checkbutton label { color: #e3edef; }
.mandelbot scale value { color: #bcd1d7; }
.mandelbot scale label { color: #a7bdc6; }
.mandelbot .dim-label { color: #a7bdc6; }
.mandelbot-title { font-size: 25px; font-weight: bold; }
.mandelbot-section { font-size: 11px; font-weight: bold; letter-spacing: 1px; color: #6edac7; }
.mandelbot button { padding: 8px 13px; }
.mandelbot frame { border: 1px solid #29444e; }
.mandelbot-hint { background: rgba(5, 12, 18, 0.8); color: #e6f4f2; padding: 12px 20px; border-radius: 20px; }
"""


class MandelbotApplication(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APPLICATION_ID, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.window = None
        self.session = None
        self.watcher = None
        self.desktop = None
        self.guard_timer = None
        self.settings = None
        self.restore_settings_window = False
        self.shutting_down = False
        self.exit_status = 0

    def do_startup(self):
        Gtk.Application.do_startup(self)
        provider = Gtk.CssProvider()
        provider.load_from_data(STYLE)
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider,
                                                 Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        root = Path(__file__).resolve().parent.parent
        icon = root / "data/mandelbot.svg"
        if icon.is_file():
            Gtk.Window.set_default_icon_from_file(str(icon))
        else:
            Gtk.Window.set_default_icon_name("mandelbot")

    def do_activate(self):
        try:
            if self.window is None:
                self.settings = load_settings()
                self.window = SettingsWindow(self, self.settings)
                self.window.connect("destroy", self._window_closed)
                if self.settings.automatic and self.watcher is None:
                    self.start_watcher(self.settings)
            self.stop_fullscreen()
            self.window.show_all()
            self.window.present()
        except Exception as error:
            self.report_error(error)

    def do_command_line(self, command_line):
        arguments = command_line.get_arguments()[1:]
        try:
            if "--quit" in arguments:
                self.quit()
            elif "--watch" in arguments:
                settings = load_settings()
                if settings.automatic:
                    self.start_watcher(settings)
            elif "--fullscreen" in arguments:
                self.show_fullscreen(load_settings())
            else:
                self.activate()
        except Exception as error:
            command_line.set_exit_status(1)
            self.report_error(error)
            return 1
        return 0

    def _window_closed(self, window):
        self.window = None

    def _ensure_desktop(self):
        if self.desktop is None:
            self.desktop = DesktopState(self._desktop_changed)
        return self.desktop

    def save_preferences(self, settings):
        # Validate desktop access before persisting a request for automatic mode.
        if settings.automatic:
            desktop = self._ensure_desktop()
            desktop.active()
            desktop.inhibited()
        save_settings(settings)
        write_autostart(settings.autostart)
        self.settings = settings
        if settings.automatic:
            self.start_watcher(settings)
        else:
            self.stop_watcher()

    def start_watcher(self, settings):
        desktop = self._ensure_desktop()
        desktop.active()
        desktop.inhibited()
        # Construct the replacement before stopping a working watcher.
        replacement = IdleWatcher(settings, desktop,
            lambda: self.show_fullscreen(settings), self.stop_fullscreen, self._watcher_error)
        self.stop_watcher()
        self.watcher = replacement
        self.settings = settings
        self.hold()

    def stop_watcher(self):
        if self.watcher is not None:
            self.watcher.close()
            self.watcher = None
            self.release()

    def show_fullscreen(self, settings):
        if self.session is not None:
            return
        try:
            if self._ensure_desktop().active():
                return
            self.restore_settings_window = self.window is not None and self.window.get_visible()
            self.session = FullscreenSession(self, settings, self._fullscreen_closed, self._fullscreen_error)
            if self.restore_settings_window:
                self.window.hide()
            self.guard_timer = GLib.timeout_add_seconds(GUARD_SECONDS, self._guard)
        except Exception as error:
            self._fullscreen_error(error)

    def stop_fullscreen(self):
        if self.session is not None:
            self.session.close()

    def _fullscreen_closed(self):
        self.session = None
        if self.guard_timer:
            GLib.source_remove(self.guard_timer)
            self.guard_timer = None
        if self.watcher is not None:
            self.watcher.dismiss()
        if self.restore_settings_window and self.window is not None and not self.shutting_down:
            self.window.show_all()
        self.restore_settings_window = False

    def _desktop_changed(self, active):
        if active:
            self.stop_fullscreen()
            if self.watcher is not None:
                self.watcher.dismiss()

    def _guard(self):
        try:
            if self.desktop.active():
                self.guard_timer = None
                self.stop_fullscreen()
                return GLib.SOURCE_REMOVE
        except Exception as error:
            self.guard_timer = None
            self._fullscreen_error(error)
            return GLib.SOURCE_REMOVE
        return GLib.SOURCE_CONTINUE

    def _fullscreen_error(self, error):
        self.stop_fullscreen()
        self.report_error(error)

    def _watcher_error(self, error):
        self.stop_watcher()
        self.report_error(error)

    def report_error(self, error):
        self.exit_status = 1
        logging.error("%s", error, exc_info=(type(error), error, error.__traceback__))
        dialog = Gtk.MessageDialog(transient_for=self.window, modal=True,
            message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.CLOSE,
            text="Mandelbot could not complete this action")
        dialog.format_secondary_text(str(error))
        dialog.set_application(self)
        dialog.connect("response", lambda widget, response: widget.destroy())
        dialog.show_all()

    def do_shutdown(self):
        self.shutting_down = True
        self.stop_fullscreen()
        self.stop_watcher()
        if self.window is not None:
            self.window.destroy()
        if self.desktop is not None:
            self.desktop.close()
        Gtk.Application.do_shutdown(self)
