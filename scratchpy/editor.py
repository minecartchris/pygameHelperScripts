"""The editor scene: palette, scripting canvas, drag-and-drop with snapping,
input editing, the stage panel, and the run/stop controls.

This is a ``pgkit.Scene`` so the whole thing rides on the pgkit game loop.
"""

from __future__ import annotations

import math
from typing import List, Optional

import pygame

import pgkit
from pgkit import utils

from . import render
from .blocks import (CATEGORY_COLORS, HAT, PALETTE_ORDER, Block, iter_tree)
from .engine import Context, Engine
from .stage import Stage, StageSprite

# regions
PALETTE_W = 232
STAGE_W = 320
STAGE_H = 280
TOOLBAR_H = 44

CANVAS_BG = (43, 47, 58)
PALETTE_BG = (30, 33, 41)


def key_name(event) -> Optional[str]:
    """Friendly key name from a KEYDOWN event, matching when_key block values."""
    special = {
        pygame.K_SPACE: "space",
        pygame.K_UP: "up", pygame.K_DOWN: "down",
        pygame.K_LEFT: "left", pygame.K_RIGHT: "right",
        pygame.K_RETURN: "enter",
    }
    if event.key in special:
        return special[event.key]
    if event.unicode and event.unicode.isprintable() and event.unicode.strip():
        return event.unicode.lower()
    return None


class Button:
    def __init__(self, rect, label, color):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.color = color

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect, border_radius=8)
        utils.draw_text(surface, self.label, self.rect.center, size=22,
                        color=(20, 20, 20), anchor="center")


class Editor(pgkit.Scene):
    def on_enter(self):
        w, h = self.app.size
        stage_rect = pygame.Rect(w - STAGE_W - 16, TOOLBAR_H + 16, STAGE_W, STAGE_H)
        self.stage = Stage(stage_rect)
        self.sprite = StageSprite(self.stage)
        self.ctx = Context(self.sprite, self.stage, None)
        self.engine = Engine(self.ctx)
        self.ctx.engine = self.engine

        self.scripts: List[Block] = []
        self.palette_scroll = 0
        self._build_palette()

        # drag / edit state
        self.drag_block: Optional[Block] = None
        self.drag_offset = (0, 0)
        self.drag_from_palette = False
        self.snap_target = None        # (mode, block)
        self.editing = None            # (block, slot_name)

        # toolbar buttons
        self.btn_flag = Button((w - STAGE_W - 16, 8, 110, 30), "⚑ Run", (90, 210, 110))
        self.btn_stop = Button((w - STAGE_W + 100, 8, 90, 30), "■ Stop", (230, 110, 110))
        self.btn_reset = Button((w - STAGE_W + 196, 8, 110, 30), "Reset", (200, 200, 210))

        # a friendly starter script
        self._add_starter()

    # ------------------------------------------------------------------ #
    def _build_palette(self):
        """One reusable prototype Block per kind, for drawing the palette."""
        self.palette_protos = [Block(kind) for kind in PALETTE_ORDER]

    def _add_starter(self):
        hat = Block("when_flag", PALETTE_W + 60, 80)
        mv = Block("move")
        turn = Block("turn_right")
        hat.next = mv
        mv.next = turn
        self.scripts.append(hat)

    # ------------------------------------------------------------------ #
    # Events
    # ------------------------------------------------------------------ #
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._on_press(event.pos)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._on_release(event.pos)
        elif event.type == pygame.MOUSEMOTION and self.drag_block:
            self._on_drag(event.pos)
        elif event.type == pygame.MOUSEWHEEL:
            mx, _ = pygame.mouse.get_pos()
            if mx < PALETTE_W:
                self.palette_scroll = min(0, self.palette_scroll + event.y * 40)
        elif event.type == pygame.KEYDOWN:
            self._on_key(event)

    def _on_press(self, pos):
        # toolbar
        if self.btn_flag.rect.collidepoint(pos):
            self.engine.start_flag(self.scripts); return
        if self.btn_stop.rect.collidepoint(pos):
            self.engine.stop(); self.sprite.say(""); return
        if self.btn_reset.rect.collidepoint(pos):
            self.engine.stop(); self.sprite.reset(); return

        # palette -> drag out a fresh block
        if pos[0] < PALETTE_W:
            self._pick_from_palette(pos); return

        self._commit_edit()

        # slot editing takes priority over dragging
        for root in self.scripts:
            render.layout_root(root)
            hit = render.slot_at(root, pos)
            if hit:
                self.editing = hit
                return

        # pick up a block (and everything below it)
        for root in reversed(self.scripts):  # topmost first
            block = render.block_at(root, pos)
            if block:
                self._pickup(block, pos)
                return

    def _on_drag(self, pos):
        self.drag_block.x = pos[0] - self.drag_offset[0]
        self.drag_block.y = pos[1] - self.drag_offset[1]
        self._update_snap()

    def _on_release(self, pos):
        if not self.drag_block:
            return
        dragged = self.drag_block
        self.drag_block = None

        # dropped on the palette -> trash it
        if pos[0] < PALETTE_W:
            if dragged in self.scripts:
                self.scripts.remove(dragged)
            self.snap_target = None
            return

        # try to snap (hats never snap under anything)
        if dragged.kind != "when_flag" and dragged.shape != HAT and self.snap_target:
            mode, target = self.snap_target
            if dragged in self.scripts:
                self.scripts.remove(dragged)
            if mode == "next":
                old = target.next
                target.next = dragged
                dragged.tail().next = old
            else:  # inner (C body)
                old = target.body
                target.body = dragged
                dragged.tail().next = old
        self.snap_target = None

    def _on_key(self, event):
        if self.editing:
            self._edit_key(event)
            return
        # otherwise, a key press may fire "when <key> pressed" scripts
        name = key_name(event)
        if name:
            self.engine.trigger_key(self.scripts, name)

    # ------------------------------------------------------------------ #
    # Drag helpers
    # ------------------------------------------------------------------ #
    def _pick_from_palette(self, pos):
        proto = self._palette_proto_at(pos)
        if not proto:
            return
        block = Block(proto.kind, pos[0] - 15, pos[1] - 15)
        self.scripts.append(block)
        self.drag_block = block
        self.drag_offset = (15, 15)
        self.drag_from_palette = True

    def _pickup(self, block, pos):
        parent, link = self._find_parent(block)
        if parent:
            if link == "next":
                parent.next = None
            else:
                parent.body = None
            block.x, block.y = block._rect.x, block._rect.y
            self.scripts.append(block)
        else:
            # already a root: bring to front
            self.scripts.remove(block)
            self.scripts.append(block)
        self.drag_block = block
        self.drag_offset = (pos[0] - block._rect.x, pos[1] - block._rect.y)
        self.drag_from_palette = False

    def _find_parent(self, target):
        for root in self.scripts:
            for b in iter_tree(root):
                if b.next is target:
                    return b, "next"
                if b.body is target:
                    return b, "body"
        return None, None

    def _update_snap(self):
        self.snap_target = None
        dragged = self.drag_block
        if dragged is None or dragged.kind == "when_flag" or dragged.shape == HAT:
            return
        render.layout_root(dragged)
        ax, ay = render.top_anchor(dragged)
        best, best_d = None, render.SNAP_DIST
        for root in self.scripts:
            if root is dragged:
                continue
            render.layout_root(root)
            for mode, b, (px, py) in render.connection_points(root):
                d = math.hypot(ax - px, ay - py)
                if d < best_d:
                    best_d = d
                    best = (mode, b)
        self.snap_target = best

    # ------------------------------------------------------------------ #
    # Slot editing
    # ------------------------------------------------------------------ #
    def _edit_key(self, event):
        block, name = self.editing
        cur = str(block.inputs.get(name, ""))
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
            self._commit_edit()
        elif event.key == pygame.K_BACKSPACE:
            block.inputs[name] = cur[:-1]
        elif event.unicode and event.unicode.isprintable():
            block.inputs[name] = cur + event.unicode

    def _commit_edit(self):
        self.editing = None

    # ------------------------------------------------------------------ #
    # Update
    # ------------------------------------------------------------------ #
    def update(self, dt):
        self.engine.step(dt)

    # ------------------------------------------------------------------ #
    # Drawing
    # ------------------------------------------------------------------ #
    def draw(self, surface):
        surface.fill(CANVAS_BG)

        # scripts (dragged one drawn last so it's on top)
        ordered = [s for s in self.scripts if s is not self.drag_block]
        if self.drag_block:
            ordered.append(self.drag_block)
        for root in ordered:
            render.layout_root(root)
            render.draw_tree(surface, root, self.editing)

        self._draw_snap_hint(surface)
        self._draw_palette(surface)
        self._draw_stage_panel(surface)

    def _draw_snap_hint(self, surface):
        if not self.snap_target:
            return
        mode, b = self.snap_target
        render.layout_root(b)
        if mode == "next":
            x, y = b._rect.x + render.NOTCH_X, b._full_bottom
        else:
            x, y = b._rect.x + render.C_INDENT + render.NOTCH_X, b._rect.bottom
        pygame.draw.rect(surface, (255, 255, 255),
                         (x - 2, y - 4, render.NOTCH_W + 4, 8), border_radius=4)

    def _draw_palette(self, surface):
        panel = pygame.Rect(0, 0, PALETTE_W, self.app.height)
        surface.fill(PALETTE_BG, panel)
        prev_clip = surface.get_clip()
        surface.set_clip(panel)

        y = 12 + self.palette_scroll
        last_cat = None
        self._palette_hitmap = []  # (proto, rect)
        for proto in self.palette_protos:
            if proto.category != last_cat:
                last_cat = proto.category
                utils.draw_text(surface, last_cat.upper(), (14, y), size=20,
                                color=CATEGORY_COLORS[last_cat])
                y += 26
            proto.x, proto.y = 14, y
            render.layout_root(proto)
            render.draw_block(surface, proto)
            self._palette_hitmap.append((proto, pygame.Rect(proto._rect)))
            y = proto._full_bottom + 8

        surface.set_clip(prev_clip)
        pygame.draw.line(surface, (15, 16, 20), (PALETTE_W, 0),
                         (PALETTE_W, self.app.height), 2)

    def _palette_proto_at(self, pos):
        for proto, rect in getattr(self, "_palette_hitmap", []):
            if rect.collidepoint(pos):
                return proto
        return None

    def _draw_stage_panel(self, surface):
        # toolbar background
        surface.fill((26, 28, 35), pygame.Rect(self.stage.rect.x - 8, 0,
                     self.app.width - self.stage.rect.x + 8, TOOLBAR_H + 8))
        self.btn_flag.draw(surface)
        self.btn_stop.draw(surface)
        self.btn_reset.draw(surface)

        self.stage.draw(surface, self.sprite)

        # little readout under the stage
        info = f"x: {self.sprite.sx:.0f}   y: {self.sprite.sy:.0f}   dir: {self.sprite.direction:.0f}"
        utils.draw_text(surface, info, (self.stage.rect.centerx, self.stage.rect.bottom + 10),
                        size=20, color=(200, 205, 215), anchor="midtop")
        status = "running" if self.engine.active else "stopped"
        utils.draw_text(surface, status, (self.stage.rect.centerx, self.stage.rect.bottom + 34),
                        size=18, color=(120, 200, 130) if self.engine.active else (140, 145, 155),
                        anchor="midtop")
