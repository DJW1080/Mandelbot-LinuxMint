"""Ordinary fullscreen windows which yield to Cinnamon and dismiss on input."""

import time

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk

from .canvas import FractalCanvas
from .presentation import motion_dismisses, MOTION_GRACE_SECONDS

HINT_SECONDS = 4


class FullscreenSession:
    def __init__(self, application, settings, on_closed, on_error):
        self.on_closed = on_closed
        self.closed = False
        self.windows = []
        self.canvases = []
        self.started = time.monotonic()
        self.display = Gdk.Display.get_default()
        pointer = self.display.get_default_seat().get_pointer()
        _, x, y = pointer.get_position()
        self.pointer_origin = (x, y)
        self.monitor_handler = self.display.connect("monitor-removed", lambda *args: self.close())
        self.hints = []
        self.hint_timer = None
        for index in range(self.display.get_n_monitors()):
            self._add_window(application, settings, index, on_error)
        self.hint_timer = GLib.timeout_add_seconds(HINT_SECONDS, self._hide_hints)

    def _add_window(self, application, settings, index, on_error):
        window = Gtk.ApplicationWindow(application=application, title="Mandelbot fullscreen")
        window.set_decorated(False)
        window.set_skip_taskbar_hint(True)
        window.add_events(Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.BUTTON_PRESS_MASK
                          | Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.KEY_PRESS_MASK)
        window.connect("key-press-event", self._dismiss_event)
        window.connect("button-press-event", self._dismiss_event)
        window.connect("scroll-event", self._dismiss_event)
        window.connect("motion-notify-event", self._motion)
        window.connect("delete-event", self._dismiss_event)
        window.connect("destroy", lambda widget: self.close())
        window.connect("realize", self._hide_cursor)
        overlay = Gtk.Overlay()
        canvas = FractalCanvas(settings, on_error)
        overlay.add(canvas)
        hint = Gtk.Label(label="Move your mouse or press a key to return")
        hint.set_halign(Gtk.Align.CENTER)
        hint.set_valign(Gtk.Align.END)
        hint.set_margin_bottom(40)
        hint.get_style_context().add_class("mandelbot-hint")
        overlay.add_overlay(hint)
        window.add(overlay)
        self.windows.append(window)
        self.canvases.append(canvas)
        self.hints.append(hint)
        window.fullscreen_on_monitor(Gdk.Screen.get_default(), index)
        window.show_all()

    def _hide_cursor(self, window):
        cursor = Gdk.Cursor.new_for_display(self.display, Gdk.CursorType.BLANK_CURSOR)
        window.get_window().set_cursor(cursor)

    def _dismiss_event(self, widget, event):
        self.close()
        return True

    def _motion(self, widget, event):
        position = (event.x_root, event.y_root)
        elapsed = time.monotonic() - self.started
        if elapsed < MOTION_GRACE_SECONDS:
            self.pointer_origin = position
        elif motion_dismisses(self.pointer_origin, position, elapsed):
            self.close()
        return True

    def _hide_hints(self):
        self.hint_timer = None
        for hint in self.hints:
            hint.hide()
        return GLib.SOURCE_REMOVE

    def close(self):
        if self.closed:
            return
        self.closed = True
        if self.hint_timer:
            GLib.source_remove(self.hint_timer)
            self.hint_timer = None
        self.display.disconnect(self.monitor_handler)
        for window in self.windows:
            window.destroy()
        self.on_closed()
