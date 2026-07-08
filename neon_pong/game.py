from __future__ import annotations

import enum
import math
import time

import pygame

from .audio import AudioManager
from .config import RESOLUTIONS, SettingsManager
from .effects import ParticleSystem, ScreenShake
from .entities import Ball, Paddle
from .ui import Button, Menu, TextBox, ToggleLine
from .utils import Vec2, clamp, draw_text, ease_out_back, ease_out_cubic, lerp


class GameMode(enum.Enum):
    MAIN_MENU = "main_menu"
    NAME_ENTRY = "name_entry"
    SETTINGS = "settings"
    CONTROLS = "controls"
    CREDITS = "credits"
    PLAYING = "playing"
    PAUSED = "paused"
    VICTORY = "victory"


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.font.init()
        self.settings_manager = SettingsManager()
        self.settings = self.settings_manager.settings
        self.screen = self.create_display()
        self.clock = pygame.time.Clock()
        self.running = True
        self.mode = GameMode.MAIN_MENU
        self.previous_mode = GameMode.MAIN_MENU
        self.transition = 1.0
        self.transition_dir = -1
        self.audio = AudioManager(self.settings)
        self.audio.play_music()
        self.fonts = self.create_fonts()
        self.particles = ParticleSystem()
        self.particles.seed_background(self.size)
        self.shake = ScreenShake()
        self.camera_offset = Vec2()
        self.left_name = "Player 1"
        self.right_name = "Player 2"
        self.score = [0, 0]
        self.goal_flash = [0.0, 0.0]
        self.countdown_time = 0.0
        self.match_start = time.perf_counter()
        self.winner = ""
        self.left = Paddle(52, self.size[1] / 2, (pygame.K_w, pygame.K_s))
        self.right = Paddle(self.size[0] - 52, self.size[1] / 2, (pygame.K_UP, pygame.K_DOWN), (255, 44, 214))
        self.ball = Ball(Vec2(self.size[0] / 2, self.size[1] / 2))
        self.ball.reset(self.size)
        self.name_boxes = [
            TextBox(pygame.Rect(self.size[0] // 2 - 190, self.size[1] // 2 - 44, 380, 56), "Player 1"),
            TextBox(pygame.Rect(self.size[0] // 2 - 190, self.size[1] // 2 + 58, 380, 56), "Player 2"),
        ]
        self.name_boxes[0].active = True
        self.menu = self.build_main_menu()
        self.pause_menu = self.build_pause_menu()
        self.settings_lines = self.build_settings_lines()
        self.settings_index = 0

    @property
    def size(self) -> tuple[int, int]:
        return self.screen.get_size()

    def create_display(self) -> pygame.Surface:
        flags = pygame.SCALED
        if self.settings.fullscreen:
            flags |= pygame.FULLSCREEN
        try:
            return pygame.display.set_mode(self.settings.resolution, flags, vsync=int(self.settings.vsync))
        except TypeError:
            return pygame.display.set_mode(self.settings.resolution, flags)

    def create_fonts(self) -> dict[str, pygame.font.Font]:
        return {
            "title": pygame.font.SysFont("consolas", 58, bold=True),
            "large": pygame.font.SysFont("consolas", 40, bold=True),
            "medium": pygame.font.SysFont("consolas", 26, bold=True),
            "small": pygame.font.SysFont("consolas", 18),
            "tiny": pygame.font.SysFont("consolas", 14),
            "score": pygame.font.SysFont("consolas", 72, bold=True),
            "mega": pygame.font.SysFont("consolas", 106, bold=True),
        }

    def button_stack(self, labels_actions: list[tuple[str, callable]], y: int = 178) -> list[Button]:
        width, height, gap = 300, 48, 14
        x = self.size[0] // 2 - width // 2
        return [
            Button(label, action, pygame.Rect(x, y + index * (height + gap), width, height))
            for index, (label, action) in enumerate(labels_actions)
        ]

    def build_main_menu(self) -> Menu:
        return Menu(
            "NEON PULSE PONG",
            self.button_stack(
                [
                    ("Play", lambda: self.change_mode(GameMode.NAME_ENTRY)),
                    ("Settings", lambda: self.change_mode(GameMode.SETTINGS)),
                    ("Controls", lambda: self.change_mode(GameMode.CONTROLS)),
                    ("Credits", lambda: self.change_mode(GameMode.CREDITS)),
                    ("Exit", self.quit),
                ]
            ),
        )

    def build_pause_menu(self) -> Menu:
        return Menu(
            "PAUSED",
            self.button_stack(
                [
                    ("Resume", lambda: self.change_mode(GameMode.PLAYING)),
                    ("Restart Match", self.start_match),
                    ("Settings", lambda: self.change_mode(GameMode.SETTINGS, from_pause=True)),
                    ("Main Menu", lambda: self.change_mode(GameMode.MAIN_MENU)),
                    ("Exit", self.quit),
                ],
                y=160,
            ),
        )

    def build_settings_lines(self) -> list[ToggleLine]:
        return [
            ToggleLine("Resolution", lambda: f"{self.settings.resolution[0]}x{self.settings.resolution[1]}", self.change_resolution),
            ToggleLine("Fullscreen", lambda: "On" if self.settings.fullscreen else "Off", self.toggle_fullscreen),
            ToggleLine("FPS Limit", lambda: str(self.settings.fps_limit), self.change_fps),
            ToggleLine("Music Volume", lambda: f"{int(self.settings.music_volume * 100)}%", self.change_music),
            ToggleLine("SFX Volume", lambda: f"{int(self.settings.sfx_volume * 100)}%", self.change_sfx),
            ToggleLine("Glow Intensity", lambda: f"{self.settings.glow_intensity:.2f}x", self.change_glow),
            ToggleLine("Winning Score", lambda: str(self.settings.winning_score), self.change_winning_score),
            ToggleLine("VSync", lambda: "On" if self.settings.vsync else "Off", self.toggle_vsync),
        ]

    def change_mode(self, mode: GameMode, from_pause: bool = False) -> None:
        self.previous_mode = GameMode.PAUSED if from_pause else self.mode
        self.mode = mode
        self.transition = 1.0
        self.transition_dir = -1

    def apply_display_changes(self) -> None:
        self.screen = self.create_display()
        self.fonts = self.create_fonts()
        self.left.x = 52
        self.right.x = self.size[0] - 52
        self.left.y = self.right.y = self.size[1] / 2
        self.left.sync_rect()
        self.right.sync_rect()
        self.ball.reset(self.size)
        self.name_boxes = [
            TextBox(pygame.Rect(self.size[0] // 2 - 190, self.size[1] // 2 - 44, 380, 56), "Player 1"),
            TextBox(pygame.Rect(self.size[0] // 2 - 190, self.size[1] // 2 + 58, 380, 56), "Player 2"),
        ]
        self.menu = self.build_main_menu()
        self.pause_menu = self.build_pause_menu()
        self.particles.seed_background(self.size)

    def change_resolution(self, direction: int) -> None:
        self.settings.resolution_index = (self.settings.resolution_index + direction) % len(RESOLUTIONS)
        self.settings_manager.save()
        self.apply_display_changes()

    def toggle_fullscreen(self, direction: int = 1) -> None:
        self.settings.fullscreen = not self.settings.fullscreen
        self.settings_manager.save()
        self.apply_display_changes()

    def change_fps(self, direction: int) -> None:
        values = [60, 90, 120, 144, 165, 240]
        index = values.index(self.settings.fps_limit) if self.settings.fps_limit in values else 3
        self.settings.fps_limit = values[(index + direction) % len(values)]
        self.settings_manager.save()

    def change_music(self, direction: int) -> None:
        self.settings.music_volume = clamp(self.settings.music_volume + direction * 0.05, 0, 1)
        self.audio.apply_volumes()
        self.settings_manager.save()

    def change_sfx(self, direction: int) -> None:
        self.settings.sfx_volume = clamp(self.settings.sfx_volume + direction * 0.05, 0, 1)
        self.audio.apply_volumes()
        self.settings_manager.save()

    def change_glow(self, direction: int) -> None:
        self.settings.glow_intensity = clamp(self.settings.glow_intensity + direction * 0.1, 0.25, 2.0)
        self.settings_manager.save()

    def change_winning_score(self, direction: int) -> None:
        self.settings.winning_score = int(clamp(self.settings.winning_score + direction, 3, 21))
        self.settings_manager.save()

    def toggle_vsync(self, direction: int = 1) -> None:
        self.settings.vsync = not self.settings.vsync
        self.settings_manager.save()
        self.apply_display_changes()

    def start_match(self) -> None:
        self.left_name = self.name_boxes[0].text.strip() or "Player 1"
        self.right_name = self.name_boxes[1].text.strip() or "Player 2"
        self.score = [0, 0]
        self.goal_flash = [0.0, 0.0]
        self.match_start = time.perf_counter()
        self.winner = ""
        self.left.y = self.right.y = self.size[1] / 2
        self.left.velocity = self.right.velocity = 0
        self.left.sync_rect()
        self.right.sync_rect()
        self.ball.reset(self.size)
        self.countdown_time = 4.0
        self.audio.play("countdown")
        self.change_mode(GameMode.PLAYING)

    def quit(self) -> None:
        self.running = False

    def run(self) -> None:
        pygame.display.set_caption("Neon Pulse Pong")
        while self.running:
            dt = self.clock.tick(self.settings.fps_limit) / 1000.0
            dt = min(dt, 1 / 30)
            self.handle_events()
            self.update(dt)
            self.draw()
        self.settings_manager.save()
        pygame.quit()

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.handle_escape()
            elif self.mode == GameMode.MAIN_MENU:
                self.menu.event(event, self.audio)
            elif self.mode == GameMode.PAUSED:
                self.pause_menu.event(event, self.audio)
            elif self.mode == GameMode.NAME_ENTRY:
                self.name_entry_event(event)
            elif self.mode == GameMode.SETTINGS:
                self.settings_event(event)
            elif self.mode == GameMode.VICTORY:
                self.victory_event(event)

    def handle_escape(self) -> None:
        if self.mode == GameMode.PLAYING:
            self.change_mode(GameMode.PAUSED)
        elif self.mode == GameMode.PAUSED:
            self.change_mode(GameMode.PLAYING)
        elif self.mode in (GameMode.SETTINGS, GameMode.CONTROLS, GameMode.CREDITS, GameMode.NAME_ENTRY, GameMode.VICTORY):
            self.change_mode(GameMode.MAIN_MENU if self.previous_mode != GameMode.PAUSED else GameMode.PAUSED)

    def name_entry_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_TAB:
            self.name_boxes[0].active, self.name_boxes[1].active = self.name_boxes[1].active, self.name_boxes[0].active
            self.audio.play("menu")
            return
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self.audio.play("menu")
            self.start_match()
            return
        for box in self.name_boxes:
            box.event(event)

    def settings_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.settings_index = (self.settings_index - 1) % len(self.settings_lines)
                self.audio.play("menu")
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.settings_index = (self.settings_index + 1) % len(self.settings_lines)
                self.audio.play("menu")
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self.settings_lines[self.settings_index].action(-1)
                self.audio.play("menu")
            elif event.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_RETURN, pygame.K_SPACE):
                self.settings_lines[self.settings_index].action(1)
                self.audio.play("menu")
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            y0, gap = 158, 46
            for index in range(len(self.settings_lines)):
                rect = pygame.Rect(self.size[0] // 2 - 250, y0 + index * gap - 18, 500, 36)
                if rect.collidepoint(event.pos):
                    self.settings_index = index
                    self.settings_lines[index].action(1)
                    self.audio.play("menu")

    def victory_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                self.start_match()
            elif event.key in (pygame.K_RETURN, pygame.K_ESCAPE):
                self.change_mode(GameMode.MAIN_MENU)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if event.pos[0] < self.size[0] / 2:
                self.start_match()
            else:
                self.change_mode(GameMode.MAIN_MENU)

    def update(self, dt: float) -> None:
        self.transition = max(0, self.transition + self.transition_dir * dt * 2.8)
        self.particles.update(dt, self.size)
        self.camera_offset = self.shake.update(dt)
        self.goal_flash[0] = max(0, self.goal_flash[0] - dt)
        self.goal_flash[1] = max(0, self.goal_flash[1] - dt)
        if self.mode == GameMode.MAIN_MENU:
            self.menu.update(dt)
        elif self.mode == GameMode.PAUSED:
            self.pause_menu.update(dt)
        elif self.mode == GameMode.NAME_ENTRY:
            for box in self.name_boxes:
                box.update(dt)
        elif self.mode == GameMode.PLAYING:
            self.update_match(dt)

    def update_match(self, dt: float) -> None:
        keys = pygame.key.get_pressed()
        bounds = self.screen.get_rect().inflate(0, -36)
        self.left.update(keys, dt, bounds)
        self.right.update(keys, dt, bounds)
        if self.countdown_time > 0:
            old_step = math.ceil(self.countdown_time)
            self.countdown_time -= dt
            if math.ceil(self.countdown_time) != old_step and self.countdown_time > 0:
                self.audio.play("countdown")
            return
        previous = Vec2(self.ball.pos)
        self.ball.update(dt)
        if self.ball.bounce_wall(bounds.top, bounds.bottom):
            self.audio.play("wall")
        for paddle in (self.left, self.right):
            if self.ball.collide_paddle(paddle, previous):
                direction = Vec2(1 if paddle is self.left else -1, 0)
                self.particles.burst(self.ball.pos, direction)
                self.audio.play("paddle")
                if self.ball.speed > 780:
                    self.shake.add(min(10, (self.ball.speed - 650) / 55))
        if self.ball.pos.x + self.ball.radius < 0:
            self.score_goal(1)
        elif self.ball.pos.x - self.ball.radius > self.size[0]:
            self.score_goal(0)

    def score_goal(self, player: int) -> None:
        self.score[player] += 1
        self.goal_flash[player] = 1.0
        self.audio.play("score")
        self.particles.goal_ring(Vec2(self.size[0] / 2, self.size[1] / 2))
        self.shake.add(7, 0.3)
        if self.score[player] >= self.settings.winning_score and self.score[player] - self.score[1 - player] >= 2:
            self.winner = self.left_name if player == 0 else self.right_name
            self.audio.play("victory")
            self.change_mode(GameMode.VICTORY)
            return
        self.ball.reset(self.size, direction=-1 if player == 0 else 1)
        self.countdown_time = 4.0

    def draw(self) -> None:
        world = pygame.Surface(self.size, pygame.SRCALPHA)
        self.draw_background(world)
        if self.mode in (GameMode.PLAYING, GameMode.PAUSED, GameMode.VICTORY):
            self.draw_match(world)
        if self.mode == GameMode.MAIN_MENU:
            self.menu.draw(world, self.fonts["title"], self.fonts["medium"])
        elif self.mode == GameMode.NAME_ENTRY:
            self.draw_name_entry(world)
        elif self.mode == GameMode.SETTINGS:
            self.draw_settings(world)
        elif self.mode == GameMode.CONTROLS:
            self.draw_info(world, "CONTROLS", ["Player 1  W / S", "Player 2  Up / Down", "Esc pauses the match", "Enter confirms menu choices"])
        elif self.mode == GameMode.CREDITS:
            self.draw_info(world, "CREDITS", [
                "Developed by Asif Ikbal",
                "Built with Python and Pygame Community Edition",
                "Inspired by the classic Pong arcade game.",
                "Special thanks to the open-source community and everyone who supported this project.",
                "Version 1.0.0",
                "© 2026 Asif Ikbal. All rights reserved."
            ])
        elif self.mode == GameMode.PAUSED:
            self.draw_dim(world, 145)
            self.pause_menu.draw(world, self.fonts["title"], self.fonts["medium"])
        elif self.mode == GameMode.VICTORY:
            self.draw_victory(world)
        if self.transition > 0:
            self.draw_transition(world)
        self.screen.blit(world, self.camera_offset)
        pygame.display.flip()

    def draw_background(self, surface: pygame.Surface) -> None:
        w, h = self.size
        for y in range(h):
            t = y / max(h - 1, 1)
            color = (int(3 + 5 * t), int(8 + 12 * t), int(28 + 34 * t))
            pygame.draw.line(surface, color, (0, y), (w, y))
        grid = pygame.Surface(self.size, pygame.SRCALPHA)
        offset = (pygame.time.get_ticks() * 0.035) % 42
        for x in range(-80, w + 80, 42):
            alpha = 26 if x % 84 else 44
            pygame.draw.line(grid, (0, 205, 255, alpha), (x + offset, h), (w / 2 + (x - w / 2) * 0.32, h * 0.52), 1)
        for y in range(int(h * 0.52), h + 60, 36):
            alpha = int(18 + 64 * ((y - h * 0.52) / (h * 0.48)))
            pygame.draw.line(grid, (255, 44, 214, alpha), (0, y + offset), (w, y + offset), 1)
        surface.blit(grid, (0, 0))
        self.particles.draw_background(surface, self.settings.glow_intensity)
        for y in range(24, h - 24, 28):
            pygame.draw.line(surface, (0, 220, 255, 90), (w // 2, y), (w // 2, y + 14), 3)

    def draw_match(self, surface: pygame.Surface) -> None:
        self.left.draw(surface, self.settings.glow_intensity)
        self.right.draw(surface, self.settings.glow_intensity)
        self.ball.draw(surface, self.settings.glow_intensity)
        self.particles.draw(surface, self.settings.glow_intensity)
        self.draw_hud(surface)
        if self.countdown_time > 0 and self.mode == GameMode.PLAYING:
            self.draw_countdown(surface)

    def draw_hud(self, surface: pygame.Surface) -> None:
        w = self.size[0]
        small, score_font = self.fonts["small"], self.fonts["score"]
        draw_text(surface, self.left_name, small, (150, 230, 255), (w * 0.25, 28), True)
        draw_text(surface, self.right_name, small, (255, 120, 235), (w * 0.75, 28), True, (255, 44, 214))
        for index, x in enumerate((w * 0.25, w * 0.75)):
            scale = 1 + 0.25 * ease_out_back(self.goal_flash[index])
            font = pygame.font.SysFont("consolas", int(72 * scale), bold=True)
            color = (235, 255, 255) if index == 0 else (255, 210, 248)
            draw_text(surface, str(self.score[index]), font, color, (x, 80), True)
        draw_text(surface, f"First to {self.settings.winning_score}, win by 2", small, (120, 170, 195), (w / 2, 26))
        if self.settings.show_ball_speed:
            draw_text(surface, f"{int(self.ball.speed)} px/s", self.fonts["tiny"], (95, 140, 170), (w / 2, 52))
        if self.settings.show_fps:
            draw_text(surface, f"{int(self.clock.get_fps())} FPS", self.fonts["tiny"], (95, 140, 170), (w - 46, self.size[1] - 18))

    def draw_countdown(self, surface: pygame.Surface) -> None:
        if self.countdown_time > 1:
            text = str(int(math.ceil(self.countdown_time - 1)))
            local = self.countdown_time % 1
        else:
            text = "GO!"
            local = self.countdown_time
        scale = 0.75 + 0.38 * ease_out_back(1 - local)
        font = pygame.font.SysFont("consolas", int(108 * scale), bold=True)
        alpha = int(255 * clamp(self.countdown_time, 0, 1))
        draw_text(surface, text, font, (235, 255, 255), (self.size[0] / 2, self.size[1] / 2), True, (0, 220, 255), alpha)

    def draw_name_entry(self, surface: pygame.Surface) -> None:
        draw_text(surface, "ENTER PLAYERS", self.fonts["title"], (235, 255, 255), (self.size[0] / 2, 112), True)
        for box, label in zip(self.name_boxes, ("Left Paddle", "Right Paddle")):
            box.draw(surface, self.fonts["medium"], self.fonts["small"], label)
        draw_text(surface, "Tab switches fields    Enter starts match", self.fonts["small"], (120, 170, 195), (self.size[0] / 2, self.size[1] - 86))

    def draw_settings(self, surface: pygame.Surface) -> None:
        draw_text(surface, "SETTINGS", self.fonts["title"], (235, 255, 255), (self.size[0] / 2, 86), True, (255, 44, 214))
        y0, gap = 158, 46
        for index, line in enumerate(self.settings_lines):
            selected = index == self.settings_index
            rect = pygame.Rect(self.size[0] // 2 - 270, y0 + index * gap - 21, 540, 40)
            layer = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(layer, (5, 20, 42, 150), layer.get_rect(), border_radius=6)
            if selected:
                pygame.draw.rect(layer, (0, 220, 255, 220), layer.get_rect(), 2, border_radius=6)
            surface.blit(layer, rect)
            draw_text(surface, line.display(), self.fonts["medium"], (230, 252, 255), rect.center, selected)
        draw_text(surface, "Use Up/Down and Left/Right. Esc returns.", self.fonts["small"], (120, 170, 195), (self.size[0] / 2, self.size[1] - 54))

    def draw_info(self, surface: pygame.Surface, title: str, lines: list[str]) -> None:
        draw_text(surface, title, self.fonts["title"], (235, 255, 255), (self.size[0] / 2, 106), True)
        for index, line in enumerate(lines):
            draw_text(surface, line, self.fonts["medium"], (210, 245, 255), (self.size[0] / 2, 205 + index * 52), True if index == 0 else False)
        draw_text(surface, "Esc returns", self.fonts["small"], (120, 170, 195), (self.size[0] / 2, self.size[1] - 64))

    def draw_victory(self, surface: pygame.Surface) -> None:
        self.draw_dim(surface, 155)
        elapsed = int(time.perf_counter() - self.match_start)
        banner_y = self.size[1] / 2 - 70
        pulse = 0.92 + 0.08 * math.sin(pygame.time.get_ticks() / 180)
        font = pygame.font.SysFont("consolas", int(70 * pulse), bold=True)
        draw_text(surface, "VICTORY", self.fonts["large"], (255, 44, 214), (self.size[0] / 2, banner_y - 86), True, (255, 44, 214))
        draw_text(surface, self.winner, font, (235, 255, 255), (self.size[0] / 2, banner_y), True)
        final = f"{self.left_name} {self.score[0]}  -  {self.score[1]} {self.right_name}"
        draw_text(surface, final, self.fonts["medium"], (210, 245, 255), (self.size[0] / 2, banner_y + 74), True)
        draw_text(surface, f"Match duration {elapsed // 60:02d}:{elapsed % 60:02d}", self.fonts["small"], (120, 190, 215), (self.size[0] / 2, banner_y + 114))
        draw_text(surface, "R replay     Enter main menu", self.fonts["small"], (170, 230, 250), (self.size[0] / 2, banner_y + 164))

    def draw_dim(self, surface: pygame.Surface, alpha: int) -> None:
        overlay = pygame.Surface(self.size, pygame.SRCALPHA)
        overlay.fill((0, 0, 18, alpha))
        surface.blit(overlay, (0, 0))

    def draw_transition(self, surface: pygame.Surface) -> None:
        alpha = int(255 * ease_out_cubic(self.transition))
        overlay = pygame.Surface(self.size, pygame.SRCALPHA)
        overlay.fill((0, 0, 20, alpha))
        surface.blit(overlay, (0, 0))
