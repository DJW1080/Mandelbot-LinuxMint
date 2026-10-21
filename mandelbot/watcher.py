"""A bounded, opt-in idle watcher which honours Cinnamon's inhibitors."""

from gi.repository import GLib

from .desktop import IdleClock
from .lifecycle import IdlePolicy

POLL_SECONDS = 1
SECONDS_PER_MINUTE = 60


class IdleWatcher:
    def __init__(self, settings, desktop, on_start, on_stop, on_error):
        self.desktop = desktop
        self.clock = IdleClock()
        self.policy = IdlePolicy(settings.idle_minutes * SECONDS_PER_MINUTE)
        self.on_start, self.on_stop, self.on_error = on_start, on_stop, on_error
        self.timer = GLib.timeout_add_seconds(POLL_SECONDS, self.poll)

    def poll(self):
        try:
            blocked = self.desktop.active() or self.desktop.inhibited()
            action = self.policy.evaluate(self.clock.seconds(), blocked)
            if action == "start":
                self.on_start()
            elif action == "stop":
                self.on_stop()
        except Exception as error:
            self.timer = None
            self.on_stop()
            self.on_error(error)
            return GLib.SOURCE_REMOVE
        return GLib.SOURCE_CONTINUE

    def dismiss(self):
        self.policy.dismiss()

    def close(self):
        if self.timer:
            GLib.source_remove(self.timer)
            self.timer = None
        self.clock.close()
