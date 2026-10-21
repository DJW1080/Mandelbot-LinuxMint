#!/usr/bin/python3
"""Use dbus-run-session --config-file scripts/private-bus.conf for this check."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from gi.repository import Gio, GLib
from mandelbot.desktop import DesktopState, LOCK_SERVICE, LOCK_PATH

APPLICATION_ID = 'org.mandelbot.Screensaver'
TIMEOUT_SECONDS = 10


def wait_until(predicate):
    deadline = time.monotonic() + TIMEOUT_SECONDS
    context = GLib.MainContext.default()
    while not predicate():
        if time.monotonic() > deadline:
            raise TimeoutError('Private-bus verification timed out')
        while context.pending():
            context.iteration(False)
        time.sleep(0.02)


def main():
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    def bus_call(method, parameters):
        return bus.call_sync('org.freedesktop.DBus', '/org/freedesktop/DBus',
            'org.freedesktop.DBus', method, parameters, None,
            Gio.DBusCallFlags.NONE, 2000, None).unpack()[0]
    assert not bus_call('NameHasOwner', GLib.Variant('(s)', (LOCK_SERVICE,))), 'Use a fresh dbus-run-session'
    assert bus_call('RequestName', GLib.Variant('(su)', (LOCK_SERVICE, 4))) == 1
    received = []
    desktop = DesktopState(received.append)
    bus.flush_sync(None)
    bus.emit_signal(None, LOCK_PATH, LOCK_SERVICE, 'ActiveChanged', GLib.Variant('(b)', (True,)))
    wait_until(lambda: received == [True])
    bus.emit_signal(None, LOCK_PATH, LOCK_SERVICE, 'ActiveChanged', GLib.Variant('(b)', (False,)))
    wait_until(lambda: received == [True, False])
    desktop.close()
    results = {'real_dbus_signal_delivery_on_isolated_bus': received}

    with tempfile.TemporaryDirectory(prefix='mandelbot-launcher-') as folder:
        environment = dict(os.environ, XDG_CONFIG_HOME=folder, XDG_STATE_HOME=folder,
                           NO_AT_BRIDGE='1')
        launcher = str(ROOT / 'bin/mandelbot')
        idle_off = subprocess.run([launcher, '--watch'], env=environment, capture_output=True, text=True, timeout=10)
        assert idle_off.returncode == 0, idle_off.stderr
        process = subprocess.Popen([launcher, '--settings'], env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            wait_until(lambda: bus_call('NameHasOwner', GLib.Variant('(s)', (APPLICATION_ID,))))
            second = subprocess.run([launcher, '--settings'], env=environment, capture_output=True, text=True, timeout=10)
            assert second.returncode == 0, second.stderr
            assert process.poll() is None, 'Second launch must reuse the running application'
            stop = subprocess.run([launcher, '--quit'], env=environment, capture_output=True, text=True, timeout=10)
            assert stop.returncode == 0, stop.stderr
            stdout, stderr = process.communicate(timeout=10)
            assert process.returncode == 0, stderr
            assert not stderr.strip(), stderr
            results['real_single_instance_open_and_quit'] = True
            results['watch_disabled_exits_without_background_process'] = True
        finally:
            if process.poll() is None:
                process.terminate()
                process.communicate(timeout=10)
    results['status'] = 'passed'
    (ROOT / 'build/evidence/private-bus-verification.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
