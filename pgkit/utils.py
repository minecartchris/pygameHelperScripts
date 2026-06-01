"""General-purpose helpers: math, color, timers, text, and asset loading."""

from __future__ import annotations

import math
import random
from typing import Iterable

import pygame
from pygame.math import Vector2


# --------------------------------------------------------------------------- #
# Math helpers
# --------------------------------------------------------------------------- #
def clamp(value: float, low: float, high: float) -> float:
    """Constrain ``value`` to the inclusive range [low, high]."""
    return max(low, min(value, high))


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between ``a`` and ``b`` by factor ``t`` (0..1)."""
    return a + (b - a) * t


def remap(value: float, in_min: float, in_max: float, out_min: float, out_max: float) -> float:
    """Map ``value`` from one numeric range into another."""
    if in_max == in_min:
        return out_min
    t = (value - in_min) / (in_max - in_min)
    return lerp(out_min, out_max, t)


def distance(a, b) -> float:
    """Distance between two points (anything with x/y or index 0/1)."""
    ax, ay = _xy(a)
    bx, by = _xy(b)
    return math.hypot(bx - ax, by - ay)


def angle_to(a, b) -> float:
    """Angle in degrees from point ``a`` to point ``b`` (0 = right, CW positive)."""
    ax, ay = _xy(a)
    bx, by = _xy(b)
    return math.degrees(math.atan2(by - ay, bx - ax))


def vector_from_angle(degrees: float, length: float = 1.0) -> Vector2:
    """Build a Vector2 pointing at ``degrees`` (0 = right) with the given length."""
    rad = math.radians(degrees)
    return Vector2(math.cos(rad) * length, math.sin(rad) * length)


def chance(probability: float) -> bool:
    """Return True with the given probability (0..1)."""
    return random.random() < probability


def _xy(p):
    """Pull (x, y) out of a Vector2, tuple, list, or rect-like object."""
    if hasattr(p, "x") and hasattr(p, "y"):
        return p.x, p.y
    return p[0], p[1]


# --------------------------------------------------------------------------- #
# Color helpers
# --------------------------------------------------------------------------- #
def lerp_color(c1, c2, t: float):
    """Interpolate between two RGB(A) colors by factor ``t`` (0..1)."""
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


def random_color(bright: bool = True):
    """A random RGB color. ``bright`` keeps it vivid rather than muddy."""
    if not bright:
        return tuple(random.randint(0, 255) for _ in range(3))
    c = pygame.Color(0, 0, 0)
    c.hsva = (random.uniform(0, 360), 80, 95, 100)
    return (c.r, c.g, c.b)


# --------------------------------------------------------------------------- #
# Timer
# --------------------------------------------------------------------------- #
class Timer:
    """A simple countdown timer driven by delta-time (seconds).

    Example::

        t = Timer(1.5)            # 1.5 second timer
        t.start()
        ...
        if t.update(dt):          # returns True on the frame it finishes
            do_something()
    """

    def __init__(self, duration: float, repeat: bool = False):
        self.duration = duration
        self.repeat = repeat
        self.remaining = duration
        self.running = False

    def start(self):
        self.remaining = self.duration
        self.running = True
        return self

    def stop(self):
        self.running = False
        return self

    @property
    def finished(self) -> bool:
        return self.running is False and self.remaining <= 0

    @property
    def progress(self) -> float:
        """0.0 at start, 1.0 when complete."""
        if self.duration <= 0:
            return 1.0
        return clamp(1 - self.remaining / self.duration, 0.0, 1.0)

    def update(self, dt: float) -> bool:
        """Advance by ``dt`` seconds. Returns True on the frame it elapses."""
        if not self.running:
            return False
        self.remaining -= dt
        if self.remaining <= 0:
            if self.repeat:
                self.remaining += self.duration
            else:
                self.running = False
                self.remaining = 0
            return True
        return False


# --------------------------------------------------------------------------- #
# Drawing / text
# --------------------------------------------------------------------------- #
_font_cache: dict = {}


def get_font(size: int = 24, name: str | None = None) -> pygame.font.Font:
    """Return a cached font of the given size (system font by ``name`` or default)."""
    key = (name, size)
    if key not in _font_cache:
        if name:
            _font_cache[key] = pygame.font.SysFont(name, size)
        else:
            _font_cache[key] = pygame.font.Font(None, size)
    return _font_cache[key]


def draw_text(
    surface: pygame.Surface,
    text: str,
    pos,
    size: int = 24,
    color=(255, 255, 255),
    anchor: str = "topleft",
    font_name: str | None = None,
):
    """Render ``text`` onto ``surface`` at ``pos``.

    ``anchor`` is any pygame Rect anchor name (``center``, ``midtop``, etc).
    Returns the text's rect.
    """
    font = get_font(size, font_name)
    img = font.render(str(text), True, color)
    rect = img.get_rect(**{anchor: pos})
    surface.blit(img, rect)
    return rect


# --------------------------------------------------------------------------- #
# Asset loading
# --------------------------------------------------------------------------- #
def load_image(path: str, scale: float | None = None, alpha: bool = True) -> pygame.Surface:
    """Load an image, optionally scaling it. Converts for fast blitting."""
    img = pygame.image.load(path)
    img = img.convert_alpha() if alpha else img.convert()
    if scale and scale != 1.0:
        size = (int(img.get_width() * scale), int(img.get_height() * scale))
        img = pygame.transform.smoothscale(img, size)
    return img


def make_surface(size, color, alpha: bool = False) -> pygame.Surface:
    """Create a solid-color surface (handy for placeholder sprites)."""
    flags = pygame.SRCALPHA if alpha else 0
    surf = pygame.Surface(size, flags)
    surf.fill(color)
    return surf
