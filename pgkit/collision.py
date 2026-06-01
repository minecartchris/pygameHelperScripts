"""Collision detection and simple resolution helpers.

Everything here accepts either a :class:`~pgkit.sprite.Sprite`, a raw
``pygame.Rect``, or anything with a ``.rect`` attribute, so you can mix and
match freely.
"""

from __future__ import annotations

from typing import Iterable, List, Optional

import pygame
from pygame.math import Vector2

from .sprite import Sprite, _target_xy


def _rect_of(obj) -> pygame.Rect:
    if isinstance(obj, pygame.Rect):
        return obj
    if hasattr(obj, "rect"):
        return obj.rect
    raise TypeError(f"Cannot get a rect from {obj!r}")


# --------------------------------------------------------------------------- #
# Boolean tests
# --------------------------------------------------------------------------- #
def rect_collide(a, b) -> bool:
    """True if the two objects' rectangles overlap."""
    return _rect_of(a).colliderect(_rect_of(b))


def circle_collide(a, b, radius_a: Optional[float] = None, radius_b: Optional[float] = None) -> bool:
    """True if two circles overlap.

    If a radius isn't given it defaults to half the object's rect width.
    """
    ra = radius_a if radius_a is not None else _rect_of(a).width / 2
    rb = radius_b if radius_b is not None else _rect_of(b).width / 2
    ca = Vector2(_rect_of(a).center)
    cb = Vector2(_rect_of(b).center)
    return ca.distance_squared_to(cb) <= (ra + rb) ** 2


def point_in(point, obj) -> bool:
    """True if ``point`` lies inside the object's rect."""
    return _rect_of(obj).collidepoint(_target_xy(point))


# --------------------------------------------------------------------------- #
# Group queries
# --------------------------------------------------------------------------- #
def collides_with_any(obj, group: Iterable) -> Optional[object]:
    """Return the first member of ``group`` that ``obj`` overlaps, else None."""
    r = _rect_of(obj)
    for other in group:
        if other is obj:
            continue
        if r.colliderect(_rect_of(other)):
            return other
    return None


def collisions(obj, group: Iterable) -> List[object]:
    """Return *all* members of ``group`` that ``obj`` overlaps."""
    r = _rect_of(obj)
    return [o for o in group if o is not obj and r.colliderect(_rect_of(o))]


def overlapping_pairs(group: Iterable) -> List[tuple]:
    """Return every unique overlapping (a, b) pair within a single group."""
    items = list(group)
    hits = []
    for i, a in enumerate(items):
        ra = _rect_of(a)
        for b in items[i + 1:]:
            if ra.colliderect(_rect_of(b)):
                hits.append((a, b))
    return hits


# --------------------------------------------------------------------------- #
# Bounds
# --------------------------------------------------------------------------- #
def keep_in_bounds(sprite: Sprite, bounds: pygame.Rect, bounce: bool = False) -> List[str]:
    """Keep a sprite inside ``bounds``. Returns the sides it hit.

    With ``bounce=True`` the velocity is reflected on the axes that hit.
    Sides are any of ``"left" "right" "top" "bottom"``.
    """
    hit = []
    r = sprite.rect
    if r.left < bounds.left:
        sprite.pos.x += bounds.left - r.left
        hit.append("left")
    elif r.right > bounds.right:
        sprite.pos.x -= r.right - bounds.right
        hit.append("right")
    if r.top < bounds.top:
        sprite.pos.y += bounds.top - r.top
        hit.append("top")
    elif r.bottom > bounds.bottom:
        sprite.pos.y -= r.bottom - bounds.bottom
        hit.append("bottom")

    if hit:
        sprite.sync_rect()
        if bounce:
            if "left" in hit or "right" in hit:
                sprite.velocity.x *= -1
            if "top" in hit or "bottom" in hit:
                sprite.velocity.y *= -1
    return hit


def wrap_around(sprite: Sprite, bounds: pygame.Rect):
    """Teleport a sprite to the opposite edge when it leaves ``bounds`` (asteroids style)."""
    r = sprite.rect
    if r.right < bounds.left:
        sprite.pos.x = bounds.right + r.width / 2
    elif r.left > bounds.right:
        sprite.pos.x = bounds.left - r.width / 2
    if r.bottom < bounds.top:
        sprite.pos.y = bounds.bottom + r.height / 2
    elif r.top > bounds.bottom:
        sprite.pos.y = bounds.top - r.height / 2
    sprite.sync_rect()


# --------------------------------------------------------------------------- #
# Resolution (push-out)
# --------------------------------------------------------------------------- #
def resolve(sprite: Sprite, obstacle, bounce: bool = False) -> Optional[str]:
    """Push ``sprite`` out of ``obstacle`` along the axis of least penetration.

    Returns which side of ``sprite`` was pushed (``"left" "right" "top"
    "bottom"``) or None if they weren't overlapping. With ``bounce=True`` the
    relevant velocity component is reflected.
    """
    a = sprite.rect
    b = _rect_of(obstacle)
    if not a.colliderect(b):
        return None

    # overlap on each axis
    overlap_left = b.right - a.left     # push sprite right by this
    overlap_right = a.right - b.left    # push sprite left by this
    overlap_top = b.bottom - a.top      # push sprite down by this
    overlap_bottom = a.bottom - b.top   # push sprite up by this

    min_x = min(overlap_left, overlap_right)
    min_y = min(overlap_top, overlap_bottom)

    if min_x < min_y:
        if overlap_left < overlap_right:
            sprite.pos.x += overlap_left
            side = "left"
        else:
            sprite.pos.x -= overlap_right
            side = "right"
        if bounce:
            sprite.velocity.x *= -1
        else:
            sprite.velocity.x = 0
    else:
        if overlap_top < overlap_bottom:
            sprite.pos.y += overlap_top
            side = "top"
        else:
            sprite.pos.y -= overlap_bottom
            side = "bottom"
        if bounce:
            sprite.velocity.y *= -1
        else:
            sprite.velocity.y = 0

    sprite.sync_rect()
    return side
