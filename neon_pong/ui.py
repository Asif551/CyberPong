from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pygame

from .utils import clamp, draw_text, ease_out_cubic


@dataclass
class Button:
    label: str
    action: Callable[[], None]
    rect: pygame.Rect
    enabled: bool = True
    hover: float = 0.0

    def update(self, dt: float, mouse_pos: tuple[int, int]) -> None:
        target = 1.0 if self.enabled and self.rect.collidepoint(mouse_pos) else 0.0
        self.hover += (target - self.hover) * min(dt * 14, 1)

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.enabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos):
            self.action()
            return True
        return False

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, selected: bool = False) -> None:
        h = max(self.hover, 1.0 if selected else 0.0)
        color = (12, 24, 48)
        border = (0, int(155 + 100 * h), 255)
        fill_alpha = int(95 + h * 60)
        layer = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        pygame.draw.rect(layer, (*border, int(35 + h * 80)), layer.get_rect().inflate(16, 16), border_radius=8)
        pygame.draw.rect(layer, (*color, fill_alpha), layer.get_rect(), border_radius=7)
        pygame.draw.rect(layer, (*border, 210), layer.get_rect(), width=2, border_radius=7)
        surface.blit(layer, self.rect)
        x = self.rect.centerx + int(6 * ease_out_cubic(h))
        draw_text(surface, self.label, font, (225, 250, 255), (x, self.rect.centery), glow=h > 0.05)


class Menu:
    def __init__(self, title: str, buttons: list[Button]) -> None:
        self.title = title
        self.buttons = buttons
        self.selected = 0

    def update(self, dt: float) -> None:
        mouse = pygame.mouse.get_pos()
        for button in self.buttons:
            button.update(dt, mouse)

    def event(self, event: pygame.event.Event, audio=None) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.selected = (self.selected - 1) % len(self.buttons)
                if audio:
                    audio.play("menu")
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.selected = (self.selected + 1) % len(self.buttons)
                if audio:
                    audio.play("menu")
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                if audio:
                    audio.play("menu")
                self.buttons[self.selected].action()
        for index, button in enumerate(self.buttons):
            if button.handle_event(event):
                self.selected = index
                if audio:
                    audio.play("menu")

    def draw(self, surface: pygame.Surface, title_font: pygame.font.Font, font: pygame.font.Font) -> None:
        draw_text(surface, self.title, title_font, (235, 255, 255), (surface.get_width() / 2, 92), True, (255, 44, 214))
        for index, button in enumerate(self.buttons):
            button.draw(surface, font, index == self.selected)


class TextBox:
    def __init__(self, rect: pygame.Rect, placeholder: str) -> None:
        self.rect = rect
        self.placeholder = placeholder
        self.text = ""
        self.active = False
        self.pulse = 0.0

    def event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)
            return self.active
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key not in (pygame.K_RETURN, pygame.K_TAB, pygame.K_ESCAPE):
                if len(self.text) < 18 and event.unicode and event.unicode.isprintable():
                    self.text += event.unicode
            return True
        return False

    def update(self, dt: float) -> None:
        self.pulse = (self.pulse + dt * 2.5) % 1.0

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, label_font: pygame.font.Font, label: str) -> None:
        h = 1.0 if self.active else 0.0
        layer = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        pygame.draw.rect(layer, (8, 18, 38, 178), layer.get_rect(), border_radius=7)
        pygame.draw.rect(layer, (0, int(160 + 80 * h), 255, 220), layer.get_rect(), 2, border_radius=7)
        surface.blit(layer, self.rect)
        draw_text(surface, label, label_font, (140, 220, 255), (self.rect.centerx, self.rect.y - 22), False)
        content = self.text or self.placeholder
        color = (235, 255, 255) if self.text else (110, 145, 170)
        draw_text(surface, content, font, color, self.rect.center)


class ToggleLine:
    def __init__(self, label: str, getter: Callable[[], str], action: Callable[[int], None]) -> None:
        self.label = label
        self.getter = getter
        self.action = action

    def display(self) -> str:
        return f"{self.label}: {self.getter()}"
