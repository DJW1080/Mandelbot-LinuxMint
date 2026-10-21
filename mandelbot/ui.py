"""Native GTK settings with a live preview and explicit preference saving."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from .canvas import FractalCanvas
from .config import Settings, PALETTES, QUALITY, MAX_IDLE_MINUTES
from .quality import speed_to_position, position_to_speed

WINDOW_WIDTH, WINDOW_HEIGHT = 1080, 700
SPEED_SLIDER_STEP = 0.005


def label(text, style=None):
    widget = Gtk.Label(label=text, xalign=0)
    widget.get_style_context().add_class("mandelbot-text")
    if style:
        widget.get_style_context().add_class(style)
    return widget


class SettingsWindow(Gtk.ApplicationWindow):
    def __init__(self, application, settings):
        super().__init__(application=application, title="Mandelbot")
        self.app = application
        self.set_default_size(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.get_style_context().add_class("mandelbot")
        header = Gtk.HeaderBar(title="Mandelbot", subtitle="Mandelbrot journeys for Linux Mint")
        header.set_show_close_button(True)
        self.set_titlebar(header)
        start = Gtk.Button(label="Start fullscreen")
        start.get_style_context().add_class("suggested-action")
        start.connect("clicked", lambda button: self.app.show_fullscreen(self.read_settings()))
        header.pack_end(start)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        outer.set_border_width(24)
        self.add(outer)
        heading = label("A little infinity on your desktop.", "mandelbot-title")
        outer.pack_start(heading, False, False, 0)
        subtitle = label("Follow the Mandelbrot set through quiet, ever-changing colour.", "dim-label")
        outer.pack_start(subtitle, False, False, 0)

        columns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=26)
        outer.pack_start(columns, True, True, 0)
        controls = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        controls.set_size_request(270, -1)
        columns.pack_start(controls, False, False, 0)
        controls.pack_start(label("YOUR JOURNEY", "mandelbot-section"), False, False, 0)
        self.palette = self._combo(controls, "Colour palette", PALETTES, settings.palette)
        self.quality = self._combo(controls, "Rendering quality", QUALITY, settings.quality)
        controls.pack_start(label("Journey speed"), False, False, 0)
        self.speed = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0.0, 1.0, SPEED_SLIDER_STEP)
        self.speed.set_digits(3)
        self.speed.set_round_digits(-1)
        self.speed.connect("format-value", lambda scale, value: f"{position_to_speed(value):.2f}×")
        self.speed.set_value(speed_to_position(settings.speed))
        for speed, caption in [(0.01, "Very slow"), (0.1, "Slow"), (1.0, "Normal")]:
            self.speed.add_mark(speed_to_position(speed), Gtk.PositionType.BOTTOM, caption)
        self.speed.connect("value-changed", self._preview_changed)
        controls.pack_start(self.speed, False, False, 0)
        quality_note = label("Ultra: native resolution · 4 samples per pixel", "dim-label")
        quality_note.set_line_wrap(True)
        quality_note.set_max_width_chars(32)
        controls.pack_start(quality_note, False, False, 0)
        controls.pack_start(Gtk.Separator(), False, False, 6)

        row = Gtk.Box(spacing=12)
        row.pack_start(label("Start when idle"), True, True, 0)
        self.automatic = Gtk.Switch(active=settings.automatic)
        self.automatic.connect("notify::active", self._automatic_changed)
        row.pack_end(self.automatic, False, False, 0)
        controls.pack_start(row, False, False, 0)
        idle_row = Gtk.Box(spacing=12)
        idle_row.pack_start(label("After"), False, False, 0)
        self.delay = Gtk.SpinButton.new_with_range(1, MAX_IDLE_MINUTES, 1)
        self.delay.set_value(settings.idle_minutes)
        idle_row.pack_start(self.delay, False, False, 0)
        idle_row.pack_start(label("minutes"), False, False, 0)
        controls.pack_start(idle_row, False, False, 0)
        self.autostart = Gtk.CheckButton(label="Start automatically when I sign in")
        self.autostart.set_active(settings.autostart)
        controls.pack_start(self.autostart, False, False, 0)
        note = label("Cinnamon keeps control of screen locking.\nMandelbot yields when its screensaver starts.", "dim-label")
        note.set_line_wrap(True)
        note.set_max_width_chars(34)
        controls.pack_start(note, False, False, 0)

        preview_column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        columns.pack_start(preview_column, True, True, 0)
        self.frame_label = label("LIVE PREVIEW", "mandelbot-section")
        preview_column.pack_start(self.frame_label, False, False, 0)
        self.gpu_label = label("Starting graphics acceleration…", "dim-label")
        self.gpu_label.set_ellipsize(3)
        preview_column.pack_start(self.gpu_label, False, False, 0)
        self.canvas = FractalCanvas(settings, self.app.report_error, self._frame_ready)
        self.canvas.set_size_request(560, 340)
        frame = Gtk.Frame()
        frame.add(self.canvas)
        preview_column.pack_start(frame, True, True, 0)
        preview_buttons = Gtk.Box(spacing=10)
        self.pause_button = Gtk.Button(label="Pause preview")
        self.pause_button.connect("clicked", self._toggle_pause)
        next_button = Gtk.Button(label="Next region")
        next_button.connect("clicked", lambda button: self.canvas.next_region())
        preview_buttons.pack_start(self.pause_button, False, False, 0)
        preview_buttons.pack_start(next_button, False, False, 0)
        preview_column.pack_start(preview_buttons, False, False, 0)

        footer = Gtk.Box(spacing=12)
        self.status = label("Preview changes are live. Save to keep your preferences.", "dim-label")
        self.status.set_line_wrap(True)
        footer.pack_start(self.status, True, True, 0)
        self.save_button = Gtk.Button(label="Save preferences")
        self.save_button.get_style_context().add_class("suggested-action")
        self.save_button.connect("clicked", self._save)
        footer.pack_end(self.save_button, False, False, 0)
        outer.pack_end(footer, False, False, 0)
        self._automatic_changed()

    def _combo(self, parent, title, choices, selected):
        parent.pack_start(label(title), False, False, 0)
        combo = Gtk.ComboBoxText()
        for choice in choices:
            combo.append(choice, choice)
        combo.set_active_id(selected)
        combo.connect("changed", self._preview_changed)
        parent.pack_start(combo, False, False, 0)
        return combo

    def read_settings(self):
        automatic = self.automatic.get_active()
        return Settings(palette=self.palette.get_active_id(), quality=self.quality.get_active_id(),
            speed=position_to_speed(self.speed.get_value()), idle_minutes=self.delay.get_value_as_int(),
            automatic=automatic, autostart=automatic and self.autostart.get_active())

    def _preview_changed(self, *args):
        if hasattr(self, "canvas"):
            self.canvas.settings = self.read_settings()

    def _automatic_changed(self, *args):
        enabled = self.automatic.get_active()
        self.delay.set_sensitive(enabled)
        self.autostart.set_sensitive(enabled)
        if not enabled:
            self.autostart.set_active(False)

    def _frame_ready(self, name, width, height):
        self.frame_label.set_text(f"LIVE  ·  {name}  ·  {width} × {height}")
        self.gpu_label.set_text(f"GPU · {self.canvas.renderer.name.split(' (')[0]} · Double precision")
        self.gpu_label.set_tooltip_text(self.canvas.renderer.name)

    def _toggle_pause(self, button):
        self.canvas.paused = not self.canvas.paused
        button.set_label("Resume preview" if self.canvas.paused else "Pause preview")

    def _save(self, button):
        try:
            settings = self.read_settings()
            self.app.save_preferences(settings)
            text = "Saved. Automatic mode is running." if settings.automatic else "Preferences saved. Automatic mode is off."
            self.status.set_text(text)
        except Exception as error:
            self.app.report_error(error)
