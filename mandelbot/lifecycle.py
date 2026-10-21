"""Desktop-independent idle policy; unknown lock state always suppresses visuals."""

from dataclasses import dataclass


@dataclass
class IdlePolicy:
    threshold_seconds: float
    running: bool = False
    armed: bool = True

    def dismiss(self):
        self.running = False
        self.armed = False

    def evaluate(self, idle_seconds, desktop_active):
        if desktop_active is not False:
            self.armed = False
            return self._stop()
        if idle_seconds < self.threshold_seconds:
            self.armed = True
            return self._stop()
        if self.armed and not self.running:
            self.running = True
            return "start"
        return "wait"

    def _stop(self):
        if self.running:
            self.running = False
            return "stop"
        return "wait"
