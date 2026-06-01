"""The script engine: turns block trees into running coroutines.

Every script (hat + the stack below it) becomes a *thread* — a Python generator
that runs a little each frame and yields to release control. This is what makes
``wait``, ``repeat`` and ``forever`` cooperate instead of freezing the window.
"""

from __future__ import annotations

from typing import Iterable, List, Optional

from .blocks import Block


class Context:
    """Shared runtime state handed to every block behavior."""

    def __init__(self, sprite, stage, engine):
        self.sprite = sprite
        self.stage = stage
        self.engine = engine
        self.dt = 1 / 60  # refreshed each frame by the engine


def run_stack(block: Optional[Block], ctx: Context):
    """Run a chain of blocks top to bottom, descending into each behavior.

    This is a generator; it yields whenever a block wants to wait a frame.
    """
    while block is not None:
        if not ctx.engine.running:
            return
        run = block.defn.run
        if run is not None:
            yield from run(block, ctx, run_stack)
        block = block.next


class Thread:
    """One running script."""

    def __init__(self, root: Block, ctx: Context):
        self.root = root
        self.gen = run_stack(root.next, ctx)  # skip the hat itself
        self.done = False

    def step(self):
        if self.done:
            return
        try:
            next(self.gen)
        except StopIteration:
            self.done = True
        except Exception as exc:  # a bad block shouldn't kill the whole app
            print(f"[script error] {self.root.kind}: {exc}")
            self.done = True


class Engine:
    """Owns the running threads and steps them each frame."""

    def __init__(self, ctx: Context):
        self.ctx = ctx
        self.threads: List[Thread] = []
        self.running = False

    @property
    def active(self) -> bool:
        return self.running and any(not t.done for t in self.threads)

    def start_flag(self, roots: Iterable[Block]):
        """Green-flag: launch every ``when ⚑ clicked`` script from the top."""
        self.stop()
        self.running = True
        for root in roots:
            if root.kind == "when_flag":
                self.threads.append(Thread(root, self.ctx))

    def trigger_key(self, roots: Iterable[Block], key_name: str):
        """Launch ``when <key> pressed`` scripts matching ``key_name``."""
        if not self.running:
            self.running = True
        for root in roots:
            if root.kind == "when_key" and root.text("key", "").strip().lower() == key_name.lower():
                self.threads.append(Thread(root, self.ctx))

    def step(self, dt: float):
        if not self.running:
            return
        self.ctx.dt = dt
        for t in list(self.threads):
            t.step()
        self.threads = [t for t in self.threads if not t.done]
        if not self.threads:
            self.running = False

    def stop(self):
        self.threads.clear()
        self.running = False
