"""Block data model, the block definition registry, and block behaviors.

A *block* is one instruction tile. Blocks link together:
    ``block.next``  – the block directly below it in a stack
    ``block.body``  – the first block nested inside a C-block (repeat/forever)

A *script* is a tree rooted at a hat block (an event like "when flag clicked").

Each block kind is described by a :class:`BlockDef` which knows the block's
category (for color), its shape, the label/input layout, and a generator
function (``run``) describing what it does at runtime. Generators let control
blocks pause between frames (``wait``, ``repeat``, ``forever``).
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Union

# --- categories & their colors -------------------------------------------- #
CATEGORY_COLORS = {
    "events": (255, 191, 64),
    "motion": (76, 151, 255),
    "looks": (153, 102, 255),
    "control": (255, 171, 25),
}

# Part descriptors used in BlockDef.parts:
#   ("label", "move")            -> static text
#   ("num", "steps", 10)         -> numeric input slot (name, default)
#   ("text", "msg", "Hello!")    -> text input slot (name, default)
LabelPart = tuple

# shapes
HAT = "hat"      # rounded top, event trigger (no top notch)
STACK = "stack"  # normal command
C = "c"          # wraps a body (repeat / forever / if)


@dataclass
class BlockDef:
    kind: str
    category: str
    shape: str
    parts: List[LabelPart]
    # run(block, ctx, run_stack) -> generator that yields between frames
    run: Optional[Callable] = None

    @property
    def color(self):
        return CATEGORY_COLORS[self.category]

    def default_inputs(self) -> dict:
        out = {}
        for part in self.parts:
            if part[0] in ("num", "text"):
                out[part[1]] = part[2]
        return out


REGISTRY: dict[str, BlockDef] = {}
PALETTE_ORDER: List[str] = []  # kinds in the order they appear in the palette


def define(kind, category, shape, parts, run=None):
    bd = BlockDef(kind, category, shape, parts, run)
    REGISTRY[kind] = bd
    PALETTE_ORDER.append(kind)
    return bd


_ids = itertools.count(1)


class Block:
    """A live instance of a block placed in the editor."""

    def __init__(self, kind: str, x: float = 0, y: float = 0):
        self.id = next(_ids)
        self.kind = kind
        self.defn = REGISTRY[kind]
        self.inputs = dict(self.defn.default_inputs())
        self.next: Optional[Block] = None
        self.body: Optional[Block] = None  # only meaningful for C blocks
        self.x = x          # top-left, only used when this block is a root
        self.y = y
        self._rect = None   # filled in by the layout pass (pygame.Rect)
        self._slot_rects: dict = {}  # input name -> pygame.Rect (layout pass)

    # --- input access ---
    def num(self, name: str, default: float = 0.0) -> float:
        try:
            return float(self.inputs.get(name, default))
        except (TypeError, ValueError):
            return default

    def text(self, name: str, default: str = "") -> str:
        return str(self.inputs.get(name, default))

    @property
    def category(self):
        return self.defn.category

    @property
    def shape(self):
        return self.defn.shape

    def tail(self) -> "Block":
        """The last block in this block's own ``next`` chain."""
        b = self
        while b.next:
            b = b.next
        return b

    def iter_chain(self):
        """Yield this block and every block below it via ``next``."""
        b = self
        while b:
            yield b
            b = b.next

    def __repr__(self):
        return f"<Block {self.kind}#{self.id}>"


def iter_tree(root: Block):
    """Yield every block in a script tree (chain + nested bodies)."""
    for b in root.iter_chain():
        yield b
        if b.body:
            yield from iter_tree(b.body)


def detach_tail_count(root: Block) -> int:
    return sum(1 for _ in iter_tree(root))


# --------------------------------------------------------------------------- #
# Behaviors
# --------------------------------------------------------------------------- #
# Each is a generator. Plain command blocks usually just act and `return`
# (yielding nothing). Control blocks yield to release the frame.

def _move(block, ctx, run_stack):
    ctx.sprite.move_steps(block.num("steps", 10))
    return
    yield  # pragma: no cover (makes this a generator)


def _turn_right(block, ctx, run_stack):
    ctx.sprite.turn(block.num("deg", 15))
    return
    yield


def _turn_left(block, ctx, run_stack):
    ctx.sprite.turn(-block.num("deg", 15))
    return
    yield


def _goto(block, ctx, run_stack):
    ctx.sprite.goto(block.num("x", 0), block.num("y", 0))
    return
    yield


def _point(block, ctx, run_stack):
    ctx.sprite.direction = block.num("dir", 90)
    return
    yield


def _change_x(block, ctx, run_stack):
    ctx.sprite.goto(ctx.sprite.sx + block.num("dx", 10), ctx.sprite.sy)
    return
    yield


def _change_y(block, ctx, run_stack):
    ctx.sprite.goto(ctx.sprite.sx, ctx.sprite.sy + block.num("dy", 10))
    return
    yield


def _bounce(block, ctx, run_stack):
    ctx.sprite.bounce_on_edge()
    return
    yield


def _say(block, ctx, run_stack):
    ctx.sprite.say(block.text("msg", "Hello!"))
    return
    yield


def _change_size(block, ctx, run_stack):
    ctx.sprite.size_pct += block.num("amt", 10)
    return
    yield


def _set_size(block, ctx, run_stack):
    ctx.sprite.size_pct = block.num("pct", 100)
    return
    yield


def _wait(block, ctx, run_stack):
    remaining = block.num("secs", 1)
    while remaining > 0:
        yield
        remaining -= ctx.dt


def _repeat(block, ctx, run_stack):
    times = int(block.num("times", 10))
    for _ in range(times):
        yield from run_stack(block.body, ctx)
        yield  # one frame per loop so motion is visible & never hard-locks


def _forever(block, ctx, run_stack):
    while True:
        yield from run_stack(block.body, ctx)
        yield


# --------------------------------------------------------------------------- #
# Block definitions (this list is also the palette order)
# --------------------------------------------------------------------------- #
# Events
define("when_flag", "events", HAT, [("label", "when ⚑ clicked")])
define("when_key", "events", HAT,
       [("label", "when"), ("text", "key", "space"), ("label", "key pressed")])

# Motion
define("move", "motion", STACK,
       [("label", "move"), ("num", "steps", 10), ("label", "steps")], _move)
define("turn_right", "motion", STACK,
       [("label", "turn ↻"), ("num", "deg", 15), ("label", "degrees")], _turn_right)
define("turn_left", "motion", STACK,
       [("label", "turn ↺"), ("num", "deg", 15), ("label", "degrees")], _turn_left)
define("goto", "motion", STACK,
       [("label", "go to x"), ("num", "x", 0), ("label", "y"), ("num", "y", 0)], _goto)
define("point", "motion", STACK,
       [("label", "point in direction"), ("num", "dir", 90)], _point)
define("change_x", "motion", STACK,
       [("label", "change x by"), ("num", "dx", 10)], _change_x)
define("change_y", "motion", STACK,
       [("label", "change y by"), ("num", "dy", 10)], _change_y)
define("bounce", "motion", STACK,
       [("label", "if on edge, bounce")], _bounce)

# Looks
define("say", "looks", STACK,
       [("label", "say"), ("text", "msg", "Hello!")], _say)
define("change_size", "looks", STACK,
       [("label", "change size by"), ("num", "amt", 10)], _change_size)
define("set_size", "looks", STACK,
       [("label", "set size to"), ("num", "pct", 100), ("label", "%")], _set_size)

# Control
define("wait", "control", STACK,
       [("label", "wait"), ("num", "secs", 1), ("label", "seconds")], _wait)
define("repeat", "control", C,
       [("label", "repeat"), ("num", "times", 10)], _repeat)
define("forever", "control", C, [("label", "forever")], _forever)
