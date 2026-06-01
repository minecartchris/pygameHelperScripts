"""Block geometry: measuring, laying out, drawing, hit-testing, and the
connection points the snapping logic uses.

A *layout pass* walks a script tree from its root and stamps each block with:
    ``block._rect``        – the header rectangle (where you grab it)
    ``block._items``       – resolved (label|slot) pieces for drawing
    ``block._slot_rects``  – name -> Rect for each editable input
    ``block._full_bottom`` – y where the next block in the chain begins
    ``block._inner_rect``  / ``block._bottom_rect`` – for C blocks
"""

from __future__ import annotations

from typing import List, Optional, Tuple

import pygame

import pgkit
from pgkit import utils

from .blocks import C, HAT, STACK, Block, iter_tree

# --- metrics --------------------------------------------------------------- #
FONT_SIZE = 20
ROW_H = 34
PAD = 12
GAP = 7
SLOT_MIN = 30
SLOT_PAD = 8
SLOT_H = 22
MIN_W = 80
C_INDENT = 18
C_BOTTOM = 14
EMPTY_BODY_H = 22
NOTCH_X = 16          # x offset of the top/bottom connection notch
NOTCH_W = 22
SNAP_DIST = 34        # how close a dragged stack must be to snap

TEXT_COLOR = (255, 255, 255)
SLOT_BG = (255, 255, 255)


def _font():
    return utils.get_font(FONT_SIZE)


def _shade(color, factor):
    return tuple(max(0, min(255, int(c * factor))) for c in color)


# --------------------------------------------------------------------------- #
# Measuring & layout
# --------------------------------------------------------------------------- #
def measure_header(block: Block) -> Tuple[int, list]:
    """Return (header_width, items) where items position each label/slot."""
    font = _font()
    x = PAD
    items = []
    for part in block.defn.parts:
        if part[0] == "label":
            tw = font.size(part[1])[0]
            items.append(("label", part[1], x, tw))
            x += tw + GAP
        else:  # num / text slot
            name = part[1]
            val = str(block.inputs.get(name, part[2]))
            tw = font.size(val)[0]
            w = max(SLOT_MIN, tw + SLOT_PAD * 2)
            items.append(("slot", name, x, w))
            x += w + GAP
    width = max(MIN_W, (x - GAP + PAD) if items else MIN_W)
    return width, items


def _place_items(block: Block, items: list):
    block._items = items
    block._slot_rects = {}
    for kind, key, relx, w in items:
        if kind == "slot":
            block._slot_rects[key] = pygame.Rect(
                block._rect.x + relx,
                block._rect.y + (ROW_H - SLOT_H) // 2,
                w, SLOT_H,
            )


def layout_stack(block: Optional[Block], x: float, y: float) -> float:
    """Lay out a chain of blocks downward. Returns the y below the last one."""
    cur = block
    while cur is not None:
        y = _layout_one(cur, x, y)
        cur = cur.next
    return y


def _layout_one(block: Block, x: float, y: float) -> float:
    width, items = measure_header(block)

    if block.shape == C:
        block._rect = pygame.Rect(x, y, width, ROW_H)
        _place_items(block, items)
        body_top = y + ROW_H
        if block.body:
            body_bottom = layout_stack(block.body, x + C_INDENT, body_top)
        else:
            body_bottom = body_top + EMPTY_BODY_H
        block._inner_rect = pygame.Rect(x, body_top, C_INDENT, body_bottom - body_top)
        block._bottom_rect = pygame.Rect(x, body_bottom, max(width, MIN_W), C_BOTTOM)
        block._full_bottom = body_bottom + C_BOTTOM
    else:
        block._rect = pygame.Rect(x, y, width, ROW_H)
        _place_items(block, items)
        block._inner_rect = None
        block._bottom_rect = None
        block._full_bottom = y + ROW_H

    return block._full_bottom


def layout_root(root: Block):
    """Lay out a whole script positioned at its stored (x, y)."""
    layout_stack(root, root.x, root.y)


# --------------------------------------------------------------------------- #
# Drawing
# --------------------------------------------------------------------------- #
def _draw_notch(surface, color, x, y):
    pygame.draw.rect(surface, color, (x + NOTCH_X, y - 4, NOTCH_W, 8),
                     border_radius=3)


def draw_block(surface, block: Block, editing_slot=None):
    """Draw a single block (header + body/bottom for C). Assumes layout done."""
    color = block.defn.color
    r = block._rect

    if block.shape == C:
        # header
        pygame.draw.rect(surface, color, r, border_radius=8)
        # left arm of the C
        ir = block._inner_rect
        pygame.draw.rect(surface, color, ir)
        # bottom bar
        br = block._bottom_rect
        pygame.draw.rect(surface, color, br, border_radius=8)
        _draw_notch(surface, _shade(color, 0.85), br.x, br.bottom)
    else:
        if block.shape == HAT:
            # rounded "hat" top
            pygame.draw.rect(surface, color, r, border_top_left_radius=16,
                             border_top_right_radius=16,
                             border_bottom_left_radius=6, border_bottom_right_radius=6)
        else:
            pygame.draw.rect(surface, color, r, border_radius=8)
            _draw_notch(surface, _shade(color, 0.85), r.x, r.bottom)

    # labels + slots
    font = _font()
    for kind, key, relx, w in block._items:
        if kind == "label":
            img = font.render(key, True, TEXT_COLOR)
            surface.blit(img, (r.x + relx, r.y + (ROW_H - img.get_height()) // 2))
        else:
            slot = block._slot_rects[key]
            border = (255, 210, 90) if editing_slot == (block, key) else (210, 215, 225)
            pygame.draw.rect(surface, SLOT_BG, slot, border_radius=10)
            pygame.draw.rect(surface, border, slot, 2, border_radius=10)
            val = str(block.inputs.get(key, ""))
            vimg = font.render(val, True, (30, 30, 40))
            surface.blit(vimg, (slot.x + SLOT_PAD,
                                slot.y + (slot.height - vimg.get_height()) // 2))


def draw_tree(surface, root: Block, editing_slot=None):
    for b in iter_tree(root):
        draw_block(surface, b, editing_slot)


# --------------------------------------------------------------------------- #
# Hit testing & connections
# --------------------------------------------------------------------------- #
def block_at(root: Block, pos) -> Optional[Block]:
    """Topmost block in this tree whose header (or C bottom bar) is under pos."""
    hit = None
    for b in iter_tree(root):
        if b._rect.collidepoint(pos):
            hit = b
        elif b._bottom_rect and b._bottom_rect.collidepoint(pos):
            hit = b
    return hit


def slot_at(root: Block, pos):
    """Return (block, slot_name) under pos, or None."""
    for b in iter_tree(root):
        for name, rect in b._slot_rects.items():
            if rect.collidepoint(pos):
                return b, name
    return None


def connection_points(root: Block):
    """Yield (mode, block, (px, py)) attach targets for a tree.

    ``mode`` is ``"next"`` (attach as the block's ``next``) or ``"inner"``
    (attach as a C-block's first ``body`` child).
    """
    for b in iter_tree(root):
        if b.shape in (STACK, HAT, C):
            yield ("next", b, (b._rect.x + NOTCH_X, b._full_bottom))
        if b.shape == C:
            yield ("inner", b, (b._rect.x + C_INDENT + NOTCH_X, b._rect.bottom))


def top_anchor(root: Block):
    """The connection point on top of a (just-laid-out) stack's first block."""
    return (root._rect.x + NOTCH_X, root._rect.y)
