from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import pygame

from .utils import Vec2, clamp


PADDLE_WIDTH = 18
PADDLE_HEIGHT = 116
PADDLE_SPEED = 660
BALL_RADIUS = 10
BALL_START_SPEED = 430
BALL_SPEEDUP = 1.055
BALL_MAX_SPEED = 1120


@dataclass
class Paddle:
    x: float
    y: float
    controls: tuple[int, int]
    color: tuple[int, int, int] = (0, 225, 255)
    height: float = PADDLE_HEIGHT
    width: float = PADDLE_WIDTH
    velocity: float = 0.0
    rect: pygame.Rect = field(init=False)

    def __post_init__(self) -> None:
        self.rect = pygame.Rect(0, 0, self.width, self.height)
        self.sync_rect()

    def sync_rect(self) -> None:
        self.rect.size = (int(self.width), int(self.height))
        self.rect.center = (round(self.x), round(self.y))

    def update(self, keys: pygame.key.ScancodeWrapper, dt: float, bounds: pygame.Rect) -> None:
        direction = 0
        if keys[self.controls[0]]:
            direction -= 1
        if keys[self.controls[1]]:
            direction += 1
        target = direction * PADDLE_SPEED
        self.velocity += (target - self.velocity) * min(dt * 18, 1)
        self.y += self.velocity * dt
        half = self.height / 2
        self.y = clamp(self.y, bounds.top + half, bounds.bottom - half)
        self.sync_rect()

    def draw(self, surface: pygame.Surface, glow: float) -> None:
        glow_size = int(24 * glow)
        layer = pygame.Surface((self.rect.width + glow_size * 2, self.rect.height + glow_size * 2), pygame.SRCALPHA)
        rect = pygame.Rect(glow_size, glow_size, self.rect.width, self.rect.height)
        pygame.draw.rect(layer, (*self.color, int(48 * glow)), rect.inflate(glow_size, glow_size), border_radius=8)
        pygame.draw.rect(layer, (*self.color, 120), rect.inflate(7, 7), border_radius=7)
        pygame.draw.rect(layer, (*self.color, 255), rect, border_radius=5)
        pygame.draw.rect(layer, (220, 255, 255, 255), rect.inflate(-8, -18), border_radius=3)
        surface.blit(layer, (self.rect.x - glow_size, self.rect.y - glow_size), special_flags=pygame.BLEND_PREMULTIPLIED)


@dataclass
class Ball:
    pos: Vec2
    radius: float = BALL_RADIUS
    vel: Vec2 = field(default_factory=Vec2)
    trail: list[Vec2] = field(default_factory=list)
    last_speed: float = BALL_START_SPEED

    def reset(self, size: tuple[int, int], direction: int | None = None) -> None:
        w, h = size
        self.pos = Vec2(w / 2, h / 2)
        angle = random.uniform(-0.42, 0.42)
        if direction is None:
            direction = random.choice((-1, 1))
        self.last_speed = BALL_START_SPEED
        self.vel = Vec2(math.cos(angle) * direction, math.sin(angle)) * self.last_speed
        self.trail.clear()

    @property
    def speed(self) -> float:
        return self.vel.length()

    def update(self, dt: float) -> None:
        self.trail.append(Vec2(self.pos))
        if len(self.trail) > 18:
            self.trail.pop(0)
        self.pos += self.vel * dt

    def bounce_wall(self, top: float, bottom: float) -> bool:
        if self.pos.y - self.radius <= top:
            self.pos.y = top + self.radius
            self.vel.y = abs(self.vel.y)
            return True
        if self.pos.y + self.radius >= bottom:
            self.pos.y = bottom - self.radius
            self.vel.y = -abs(self.vel.y)
            return True
        return False

    def collide_paddle(self, paddle: Paddle, previous: Vec2) -> bool:
        rect = paddle.rect.inflate(0, 10)
        moving_right = self.vel.x > 0
        crossing = (
            moving_right
            and previous.x + self.radius <= rect.left
            and self.pos.x + self.radius >= rect.left
        ) or (
            not moving_right
            and previous.x - self.radius >= rect.right
            and self.pos.x - self.radius <= rect.right
        )
        overlaps_y = self.pos.y + self.radius >= rect.top and self.pos.y - self.radius <= rect.bottom
        if not (crossing and overlaps_y):
            return False

        offset = clamp((self.pos.y - paddle.y) / (paddle.height / 2), -1, 1)
        max_angle = math.radians(64)
        angle = offset * max_angle
        speed = min(max(self.speed, BALL_START_SPEED) * BALL_SPEEDUP, BALL_MAX_SPEED)
        spin = clamp(paddle.velocity / PADDLE_SPEED, -1, 1) * 145
        direction = 1 if not moving_right else -1
        self.vel.x = math.cos(angle) * speed * direction
        self.vel.y = math.sin(angle) * speed + spin
        if self.vel.length() > BALL_MAX_SPEED:
            self.vel.scale_to_length(BALL_MAX_SPEED)
        if moving_right:
            self.pos.x = rect.left - self.radius
        else:
            self.pos.x = rect.right + self.radius
        self.last_speed = self.speed
        return True

    def draw(self, surface: pygame.Surface, glow: float) -> None:
        for index, point in enumerate(self.trail):
            alpha = int(18 + 130 * (index / max(len(self.trail), 1)))
            radius = int(self.radius * (0.5 + index / max(len(self.trail), 1)))
            pygame.draw.circle(surface, (0, 230, 255, alpha), point, radius)
        glow_radius = int(self.radius * (5.8 * glow))
        layer = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
        center = (glow_radius, glow_radius)
        pygame.draw.circle(layer, (0, 220, 255, int(48 * glow)), center, glow_radius)
        pygame.draw.circle(layer, (255, 44, 214, int(70 * glow)), center, int(glow_radius * 0.55))
        pygame.draw.circle(layer, (230, 255, 255, 255), center, int(self.radius))
        surface.blit(layer, self.pos - Vec2(center), special_flags=pygame.BLEND_PREMULTIPLIED)
