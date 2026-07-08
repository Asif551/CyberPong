from __future__ import annotations

import random
from dataclasses import dataclass

import pygame

from .utils import Vec2, clamp, random_neon


@dataclass
class Particle:
    pos: Vec2
    vel: Vec2
    color: tuple[int, int, int]
    life: float
    max_life: float
    radius: float

    def update(self, dt: float) -> None:
        self.life -= dt
        self.pos += self.vel * dt
        self.vel *= 1.0 - min(dt * 1.8, 0.45)

    def draw(self, surface: pygame.Surface, glow: float) -> None:
        if self.life <= 0:
            return
        alpha = int(255 * clamp(self.life / self.max_life, 0, 1))
        radius = max(1, int(self.radius * (0.65 + self.life / self.max_life)))
        layer = pygame.Surface((radius * 8, radius * 8), pygame.SRCALPHA)
        center = (layer.get_width() // 2, layer.get_height() // 2)
        pygame.draw.circle(layer, (*self.color, int(55 * glow)), center, radius * 4)
        pygame.draw.circle(layer, (*self.color, alpha), center, radius)
        surface.blit(layer, self.pos - Vec2(center))


class ParticleSystem:
    def __init__(self) -> None:
        self.particles: list[Particle] = []
        self.background: list[Particle] = []

    def seed_background(self, size: tuple[int, int], count: int = 80) -> None:
        self.background.clear()
        w, h = size
        for _ in range(count):
            pos = Vec2(random.uniform(0, w), random.uniform(0, h))
            vel = Vec2(random.uniform(-8, 8), random.uniform(8, 28))
            self.background.append(Particle(pos, vel, random_neon(), 99, 99, random.uniform(1, 2.5)))

    def burst(self, pos: Vec2, direction: Vec2, amount: int = 32) -> None:
        base_angle = direction.angle_to(Vec2(1, 0)) if direction.length_squared() else 0
        for _ in range(amount):
            angle = -base_angle + random.uniform(-55, 55)
            speed = random.uniform(120, 520)
            vel = Vec2(speed, 0).rotate(angle)
            self.particles.append(
                Particle(Vec2(pos), vel, random_neon(), random.uniform(0.25, 0.65), 0.65, random.uniform(2, 5))
            )

    def goal_ring(self, pos: Vec2, amount: int = 90) -> None:
        for i in range(amount):
            angle = i * (360 / amount)
            vel = Vec2(random.uniform(110, 480), 0).rotate(angle)
            self.particles.append(
                Particle(Vec2(pos), vel, random_neon(), random.uniform(0.45, 1.0), 1.0, random.uniform(2, 4))
            )

    def update(self, dt: float, size: tuple[int, int]) -> None:
        w, h = size
        for particle in self.background:
            particle.update(dt * 0.12)
            if particle.pos.y > h + 10:
                particle.pos.y = -10
                particle.pos.x = random.uniform(0, w)
        for particle in self.particles:
            particle.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]

    def draw_background(self, surface: pygame.Surface, glow: float) -> None:
        for particle in self.background:
            particle.draw(surface, glow * 0.45)

    def draw(self, surface: pygame.Surface, glow: float) -> None:
        for particle in self.particles:
            particle.draw(surface, glow)


class ScreenShake:
    def __init__(self) -> None:
        self.time = 0.0
        self.power = 0.0

    def add(self, power: float, duration: float = 0.20) -> None:
        self.time = max(self.time, duration)
        self.power = max(self.power, power)

    def update(self, dt: float) -> Vec2:
        if self.time <= 0:
            self.power = 0
            return Vec2()
        self.time -= dt
        strength = self.power * clamp(self.time / 0.20, 0, 1)
        return Vec2(random.uniform(-strength, strength), random.uniform(-strength, strength))
