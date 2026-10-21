"""Frame-clock-driven OpenGL canvas at physical display resolution."""

import time

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from .progressive import ProgressiveRenderer
from .quality import physical_dimensions
from .tour import sample, REGION_SECONDS

PALETTE_CYCLE_SECONDS = 160.0
FRAME_INTERVAL_SECONDS = 1.0 / 30.0
FRAME_CLOCK_TOLERANCE_SECONDS = 0.002
INITIAL_JOURNEY_SECONDS = 2.0
STATUS_INTERVAL_SECONDS = 0.5


class FractalCanvas(Gtk.GLArea):
    def __init__(self, settings, on_error, on_frame=None):
        super().__init__()
        self.settings = settings
        self.on_error = on_error
        self.on_frame = on_frame
        self.renderer = None
        self.elapsed = INITIAL_JOURNEY_SECONDS
        self.paused = False
        self.closed = False
        self.failed = False
        self.frame_count = 0
        self.frame_size = (0, 0)
        self.previous_tick = time.monotonic()
        self.next_frame_deadline = self.previous_tick
        self.previous_status = 0.0
        self.last_render_state = None
        self.set_required_version(4, 0)
        self.set_use_es(False)
        self.set_auto_render(False)
        self.set_has_depth_buffer(False)
        self.set_has_stencil_buffer(False)
        self.connect("realize", self._realize)
        self.connect("unrealize", self._unrealize)
        self.connect("render", self._render)
        self.connect("destroy", lambda widget: self.close())
        self.connect("map", self._mapped)
        self.tick_id = self.add_tick_callback(self._tick)

    def _mapped(self, widget):
        # Hidden previews must resume where they stopped, without a time jump.
        self.previous_tick = time.monotonic()

    def next_region(self):
        self.elapsed = (int(self.elapsed / REGION_SECONDS) + 1) * REGION_SECONDS + INITIAL_JOURNEY_SECONDS
        self.queue_render()

    def _realize(self, widget):
        try:
            self.make_current()
            if self.get_error():
                raise RuntimeError(f"Cannot create the OpenGL 4.0 context: {self.get_error().message}")
            self.renderer = ProgressiveRenderer()
        except Exception as error:
            self._fail(error)

    def _unrealize(self, widget):
        if self.renderer is not None:
            self.make_current()
            if not self.get_error():
                self.renderer.close()
            self.renderer = None

    def _fail(self, error):
        self.failed = True
        # Reporting outside rendering lets the application close fullscreen safely.
        GLib.idle_add(self._report_failure, error)

    def _report_failure(self, error):
        if not self.closed:
            self.on_error(error)
        return GLib.SOURCE_REMOVE

    def _state(self):
        return (self.settings, self.elapsed, self.get_allocated_width(),
                self.get_allocated_height(), self.get_scale_factor())

    def _tick(self, widget, frame_clock):
        now = time.monotonic()
        if not self.paused and self.get_mapped():
            self.elapsed += (now - self.previous_tick) * self.settings.speed
        self.previous_tick = now
        changed = self.last_render_state != self._state() or (self.renderer is not None and not self.renderer.settled)
        if (not self.closed and not self.failed and changed
                and now + FRAME_CLOCK_TOLERANCE_SECONDS >= self.next_frame_deadline):
            self.queue_render()
            # An anchored deadline avoids halving a 30 Hz clock due to tiny jitter.
            self.next_frame_deadline += FRAME_INTERVAL_SECONDS
            if self.next_frame_deadline < now:
                self.next_frame_deadline = now + FRAME_INTERVAL_SECONDS
        return GLib.SOURCE_CONTINUE

    def _render(self, widget, context):
        if self.closed or self.failed or self.renderer is None:
            return True
        try:
            width, height = physical_dimensions(self.get_allocated_width(),
                self.get_allocated_height(), self.get_scale_factor())
            view = sample(self.elapsed, 1.0)
            self.renderer.draw(width, height, view, self.settings, self.elapsed / PALETTE_CYCLE_SECONDS)
            if self.renderer.ready:
                self.frame_count += 1
            self.frame_size = width, height
            self.last_render_state = self._state()
            now = time.monotonic()
            if self.on_frame and now - self.previous_status >= STATUS_INTERVAL_SECONDS:
                self.on_frame(view.name, width, height)
                self.previous_status = now
        except Exception as error:
            self._fail(error)
        return True

    def close(self):
        if self.closed:
            return
        self.closed = True
        if self.tick_id:
            self.remove_tick_callback(self.tick_id)
            self.tick_id = None
