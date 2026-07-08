from __future__ import annotations

import math
import random
from typing import Iterable

import pygame


Vec2 = pygame.math.Vector2


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * clamp(t, 0.0, 1.0)


def ease_out_back(t: float) -> float:
    t = clamp(t, 0.0, 1.0) - 1.0
    c1 = 1.70158
    c3 = c1 + 1.0
    return 1.0 + c3 * t * t * t + c1 * t * t


def ease_out_cubic(t: float) -> float:
    return 1.0 - pow(1.0 - clamp(t, 0.0, 1.0), 3)


def draw_text(
    surface: pygame.Surface,
    text: str,
    font: pygame.font.Font,
    color: pygame.Color | tuple[int, int, int],
    center: tuple[float, float],
    glow: bool = False,
    glow_color: tuple[int, int, int] = (0, 220, 255),
    alpha: int = 255,
) -> pygame.Rect:
    if glow:
        for radius, opacity in ((8, 35), (4, 60), (2, 90)):
            image = font.render(text, True, glow_color)
            image.set_alpha(min(opacity, alpha))
            rect = image.get_rect(center=center)
            for dx, dy in ring_offsets(radius):
                surface.blit(image, rect.move(dx, dy))
    image = font.render(text, True, color)
    image.set_alpha(alpha)
    rect = image.get_rect(center=center)
    surface.blit(image, rect)
    return rect


def ring_offsets(radius: int) -> Iterable[tuple[int, int]]:
    for angle in range(0, 360, 45):
        yield int(math.cos(math.radians(angle)) * radius), int(math.sin(math.radians(angle)) * radius)


def random_neon() -> tuple[int, int, int]:
    return random.choice([(0, 230, 255), (20, 120, 255), (255, 44, 214), (120, 255, 230)])
