"""X11 idle observation and the installed Cinnamon public D-Bus interfaces."""

import ctypes
import os

from gi.repository import Gio, GLib

MILLISECONDS_PER_SECOND = 1000.0
DBUS_TIMEOUT_MS = 1500
IDLE_INHIBITOR_FLAG = 8
LOCK_SERVICE = "org.cinnamon.ScreenSaver"
LOCK_PATH = "/org/cinnamon/ScreenSaver"
SESSION_SERVICE = "org.gnome.SessionManager"
SESSION_PATH = "/org/gnome/SessionManager"


class XScreenSaverInfo(ctypes.Structure):
    _fields_ = [("window", ctypes.c_ulong), ("state", ctypes.c_int),
                ("kind", ctypes.c_int), ("til_or_since", ctypes.c_ulong),
                ("idle", ctypes.c_ulong), ("event_mask", ctypes.c_ulong)]


class IdleClock:
    def __init__(self):
        if os.environ.get("XDG_SESSION_TYPE") == "wayland":
            raise RuntimeError("Automatic mode requires a Cinnamon X11 session. Manual preview remains available.")
        self.x11 = ctypes.CDLL("libX11.so.6")
        self.xss = ctypes.CDLL("libXss.so.1")
        self.x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        self.x11.XOpenDisplay.restype = ctypes.c_void_p
        self.x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
        self.x11.XDefaultRootWindow.restype = ctypes.c_ulong
        self.x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
        self.x11.XCloseDisplay.restype = ctypes.c_int
        self.xss.XScreenSaverQueryExtension.argtypes = [ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)]
        self.xss.XScreenSaverQueryExtension.restype = ctypes.c_int
        self.xss.XScreenSaverQueryInfo.argtypes = [ctypes.c_void_p, ctypes.c_ulong,
                                                  ctypes.POINTER(XScreenSaverInfo)]
        self.xss.XScreenSaverQueryInfo.restype = ctypes.c_int
        self.display = self.x11.XOpenDisplay(None)
        if not self.display:
            raise RuntimeError("Cannot connect to the X11 display for idle detection.")
        event, error = ctypes.c_int(), ctypes.c_int()
        if not self.xss.XScreenSaverQueryExtension(self.display, ctypes.byref(event), ctypes.byref(error)):
            self.close()
            raise RuntimeError("The X11 server does not provide the XScreenSaver idle extension.")
        self.root = self.x11.XDefaultRootWindow(self.display)

    def seconds(self):
        information = XScreenSaverInfo()
        if not self.xss.XScreenSaverQueryInfo(self.display, self.root, ctypes.byref(information)):
            raise RuntimeError("The X11 server could not report idle time.")
        return information.idle / MILLISECONDS_PER_SECOND

    def close(self):
        if self.display:
            self.x11.XCloseDisplay(self.display)
            self.display = None


class DesktopState:
    def __init__(self, on_active):
        self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        self.subscription = self.bus.signal_subscribe(LOCK_SERVICE, LOCK_SERVICE,
            "ActiveChanged", LOCK_PATH, None, Gio.DBusSignalFlags.NONE,
            lambda connection, sender, path, interface, signal, parameters:
                on_active(parameters.unpack()[0]))

    def _call(self, service, path, method, parameters=None):
        return self.bus.call_sync(service, path, service, method, parameters, None,
            Gio.DBusCallFlags.NONE, DBUS_TIMEOUT_MS, None).unpack()[0]

    def active(self):
        # D-Bus may start Cinnamon's existing service; this never requests a lock.
        return bool(self._call(LOCK_SERVICE, LOCK_PATH, "GetActive"))

    def inhibited(self):
        return bool(self._call(SESSION_SERVICE, SESSION_PATH, "IsInhibited",
                              GLib.Variant("(u)", (IDLE_INHIBITOR_FLAG,))))

    def close(self):
        if self.subscription:
            self.bus.signal_unsubscribe(self.subscription)
            self.subscription = None
