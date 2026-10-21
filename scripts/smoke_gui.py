#!/usr/bin/python3
"""Exercise real GTK rendering and desktop handoff in an isolated config directory.

Only activate Cinnamon's visual screensaver when password locking is already off;
otherwise skip that live handoff check. Never change the user's lock preferences.
"""

import argparse
from dataclasses import replace
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import traceback

PROJECT = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser()
parser.add_argument('--application-root', type=Path, default=PROJECT)
parser.add_argument('--output', type=Path, default=PROJECT / 'build/evidence')
options = parser.parse_args()
sys.path.insert(0, str(options.application_root))

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, Gio, GLib, Gtk
from mandelbot.application import MandelbotApplication
from mandelbot.config import load_settings, PALETTES
from mandelbot.quality import speed_to_position
from mandelbot.integration import autostart_path
from mandelbot.desktop import LOCK_PATH, LOCK_SERVICE

CHECK_TIMEOUT_SECONDS = 15
TICK_MS = 50


def capture(widget, destination):
    window = widget.get_window()
    pixels = Gdk.pixbuf_get_from_window(window, 0, 0, window.get_width(), window.get_height())
    if pixels is None:
        raise AssertionError('The native window could not be captured')
    pixels.savev(str(destination), 'png', [], [])


def canvas_pixels(canvas):
    canvas.make_current()
    canvas.attach_buffers()
    return canvas.renderer.read_pixels(*canvas.frame_size)


def main():
    options.output.mkdir(parents=True, exist_ok=True)
    results = {}
    failures = []
    temporary = tempfile.TemporaryDirectory(prefix='mandelbot-gui-')
    os.environ['XDG_CONFIG_HOME'] = temporary.name
    os.environ['XDG_STATE_HOME'] = temporary.name
    app = MandelbotApplication()
    app.set_flags(Gio.ApplicationFlags.NON_UNIQUE)
    locker_settings = Gio.Settings.new('org.cinnamon.desktop.screensaver')
    session_settings = Gio.Settings.new('org.cinnamon.desktop.session')
    before = {key: locker_settings.get_value(key).unpack() for key in
              ['idle-activation-enabled', 'lock-enabled', 'lock-delay']}
    before['idle-delay'] = session_settings.get_value('idle-delay').unpack()
    screensaver_activated = False

    def set_screensaver(active):
        app.desktop.bus.call_sync(LOCK_SERVICE, LOCK_PATH, LOCK_SERVICE, 'SetActive',
            GLib.Variant('(b)', (active,)), None, Gio.DBusCallFlags.NONE, 5000, None)

    def steps():
        nonlocal screensaver_activated
        yield lambda: app.window is not None and app.window.canvas.frame_count > 0
        window = app.window
        first_frame = window.canvas.frame_count
        first_pixels = canvas_pixels(window.canvas)
        yield lambda: window.canvas.frame_count > first_frame + 1
        assert canvas_pixels(window.canvas) != first_pixels
        results['animated_native_preview'] = True
        results['gpu_renderer'] = window.canvas.renderer.name
        window.palette.set_active_id('Ember')
        window.quality.set_active_id('Eco')
        window.speed.set_value(speed_to_position(1.3))
        assert window.canvas.settings.palette == 'Ember'
        window.save_button.clicked()
        assert load_settings().palette == 'Ember'
        assert abs(load_settings().speed - 1.3) < 1e-10
        assert not load_settings().automatic
        results['settings_save_and_live_changes'] = True
        window.pause_button.clicked()
        assert window.canvas.paused
        pause_elapsed = window.canvas.elapsed
        pause_start = time.monotonic()
        yield lambda: time.monotonic() - pause_start > 0.3
        assert window.canvas.elapsed == pause_elapsed
        # Changing controls while paused must still refresh the GPU image.
        frame_before_change = window.canvas.frame_count
        window.palette.set_active_id('Ocean')
        yield lambda: window.canvas.frame_count > frame_before_change and window.canvas.renderer.settled
        theme_frames = set()
        for name in PALETTES:
            window.palette.set_active_id(name)
            yield lambda: (window.canvas.renderer.settled
                           and window.canvas.renderer.front.settings.palette == name)
            pixels = canvas_pixels(window.canvas)
            assert pixels not in theme_frames, f'{name} did not change the preview'
            theme_frames.add(pixels)
            window.save_button.clicked()
            assert load_settings().palette == name
        results['all_themes_select_render_and_save'] = list(PALETTES)
        window.pause_button.clicked()
        assert not window.canvas.paused
        window.speed.set_value(speed_to_position(0.01))
        window.save_button.clicked()
        assert load_settings().speed == 0.01
        start_elapsed, start_time = window.canvas.elapsed, time.monotonic()
        yield lambda: time.monotonic() - start_time > 1.0
        measured_speed = (window.canvas.elapsed - start_elapsed) / (time.monotonic() - start_time)
        assert 0.008 < measured_speed < 0.012, measured_speed
        results['measured_minimum_journey_speed'] = measured_speed
        results['paused_controls_redraw_without_motion'] = True
        # Return to the default palette for the user-facing screenshot.
        window.palette.set_active_id('Aurora')
        window.quality.set_active_id('Ultra')
        screenshot_frame = window.canvas.frame_count
        yield lambda: window.canvas.frame_count > screenshot_frame and window.canvas.renderer.front.settings == window.canvas.settings
        assert window.canvas.frame_size == (window.canvas.get_allocated_width() * window.canvas.get_scale_factor(),
                                            window.canvas.get_allocated_height() * window.canvas.get_scale_factor())
        capture(window, options.output / 'settings-window.png')

        app.show_fullscreen(window.read_settings())
        yield lambda: app.session is not None and all(canvas.frame_count > 0 for canvas in app.session.canvases)
        fullscreen = app.session.windows[0]
        yield lambda: bool(fullscreen.get_window().get_state() & Gdk.WindowState.FULLSCREEN)
        capture(fullscreen, options.output / 'fullscreen.png')
        results['fullscreen_physical_pixels'] = list(app.session.canvases[0].frame_size)
        live_canvas = app.session.canvases[0]
        start_frame, start_time = live_canvas.frame_count, time.monotonic()
        yield lambda: time.monotonic() - start_time > 3.0
        results['fullscreen_presentation_fps'] = (live_canvas.frame_count - start_frame) / (time.monotonic() - start_time)
        assert results['fullscreen_presentation_fps'] > 15, results['fullscreen_presentation_fps']
        results['fullscreen_completed_detail_frames'] = live_canvas.renderer.detail_frames
        results['native_fullscreen_windows'] = len(app.session.windows)
        event = Gdk.Event.new(Gdk.EventType.KEY_PRESS)
        event.keyval = Gdk.KEY_Escape
        event.window = fullscreen.get_window()
        fullscreen.emit('key-press-event', event)
        yield lambda: app.session is None and window.get_visible()
        results['fullscreen_escape_dismissal'] = True

        window.automatic.set_active(True)
        window.autostart.set_active(True)
        window.save_button.clicked()
        assert app.watcher is not None and load_settings().autostart
        assert Gio.DesktopAppInfo.new_from_filename(str(autostart_path())) is not None
        window.automatic.set_active(False)
        window.save_button.clicked()
        assert app.watcher is None and not autostart_path().exists()
        assert not load_settings().automatic
        results['settings_idle_and_login_opt_in_and_removal'] = True

        app.show_fullscreen(window.read_settings())
        yield lambda: app.session is not None and app.session.canvases[0].frame_count > 0
        app._desktop_changed(True)
        yield lambda: app.session is None
        results['simulated_cinnamon_active_signal_dismissal'] = True

        automatic = replace(window.read_settings(), automatic=True)
        app.start_watcher(automatic)
        results['real_x11_idle_seconds'] = app.watcher.clock.seconds()
        results['cinnamon_active_before'] = app.desktop.active()
        results['session_idle_inhibited'] = app.desktop.inhibited()
        if results['session_idle_inhibited']:
            results['real_idle_activation'] = 'skipped: a desktop inhibitor is active'
        else:
            # Shorten only the in-memory test policy; persisted user preferences stay untouched.
            app.watcher.policy.threshold_seconds = 0.05
            yield lambda: app.session is not None and app.session.canvases[0].frame_count > 0
            results['real_idle_activation'] = True
            if not before['lock-enabled'] and not results['cinnamon_active_before']:
                screensaver_activated = True
                set_screensaver(True)
                yield lambda: app.session is None and app.desktop.active()
                results['live_cinnamon_handoff_without_password_lock'] = True
                app.stop_watcher()
                set_screensaver(False)
                screensaver_activated = False
                yield lambda: not app.desktop.active()
            else:
                results['live_cinnamon_handoff_without_password_lock'] = 'skipped: password locking is enabled or desktop was active'
        app.stop_fullscreen()
        app.stop_watcher()
        after = {key: locker_settings.get_value(key).unpack() for key in
                 ['idle-activation-enabled', 'lock-enabled', 'lock-delay']}
        after['idle-delay'] = session_settings.get_value('idle-delay').unpack()
        assert before == after, 'Desktop settings must not change'
        assert app.exit_status == 0, 'The app reported a runtime error'
        results['desktop_settings_unchanged'] = before
        results['status'] = 'passed'

    sequence = steps()
    waiting = None
    deadline = time.monotonic() + CHECK_TIMEOUT_SECONDS

    def tick():
        nonlocal waiting, deadline
        try:
            if app.exit_status:
                raise AssertionError('The application reported an error during GUI verification')
            if waiting is not None and not waiting():
                if time.monotonic() >= deadline:
                    canvas = app.window.canvas if app.window else None
                    state = {'wait_line': waiting.__code__.co_firstlineno,
                             'session_open': app.session is not None,
                             'desktop_active': app.desktop.active() if app.desktop else None}
                    if canvas and canvas.renderer:
                        state.update(frame_count=canvas.frame_count, size=canvas.frame_size,
                                     paused=canvas.paused, mapped=canvas.get_mapped(),
                                     next_row=canvas.renderer.next_row,
                                     front_settings=str(canvas.renderer.front.settings),
                                     desired_settings=str(canvas.settings))
                    raise TimeoutError(f'A GUI verification condition did not complete: {state}')
                return GLib.SOURCE_CONTINUE
            waiting = next(sequence)
            deadline = time.monotonic() + CHECK_TIMEOUT_SECONDS
        except StopIteration:
            app.quit()
            return GLib.SOURCE_REMOVE
        except Exception:
            failures.append(traceback.format_exc())
            if screensaver_activated and app.desktop is not None:
                set_screensaver(False)
            app.quit()
            return GLib.SOURCE_REMOVE
        return GLib.SOURCE_CONTINUE

    app.connect('activate', lambda application: GLib.timeout_add(TICK_MS, tick))
    app.run(['mandelbot-gui-verification'])
    temporary.cleanup()
    results['errors'] = failures
    (options.output / 'gui-verification.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(results, indent=2))
    return 1 if failures or app.exit_status else 0


if __name__ == '__main__':
    raise SystemExit(main())
