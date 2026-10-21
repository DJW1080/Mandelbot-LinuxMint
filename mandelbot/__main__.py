"""Command-line entry point; version/help work without a display server."""

import argparse
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys

from . import __version__

LOG_MAX_BYTES = 1_000_000


def main(arguments=None):
    arguments = list(sys.argv[1:] if arguments is None else arguments)
    parser = argparse.ArgumentParser(description="Native Mandelbrot journeys for Linux Mint.")
    parser.add_argument("--version", action="version", version=f"Mandelbot {__version__}")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--settings", action="store_true", help="open the settings window (default)")
    modes.add_argument("--fullscreen", action="store_true", help="show the fullscreen fractal")
    modes.add_argument("--watch", action="store_true", help="run idle mode if enabled in saved preferences")
    modes.add_argument("--quit", action="store_true", help="stop this user's running Mandelbot instance")
    parser.parse_args(arguments)
    root = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "mandelbot"
    root.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
        handlers=[RotatingFileHandler(root / "application.log", maxBytes=LOG_MAX_BYTES,
                                     backupCount=1), logging.StreamHandler()])
    from .application import MandelbotApplication
    app = MandelbotApplication()
    result = app.run([sys.argv[0], *arguments])
    return result or app.exit_status


if __name__ == "__main__":
    raise SystemExit(main())
