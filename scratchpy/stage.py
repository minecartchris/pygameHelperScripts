"""The stage and its sprite — what the blocks actually control.

Coordinates follow Scratch: the stage centre is (0, 0), x grows right, y grows
*up*, and ``direction`` is in degrees where 90 = right, 0 = up, turning
clockwise increases it. :class:`StageSprite` is a thin layer over
``pgkit.Sprite`` that maps those onto screen pixels and a rotated costume.
"""

from __future__ import annotations

import math

import pygame

import pgkit
from pgkit import utils


def make_costume(size=64, color=(255, 140, 60)) -> pygame.Surface:
    """A simple round costume with a triangle marking its 'front' (up = dir 0)."""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    c = size // 2
    pygame.draw.circle(surf, color, (c, c), c - 4)
    pygame.draw.circle(surf, (255, 255, 255), (c, c), c - 4, 3)
    # front-pointing triangle (points up)
    pygame.draw.polygon(surf, (40, 40, 40),
                        [(c, 6), (c - 9, 22), (c + 9, 22)])
    return surf


class Stage:
    """A rectangular drawing area with a light background and a border."""

    def __init__(self, rect: pygame.Rect, background=(245, 246, 250)):
        self.rect = pygame.Rect(rect)
        self.background = background

    @property
    def width(self):
        return self.rect.width

    @property
    def height(self):
        return self.rect.height

    def to_screen(self, sx, sy):
        """Scratch (centre-origin, y-up) -> screen pixels."""
        return (self.rect.centerx + sx, self.rect.centery - sy)

    def draw(self, surface, sprite: "StageSprite"):
        prev_clip = surface.get_clip()
        surface.set_clip(self.rect)
        surface.fill(self.background, self.rect)
        sprite.draw(surface)
        sprite.draw_bubble(surface)
        surface.set_clip(prev_clip)
        pygame.draw.rect(surface, (90, 95, 110), self.rect, 2, border_radius=6)


class StageSprite(pgkit.Sprite):
    """The actor the scripts move around. Built on pgkit.Sprite."""

    def __init__(self, stage: Stage, costume: pygame.Surface | None = None):
        self.stage = stage
        self._costume = costume or make_costume()
        super().__init__(image=self._costume, pos=stage.to_screen(0, 0))

        self.sx = 0.0          # scratch coords (centre origin, y up)
        self.sy = 0.0
        self._direction = 90.0  # 90 = right
        self._size = 100.0      # percent
        self.say_text = ""
        self._rebuild()

    # ------------------------------------------------------------------ #
    # State
    # ------------------------------------------------------------------ #
    @property
    def direction(self):
        return self._direction

    @direction.setter
    def direction(self, value):
        # normalize to (-180, 180]
        self._direction = ((float(value) + 180) % 360) - 180
        self.angle = self._direction  # pgkit rotates the costume (0 = up)

    @property
    def size_pct(self):
        return self._size

    @size_pct.setter
    def size_pct(self, value):
        self._size = max(5.0, float(value))
        self._rebuild()

    def _rebuild(self):
        scale = self._size / 100.0
        w = max(1, int(self._costume.get_width() * scale))
        h = max(1, int(self._costume.get_height() * scale))
        scaled = pygame.transform.smoothscale(self._costume, (w, h))
        self.set_image(scaled, keep_angle=False)
        self.angle = self._direction
        self._sync_screen()

    def _sync_screen(self):
        self.move_to(self.stage.to_screen(self.sx, self.sy))

    # ------------------------------------------------------------------ #
    # Actions used by block behaviors
    # ------------------------------------------------------------------ #
    def move_steps(self, steps):
        rad = math.radians(self._direction)
        self.sx += math.sin(rad) * steps
        self.sy += math.cos(rad) * steps
        self._sync_screen()

    def turn(self, degrees):
        self.direction = self._direction + degrees

    def goto(self, x, y):
        self.sx, self.sy = float(x), float(y)
        self._sync_screen()

    def say(self, text):
        self.say_text = "" if text is None else str(text)

    def bounce_on_edge(self):
        hw, hh = self.stage.width / 2, self.stage.height / 2
        half_w = self.rect.width / 2
        half_h = self.rect.height / 2
        rad = math.radians(self._direction)
        vx, vy = math.sin(rad), math.cos(rad)

        if self.sx + half_w > hw and vx > 0:
            vx = -vx
            self.sx = hw - half_w
        elif self.sx - half_w < -hw and vx < 0:
            vx = -vx
            self.sx = -hw + half_w
        if self.sy + half_h > hh and vy > 0:
            vy = -vy
            self.sy = hh - half_h
        elif self.sy - half_h < -hh and vy < 0:
            vy = -vy
            self.sy = -hh + half_h

        self.direction = math.degrees(math.atan2(vx, vy))
        self._sync_screen()

    def reset(self):
        self.say_text = ""
        self._direction = 90.0
        self._size = 100.0
        self.sx = self.sy = 0.0
        self._rebuild()

    # ------------------------------------------------------------------ #
    # Rendering extras
    # ------------------------------------------------------------------ #
    def draw_bubble(self, surface):
        if not self.say_text:
            return
        pad = 8
        img = utils.get_font(22).render(self.say_text, True, (30, 30, 30))
        w, h = img.get_width() + pad * 2, img.get_height() + pad * 2
        bx = self.rect.centerx + 10
        by = self.rect.top - h - 6
        bx = max(self.stage.rect.left + 4, min(bx, self.stage.rect.right - w - 4))
        by = max(self.stage.rect.top + 4, by)
        bubble = pygame.Rect(bx, by, w, h)
        pygame.draw.rect(surface, (255, 255, 255), bubble, border_radius=10)
        pygame.draw.rect(surface, (170, 175, 190), bubble, 2, border_radius=10)
        surface.blit(img, (bx + pad, by + pad))
