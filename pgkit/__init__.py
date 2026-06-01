"""pgkit — a small toolkit that makes pygame game dev a lot easier.

Quick start::

    import pgkit
    from pgkit import Sprite, collision, movement

    class Game(pgkit.Scene):
        def on_enter(self):
            self.player = Sprite(size=(40, 40), color="green", pos=(400, 300))
            self.player.speed = 250

        def update(self, dt):
            self.player.move_in_direction(self.input.direction(), self.player.speed)
            self.player.update(dt)
            collision.keep_in_bounds(self.player, self.app.bounds)

        def draw(self, surface):
            self.player.draw(surface)

    pgkit.App(800, 600, title="Hello pgkit").run(Game())

The submodules ``collision``, ``movement``, ``utils`` and ``constants`` hold
the helper functions; everything else is exported at the top level.
"""

from pygame.math import Vector2  # re-exported for convenience

from . import collision, constants, movement, utils
from .animation import Animation, SpriteSheet
from .app import App
from .input import InputManager
from .scene import Scene
from .sprite import Sprite

# Bring the color/direction constants up to the top level (pgkit.RED, pgkit.UP, …)
from .constants import *  # noqa: F401,F403

__version__ = "0.1.0"

Game = App  # friendly alias

__all__ = [
    "App",
    "Game",
    "Scene",
    "Sprite",
    "InputManager",
    "Animation",
    "SpriteSheet",
    "Vector2",
    "collision",
    "movement",
    "utils",
    "constants",
]
