"""The App: window creation, the main loop, timing, and a scene stack.

Minimal usage::

    import pgkit

    class MyGame(pgkit.Scene):
        def update(self, dt): ...
        def draw(self, surface): ...

    app = pgkit.App(800, 600, title="My Game")
    app.run(MyGame())
"""

from __future__ import annotations

from typing import List, Optional

import pygame

from .input import InputManager
from .scene import Scene


class App:
    """Owns the pygame window and runs the game loop over a stack of scenes."""

    def __init__(
        self,
        width: int = 800,
        height: int = 600,
        title: str = "pgkit game",
        fps: int = 60,
        background=(30, 30, 40),
        resizable: bool = False,
    ):
        pygame.init()
        flags = pygame.RESIZABLE if resizable else 0
        self.screen = pygame.display.set_mode((width, height), flags)
        pygame.display.set_caption(title)

        self.width = width
        self.height = height
        self.fps = fps
        self.background = background

        self.clock = pygame.time.Clock()
        self.input = InputManager()
        self.running = False
        self.dt = 0.0
        self.time = 0.0  # total seconds since run() started

        self._scenes: List[Scene] = []

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #
    @property
    def size(self):
        return (self.width, self.height)

    @property
    def bounds(self) -> pygame.Rect:
        """A Rect covering the whole window (handy for keep_in_bounds)."""
        return pygame.Rect(0, 0, self.width, self.height)

    @property
    def scene(self) -> Optional[Scene]:
        """The currently active (top) scene."""
        return self._scenes[-1] if self._scenes else None

    # ------------------------------------------------------------------ #
    # Scene stack
    # ------------------------------------------------------------------ #
    def set_scene(self, scene: Scene):
        """Replace the entire stack with a single scene."""
        while self._scenes:
            self.pop_scene()
        self.push_scene(scene)

    def push_scene(self, scene: Scene):
        """Put ``scene`` on top of the stack and activate it."""
        if self.scene:
            self.scene.on_exit()
        scene.app = self
        self._scenes.append(scene)
        scene.on_enter()

    def pop_scene(self):
        """Remove the top scene; re-enter the one beneath, if any."""
        if not self._scenes:
            return
        top = self._scenes.pop()
        top.on_exit()
        if self.scene:
            self.scene.on_enter()

    # ------------------------------------------------------------------ #
    # Main loop
    # ------------------------------------------------------------------ #
    def run(self, scene: Optional[Scene] = None):
        """Start the game loop. Optionally pass the first scene."""
        if scene is not None:
            self.set_scene(scene)
        if not self.scene:
            raise RuntimeError("App.run() needs a scene (pass one or call set_scene first).")

        self.running = True
        while self.running:
            self.dt = self.clock.tick(self.fps) / 1000.0
            self.time += self.dt

            self.input.begin_frame()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.width, self.height = event.w, event.h
                self.input.process(event)
                if self.scene:
                    self.scene.handle_event(event)

            if self.scene:
                self.scene.update(self.dt)

            self.screen.fill(self.background)
            if self.scene:
                self.scene.draw(self.screen)
            pygame.display.flip()

        pygame.quit()

    def quit(self):
        """Stop the loop after the current frame."""
        self.running = False
