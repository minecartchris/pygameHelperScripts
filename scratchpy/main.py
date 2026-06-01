"""Entry point for the scratchpy block-coding environment."""

import os
import sys

# Make the repo root importable so 'pgkit' and 'scratchpy' resolve when this
# file is run directly (python scratchpy/main.py).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pgkit
from scratchpy.editor import Editor


def main():
    app = pgkit.App(1280, 760, title="scratchpy · block coding", background=(43, 47, 58))
    app.run(Editor())


if __name__ == "__main__":
    main()
