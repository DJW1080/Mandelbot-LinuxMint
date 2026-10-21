"""User-owned login integration; never changes Cinnamon lock or power settings."""

import os
from pathlib import Path
import tempfile


def launcher_path():
    root = Path(__file__).resolve().parent.parent
    source_launcher = root / "bin/mandelbot"
    return source_launcher if source_launcher.is_file() else root.parent.parent / "bin/mandelbot"


def autostart_path():
    root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / "autostart/mandelbot.desktop"


def desktop_command(executable):
    path = str(executable)
    if any(character in path for character in "\n\r"):
        raise ValueError("The application path cannot contain a newline.")
    path = path.replace("%", "%%")
    quoted = '"' + ''.join('\\' + char if char in '\\"`$' else char for char in path) + '"'
    # GLib checks the executable before expanding desktop-entry percent codes.
    # A stable interpreter keeps the user-owned script path in the argument list,
    # where %% is expanded correctly at launch, including paths containing %.
    return '/usr/bin/python3 ' + quoted.replace('\\', '\\\\') + " --watch"


def write_autostart(enabled, executable=None, path=None):
    path = Path(path) if path is not None else autostart_path()
    if not enabled:
        path.unlink(missing_ok=True)
        return
    command = desktop_command(executable or launcher_path())
    content = ("[Desktop Entry]\nType=Application\nName=Mandelbot\n"
               "Comment=Start the Mandelbot idle watcher\n"
               f"Exec={command}\nIcon=mandelbot\nTerminal=false\n"
               "OnlyShowIn=X-Cinnamon;\nX-GNOME-Autostart-enabled=true\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".mandelbot-", delete=False) as output:
            temporary = Path(output.name)
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
