"""A polled input manager that tracks held / just-pressed / just-released state.

The :class:`App` owns one of these and feeds it events; in your scene you just
ask questions like ``app.input.pressed("space")`` or ``app.input.axis()``.

Key names are friendly strings: ``"left" "a" "space" "escape" "lshift"`` …
(anything ``pygame.key.key_code`` understands), plus the arrow aliases
``"left" "right" "up" "down"``.
"""

from __future__ import annotations

from typing import Set

import pygame
from pygame.math import Vector2


_ALIASES = {
    "left": pygame.K_LEFT,
    "right": pygame.K_RIGHT,
    "up": pygame.K_UP,
    "down": pygame.K_DOWN,
    "enter": pygame.K_RETURN,
    "return": pygame.K_RETURN,
    "esc": pygame.K_ESCAPE,
    "escape": pygame.K_ESCAPE,
    "space": pygame.K_SPACE,
    "shift": pygame.K_LSHIFT,
    "ctrl": pygame.K_LCTRL,
    "alt": pygame.K_LALT,
    "tab": pygame.K_TAB,
}


def _to_keycode(name) -> int:
    if isinstance(name, int):
        return name
    key = name.lower()
    if key in _ALIASES:
        return _ALIASES[key]
    try:
        return pygame.key.key_code(key)
    except (ValueError, TypeError):
        raise ValueError(f"Unknown key name: {name!r}")


class InputManager:
    """Tracks keyboard and mouse state across frames."""

    def __init__(self):
        self._held: Set[int] = set()
        self._pressed: Set[int] = set()      # went down this frame
        self._released: Set[int] = set()     # went up this frame

        self.mouse_pos = (0, 0)
        self.mouse_rel = (0, 0)
        self._mouse_held: Set[int] = set()
        self._mouse_pressed: Set[int] = set()
        self._mouse_released: Set[int] = set()
        self.scroll = 0                      # net wheel scroll this frame

    # ------------------------------------------------------------------ #
    # Called by the App each frame
    # ------------------------------------------------------------------ #
    def begin_frame(self):
        """Clear per-frame edge state. Call before processing events."""
        self._pressed.clear()
        self._released.clear()
        self._mouse_pressed.clear()
        self._mouse_released.clear()
        self.scroll = 0
        self.mouse_rel = (0, 0)

    def process(self, event: pygame.event.Event):
        """Feed a single pygame event into the manager."""
        if event.type == pygame.KEYDOWN:
            self._held.add(event.key)
            self._pressed.add(event.key)
        elif event.type == pygame.KEYUP:
            self._held.discard(event.key)
            self._released.add(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            self._mouse_held.add(event.button)
            self._mouse_pressed.add(event.button)
        elif event.type == pygame.MOUSEBUTTONUP:
            self._mouse_held.discard(event.button)
            self._mouse_released.add(event.button)
        elif event.type == pygame.MOUSEMOTION:
            self.mouse_pos = event.pos
            self.mouse_rel = event.rel
        elif event.type == pygame.MOUSEWHEEL:
            self.scroll += event.y

    # ------------------------------------------------------------------ #
    # Keyboard queries
    # ------------------------------------------------------------------ #
    def held(self, key) -> bool:
        """True while the key is down."""
        return _to_keycode(key) in self._held

    # alias people expect
    pressed_held = held

    def pressed(self, key) -> bool:
        """True only on the frame the key went down."""
        return _to_keycode(key) in self._pressed

    def released(self, key) -> bool:
        """True only on the frame the key came up."""
        return _to_keycode(key) in self._released

    def any_held(self, *keys) -> bool:
        return any(self.held(k) for k in keys)

    # ------------------------------------------------------------------ #
    # Mouse queries
    # ------------------------------------------------------------------ #
    def mouse_held(self, button: int = 1) -> bool:
        return button in self._mouse_held

    def mouse_pressed(self, button: int = 1) -> bool:
        return button in self._mouse_pressed

    def mouse_released(self, button: int = 1) -> bool:
        return button in self._mouse_released

    # ------------------------------------------------------------------ #
    # Convenience
    # ------------------------------------------------------------------ #
    def axis(self, neg, pos) -> float:
        """Return -1 / 0 / +1 based on two opposing keys."""
        return (1 if self.held(pos) else 0) - (1 if self.held(neg) else 0)

    def direction(self, scheme: str = "both") -> Vector2:
        """Movement vector from WASD and/or arrow keys.

        ``scheme`` is ``"arrows"``, ``"wasd"``, or ``"both"`` (default).
        The vector is normalized so diagonals aren't faster.
        """
        x = y = 0.0
        if scheme in ("arrows", "both"):
            x += self.axis("left", "right")
            y += self.axis("up", "down")
        if scheme in ("wasd", "both"):
            x += self.axis("a", "d")
            y += self.axis("w", "s")
        v = Vector2(max(-1, min(1, x)), max(-1, min(1, y)))
        if v.length_squared() > 1:
            v.normalize_ip()
        return v
