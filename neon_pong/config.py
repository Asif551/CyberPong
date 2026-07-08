from __future__ import annotations

from dataclasses import dataclass, asdict
import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
ASSET_DIR = ROOT_DIR / "assets"
GENERATED_ASSET_DIR = ASSET_DIR / "generated"
SETTINGS_PATH = ROOT_DIR / "settings.json"


RESOLUTIONS = [(960, 540), (1280, 720), (1600, 900), (1920, 1080)]


@dataclass
class Settings:
    resolution_index: int = 1
    fullscreen: bool = False
    fps_limit: int = 144
    music_volume: float = 0.45
    sfx_volume: float = 0.75
    glow_intensity: float = 1.0
    winning_score: int = 7
    vsync: bool = True
    show_fps: bool = True
    show_ball_speed: bool = True

    @property
    def resolution(self) -> tuple[int, int]:
        return RESOLUTIONS[self.resolution_index % len(RESOLUTIONS)]


class SettingsManager:
    def __init__(self, path: Path = SETTINGS_PATH) -> None:
        self.path = path
        self.settings = self.load()

    def load(self) -> Settings:
        if not self.path.exists():
            return Settings()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            valid = {field: raw[field] for field in Settings.__dataclass_fields__ if field in raw}
            settings = Settings(**valid)
            settings.resolution_index %= len(RESOLUTIONS)
            settings.fps_limit = min(max(int(settings.fps_limit), 60), 240)
            settings.music_volume = min(max(float(settings.music_volume), 0.0), 1.0)
            settings.sfx_volume = min(max(float(settings.sfx_volume), 0.0), 1.0)
            settings.glow_intensity = min(max(float(settings.glow_intensity), 0.25), 2.0)
            settings.winning_score = min(max(int(settings.winning_score), 3), 21)
            return settings
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return Settings()

    def save(self) -> None:
        self.path.write_text(json.dumps(asdict(self.settings), indent=2), encoding="utf-8")
