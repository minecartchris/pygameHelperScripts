"""A friendlier sprite built on top of ``pygame.sprite.Sprite``.

Adds float-precision position, velocity/acceleration physics, rotation,
and a pile of convenience helpers so you rarely have to touch ``rect`` math
directly. Works inside ``pygame.sprite.Group`` like any normal sprite.
"""

from __future__ import annotations

import math
from typing import Optional

import pygame
from pygame.math import Vector2

from . import utils


class Sprite(pygame.sprite.Sprite):
    """An enhanced sprite.

    Create one with an image, or with a size+color to get a placeholder block::

        player = Sprite(image=my_surface, pos=(100, 100))
        enemy  = Sprite(size=(32, 32), color="red", pos=(200, 200))

    Position is tracked in ``self.pos`` (a Vector2 at the sprite's *center*)
    with float precision; ``self.rect`` is kept in sync automatically.
    """

    def __init__(
        self,
        image: Optional[pygame.Surface] = None,
        pos=(0, 0),
        size=(32, 32),
        color=(200, 200, 200),
        *groups,
        speed: float = 0.0,
        max_speed: Optional[float] = None,
        friction: float = 0.0,
    ):
        super().__init__(*groups)

        if image is None:
            image = utils.make_surface(size, color, alpha=True)
        self._base_image = image          # un-rotated source
        self.image = image
        self.rect = self.image.get_rect(center=pos)

        # --- movement state ---
        self.pos = Vector2(pos)           # center, float precision
        self.velocity = Vector2(0, 0)
        self.acceleration = Vector2(0, 0)
        self.speed = speed                # default move speed (px/sec)
        self.max_speed = max_speed        # velocity magnitude cap, or None
        self.friction = friction          # 0 = none, ~5 = sticky, per second

        self._angle = 0.0                 # degrees, 0 = unrotated
        self.alive_flag = True

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #
    @property
    def x(self) -> float:
        return self.pos.x

    @x.setter
    def x(self, value: float):
        self.pos.x = value
        self.rect.centerx = round(value)

    @property
    def y(self) -> float:
        return self.pos.y

    @y.setter
    def y(self, value: float):
        self.pos.y = value
        self.rect.centery = round(value)

    @property
    def angle(self) -> float:
        """Rotation in degrees (0 = upright). Setting it re-renders the image."""
        return self._angle

    @angle.setter
    def angle(self, degrees: float):
        self._angle = degrees % 360
        center = self.rect.center
        self.image = pygame.transform.rotate(self._base_image, -self._angle)
        self.rect = self.image.get_rect(center=center)

    @property
    def width(self) -> int:
        return self.rect.width

    @property
    def height(self) -> int:
        return self.rect.height

    # ------------------------------------------------------------------ #
    # Movement
    # ------------------------------------------------------------------ #
    def move(self, dx: float, dy: float):
        """Shift the sprite by (dx, dy) pixels immediately."""
        self.pos.x += dx
        self.pos.y += dy
        self.sync_rect()
        return self

    def move_to(self, x, y=None):
        """Teleport the center to (x, y). Accepts a tuple/Vector2 too."""
        if y is None:
            x, y = utils._xy(x)
        self.pos.update(x, y)
        self.sync_rect()
        return self

    def set_velocity(self, vx: float, vy: float):
        self.velocity.update(vx, vy)
        return self

    def move_in_direction(self, direction, speed: Optional[float] = None):
        """Set velocity toward a direction vector (normalized) * speed."""
        speed = self.speed if speed is None else speed
        d = Vector2(direction)
        if d.length_squared() > 0:
            self.velocity = d.normalize() * speed
        return self

    def point_at(self, target):
        """Rotate the sprite to face ``target`` (a point or another sprite)."""
        tx, ty = _target_xy(target)
        self.angle = math.degrees(math.atan2(ty - self.pos.y, tx - self.pos.x))
        return self

    @property
    def facing(self) -> Vector2:
        """Unit vector in the direction the sprite is currently rotated."""
        return utils.vector_from_angle(self._angle, 1.0)

    def stop(self):
        self.velocity.update(0, 0)
        self.acceleration.update(0, 0)
        return self

    # ------------------------------------------------------------------ #
    # Per-frame update
    # ------------------------------------------------------------------ #
    def update(self, dt: float = 1 / 60, *args, **kwargs):
        """Integrate physics for ``dt`` seconds and sync the rect.

        Override this in subclasses for custom behavior; call
        ``super().update(dt)`` to keep the built-in motion.
        """
        # acceleration -> velocity
        self.velocity += self.acceleration * dt

        # friction (exponential decay toward zero — stable for any dt)
        if self.friction:
            self.velocity *= math.exp(-self.friction * dt)

        # clamp speed
        if self.max_speed is not None and self.velocity.length_squared() > self.max_speed ** 2:
            self.velocity.scale_to_length(self.max_speed)

        # velocity -> position
        self.pos += self.velocity * dt
        self.sync_rect()

    def sync_rect(self):
        """Snap the integer rect to the float position."""
        self.rect.center = (round(self.pos.x), round(self.pos.y))

    # ------------------------------------------------------------------ #
    # Appearance / lifecycle
    # ------------------------------------------------------------------ #
    def set_image(self, image: pygame.Surface, keep_angle: bool = True):
        """Swap the sprite's image, preserving center (and rotation)."""
        center = self.rect.center
        self._base_image = image
        if keep_angle and self._angle:
            self.image = pygame.transform.rotate(image, -self._angle)
        else:
            self.image = image
            self._angle = 0.0
        self.rect = self.image.get_rect(center=center)
        return self

    def draw(self, surface: pygame.Surface):
        """Blit this sprite onto ``surface`` (groups usually do this for you)."""
        surface.blit(self.image, self.rect)

    def distance_to(self, other) -> float:
        return self.pos.distance_to(Vector2(_target_xy(other)))

    def destroy(self):
        """Remove from all groups and mark as not alive."""
        self.alive_flag = False
        self.kill()


def _target_xy(target):
    """Accept a Sprite, Vector2, tuple, or rect-like and return (x, y)."""
    if isinstance(target, Sprite):
        return target.pos.x, target.pos.y
    if hasattr(target, "center"):  # a Rect
        return target.center
    return utils._xy(target)
