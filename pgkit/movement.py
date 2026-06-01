"""Movement behaviors you can call on a sprite each frame.

These are plain functions (not methods) so they compose freely and work on
any :class:`~pgkit.sprite.Sprite`. Call them inside your update loop.
"""

from __future__ import annotations

import math
from typing import Optional

from pygame.math import Vector2

from . import utils
from .sprite import Sprite, _target_xy


def move_toward(sprite: Sprite, target, speed: float, dt: float, stop_distance: float = 1.0) -> bool:
    """Step a sprite toward ``target`` at ``speed`` px/sec.

    Returns True once it's within ``stop_distance`` (and snaps it there).
    """
    target = Vector2(_target_xy(target))
    offset = target - sprite.pos
    dist = offset.length()
    step = speed * dt
    if dist <= stop_distance or dist <= step:
        sprite.move_to(target)
        return True
    sprite.pos += offset.normalize() * step
    sprite.sync_rect()
    return False


def follow(sprite: Sprite, target, speed: float, dt: float, keep_distance: float = 0.0):
    """Continuously chase ``target`` (e.g. an enemy following the player).

    ``keep_distance`` makes the sprite stop short rather than overlap.
    """
    target = Vector2(_target_xy(target))
    offset = target - sprite.pos
    dist = offset.length()
    if dist <= keep_distance or dist == 0:
        return
    sprite.velocity = offset.normalize() * speed
    sprite.pos += sprite.velocity * dt
    sprite.sync_rect()


def flee(sprite: Sprite, threat, speed: float, dt: float):
    """Move directly away from ``threat``."""
    threat = Vector2(_target_xy(threat))
    offset = sprite.pos - threat
    if offset.length_squared() == 0:
        return
    sprite.velocity = offset.normalize() * speed
    sprite.pos += sprite.velocity * dt
    sprite.sync_rect()


def orbit(sprite: Sprite, center, radius: float, angular_speed: float, dt: float):
    """Move a sprite around ``center`` in a circle. ``angular_speed`` in deg/sec."""
    center = Vector2(_target_xy(center))
    current = sprite.pos - center
    angle = math.degrees(math.atan2(current.y, current.x)) + angular_speed * dt
    sprite.move_to(center + utils.vector_from_angle(angle, radius))


def apply_gravity(sprite: Sprite, dt: float, gravity: float = 800.0, terminal: float = 1200.0):
    """Accelerate a sprite downward; caps fall speed at ``terminal``."""
    sprite.velocity.y = min(sprite.velocity.y + gravity * dt, terminal)


def patrol(sprite: Sprite, point_a, point_b, speed: float, dt: float):
    """Bounce a sprite back and forth between two points forever.

    Stores progress on the sprite via ``_patrol_target``.
    """
    a = Vector2(_target_xy(point_a))
    b = Vector2(_target_xy(point_b))
    target = getattr(sprite, "_patrol_target", b)
    if move_toward(sprite, target, speed, dt):
        sprite._patrol_target = a if target == b else b


def smooth_follow(sprite: Sprite, target, dt: float, smoothing: float = 8.0):
    """Ease a sprite toward ``target`` (nice for cameras). Higher = snappier."""
    target = Vector2(_target_xy(target))
    t = utils.clamp(smoothing * dt, 0.0, 1.0)
    sprite.move_to(sprite.pos.lerp(target, t))
