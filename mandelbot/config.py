"""Validated user preferences, stored atomically in the XDG config directory."""

from dataclasses import asdict, dataclass, fields
import json
import math
import os
from pathlib import Path
import tempfile

from .quality import QUALITY, MIN_SPEED, MAX_SPEED
from .palettes import PALETTES

MIN_IDLE_MINUTES, MAX_IDLE_MINUTES = 1, 60


@dataclass(frozen=True)
class Settings:
    palette: str = "Aurora"
    quality: str = "Ultra"
    speed: float = 1.0
    idle_minutes: int = 2
    automatic: bool = False
    autostart: bool = False

    def __post_init__(self):
        if self.palette not in PALETTES or self.quality not in QUALITY:
            raise ValueError("Choose one of the available palettes and quality levels.")
        if (type(self.speed) not in (int, float) or not math.isfinite(self.speed)
                or not MIN_SPEED <= self.speed <= MAX_SPEED):
            raise ValueError(f"Journey speed must be between {MIN_SPEED} and {MAX_SPEED}.")
        if type(self.idle_minutes) is not int or not MIN_IDLE_MINUTES <= self.idle_minutes <= MAX_IDLE_MINUTES:
            raise ValueError("Idle delay must be a whole number from 1 to 60 minutes.")
        if type(self.automatic) is not bool:
            raise ValueError("Automatic activation must be true or false.")
        if type(self.autostart) is not bool:
            raise ValueError("Login startup must be true or false.")
        if self.autostart and not self.automatic:
            raise ValueError("Enable automatic activation before enabling login startup.")


def settings_path():
    root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / "mandelbot/settings.json"


def load_settings(path=None):
    path = Path(path) if path is not None else settings_path()
    if not path.exists():
        return Settings()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeError) as error:
        raise ValueError(f"Cannot read settings in {path}: {error}") from error
    if not isinstance(data, dict) or set(data) - {field.name for field in fields(Settings)}:
        raise ValueError(f"Unsupported settings in {path}; the file has been preserved.")
    try:
        return Settings(**data)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid settings in {path}: {error}") from error


def save_settings(settings, path=None):
    path = Path(path) if path is not None else settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".settings-", delete=False) as output:
            temporary_path = Path(output.name)
            json.dump(asdict(settings), output, indent=2, allow_nan=False)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        temporary_path.replace(path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
