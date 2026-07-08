from __future__ import annotations

import math
import wave
from array import array
from pathlib import Path

import pygame

from .config import GENERATED_ASSET_DIR, Settings


class AudioManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.enabled = False
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self.ensure_assets()
        try:
            pygame.mixer.pre_init(44100, -16, 2, 512)
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self.enabled = True
            self.load()
        except pygame.error:
            self.enabled = False

    def ensure_assets(self) -> None:
        GENERATED_ASSET_DIR.mkdir(parents=True, exist_ok=True)
        specs = {
            "paddle.wav": (180, 660, 0.10, "zap"),
            "wall.wav": (360, 210, 0.08, "ping"),
            "score.wav": (130, 55, 0.42, "fall"),
            "countdown.wav": (520, 520, 0.09, "beep"),
            "menu.wav": (740, 420, 0.07, "blip"),
            "victory.wav": (220, 880, 0.85, "rise"),
            "music.wav": (70, 110, 8.0, "music"),
        }
        for name, spec in specs.items():
            path = GENERATED_ASSET_DIR / name
            if not path.exists():
                self.write_wave(path, *spec)

    def write_wave(self, path: Path, start_hz: float, end_hz: float, duration: float, mode: str) -> None:
        sample_rate = 44100
        frames = int(sample_rate * duration)
        data = array("h")
        for i in range(frames):
            t = i / sample_rate
            p = i / max(frames - 1, 1)
            if mode == "music":
                beat = int(t * 2) % 8
                root = [55, 65.41, 73.42, 82.41][beat // 2]
                lead = [220, 277.18, 329.63, 440][beat % 4]
                value = (
                    math.sin(2 * math.pi * root * t) * 0.35
                    + math.sin(2 * math.pi * root * 2 * t) * 0.18
                    + math.sin(2 * math.pi * lead * t) * 0.10 * (0.5 + 0.5 * math.sin(2 * math.pi * 4 * t))
                )
                env = 0.65
            else:
                hz = start_hz + (end_hz - start_hz) * p
                if mode == "zap":
                    value = math.sin(2 * math.pi * hz * t) + 0.35 * math.sin(2 * math.pi * hz * 2.01 * t)
                elif mode == "blip":
                    value = math.sin(2 * math.pi * hz * t)
                elif mode == "rise":
                    value = math.sin(2 * math.pi * hz * t) + 0.25 * math.sin(2 * math.pi * hz * 1.5 * t)
                else:
                    value = math.sin(2 * math.pi * hz * t)
                env = (1.0 - p) ** 1.7
                if mode == "rise":
                    env = min(p * 4, 1.0) * (1.0 - p * 0.35)
            sample = int(max(-1, min(1, value * env)) * 21000)
            data.extend((sample, sample))
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(2)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(data.tobytes())

    def load(self) -> None:
        for key in ("paddle", "wall", "score", "countdown", "menu", "victory"):
            self.sounds[key] = pygame.mixer.Sound(str(GENERATED_ASSET_DIR / f"{key}.wav"))
        self.apply_volumes()
        pygame.mixer.music.load(str(GENERATED_ASSET_DIR / "music.wav"))
        pygame.mixer.music.set_volume(self.settings.music_volume)

    def apply_volumes(self) -> None:
        if not self.enabled:
            return
        for sound in self.sounds.values():
            sound.set_volume(self.settings.sfx_volume)
        pygame.mixer.music.set_volume(self.settings.music_volume)

    def play_music(self) -> None:
        if self.enabled and not pygame.mixer.music.get_busy():
            pygame.mixer.music.play(-1, fade_ms=800)

    def play(self, name: str) -> None:
        if self.enabled and name in self.sounds:
            self.sounds[name].play()
