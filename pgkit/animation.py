"""Sprite-sheet slicing and frame-based animation."""

from __future__ import annotations

from typing import List, Optional

import pygame


class SpriteSheet:
    """Wraps a single image and slices frames out of it."""

    def __init__(self, image: pygame.Surface):
        self.image = image

    def frame(self, x: int, y: int, w: int, h: int) -> pygame.Surface:
        """Grab one (w x h) frame at pixel offset (x, y)."""
        return self.image.subsurface(pygame.Rect(x, y, w, h)).copy()

    def grid(self, frame_w: int, frame_h: int, count: Optional[int] = None,
             start: int = 0) -> List[pygame.Surface]:
        """Slice the sheet into a left-to-right, top-to-bottom list of frames.

        ``count`` limits how many frames to return; ``start`` skips that many.
        """
        cols = self.image.get_width() // frame_w
        rows = self.image.get_height() // frame_h
        frames = []
        for index in range(cols * rows):
            cx = (index % cols) * frame_w
            cy = (index // cols) * frame_h
            frames.append(self.frame(cx, cy, frame_w, frame_h))
        frames = frames[start:]
        if count is not None:
            frames = frames[:count]
        return frames


class Animation:
    """Plays a list of frames at a given FPS.

    Example::

        anim = Animation(frames, fps=10, loop=True)
        ...
        anim.update(dt)
        sprite.set_image(anim.current)
    """

    def __init__(self, frames: List[pygame.Surface], fps: float = 10.0, loop: bool = True):
        if not frames:
            raise ValueError("Animation needs at least one frame")
        self.frames = frames
        self.fps = fps
        self.loop = loop
        self.index = 0
        self._acc = 0.0
        self.playing = True
        self.finished = False

    @property
    def current(self) -> pygame.Surface:
        return self.frames[self.index]

    def reset(self):
        self.index = 0
        self._acc = 0.0
        self.playing = True
        self.finished = False
        return self

    def update(self, dt: float) -> pygame.Surface:
        """Advance the animation by ``dt`` seconds; returns the current frame."""
        if not self.playing or self.fps <= 0:
            return self.current
        self._acc += dt
        frame_time = 1.0 / self.fps
        while self._acc >= frame_time:
            self._acc -= frame_time
            self.index += 1
            if self.index >= len(self.frames):
                if self.loop:
                    self.index = 0
                else:
                    self.index = len(self.frames) - 1
                    self.playing = False
                    self.finished = True
                    break
        return self.current
