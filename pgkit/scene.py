"""Scenes are self-contained game screens (menu, level, game-over, ...).

Subclass :class:`Scene`, override the hooks you care about, and hand it to the
:class:`~pgkit.app.App`. The App calls these for you every frame.
"""

from __future__ import annotations

import pygame


class Scene:
    """Base class for a game screen.

    Lifecycle hooks (all optional to override):
        ``on_enter()``  – called once when the scene becomes active
        ``on_exit()``   – called once when it's removed/covered
        ``handle_event(event)`` – per pygame event
        ``update(dt)``  – per frame logic (dt = seconds since last frame)
        ``draw(surface)`` – per frame rendering

    Useful attributes set by the App when the scene starts:
        ``self.app``    – the owning App (access ``app.input``, ``app.size`` …)
    """

    def __init__(self):
        self.app = None  # set by App.set_scene / push_scene

    # --- lifecycle ---
    def on_enter(self):
        pass

    def on_exit(self):
        pass

    # --- per frame ---
    def handle_event(self, event: pygame.event.Event):
        pass

    def update(self, dt: float):
        pass

    def draw(self, surface: pygame.Surface):
        pass

    # --- convenience ---
    @property
    def input(self):
        return self.app.input if self.app else None

    def go_to(self, scene: "Scene"):
        """Replace this scene with another."""
        self.app.set_scene(scene)

    def push(self, scene: "Scene"):
        """Overlay another scene on top (e.g. a pause menu)."""
        self.app.push_scene(scene)

    def pop(self):
        """Return to the scene beneath this one."""
        self.app.pop_scene()
