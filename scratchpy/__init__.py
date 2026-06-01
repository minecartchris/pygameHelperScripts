"""scratchpy — a small drag-and-drop, block-based coding environment built on
top of the ``pgkit`` pygame toolkit.

Run it with::

    python -m scratchpy        # from the repo root
    # or
    python scratchpy/main.py

Drag blocks out of the left palette, snap them under a hat block
("when ⚑ clicked"), edit the white number/text slots, then press ⚑ Run.
"""

from .blocks import Block, BlockDef, REGISTRY
from .editor import Editor
from .engine import Context, Engine
from .stage import Stage, StageSprite

__version__ = "0.1.0"

__all__ = [
    "Block", "BlockDef", "REGISTRY",
    "Editor", "Engine", "Context",
    "Stage", "StageSprite",
]
