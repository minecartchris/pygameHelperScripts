"""A small playable demo showing off pgkit.

Run from the repo root:   python examples/demo.py

Controls:
    WASD / arrow keys  – move the green player
    R                  – respawn coins
    Esc                – quit

Goal: grab the yellow coins. Red chasers follow you; blue balls bounce around.
"""

import os
import random
import sys

# Make 'pgkit' importable when running this file directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pgkit
from pgkit import Sprite, collision, movement, utils


class DemoScene(pgkit.Scene):
    def on_enter(self):
        w, h = self.app.size

        # Player
        self.player = Sprite(size=(36, 36), color=pgkit.GREEN, pos=(w / 2, h / 2))
        self.player.speed = 280
        self.player.friction = 8
        self.player.max_speed = 320

        # Coins to collect
        self.coins = pygame_group()
        self.spawn_coins(6)

        # Chasers that follow the player
        self.chasers = pygame_group()
        for _ in range(3):
            c = Sprite(size=(28, 28), color=pgkit.RED,
                       pos=(random.randint(0, w), random.randint(0, h)))
            self.chasers.add(c)

        # Bouncing balls
        self.balls = pygame_group()
        for _ in range(4):
            b = Sprite(size=(24, 24), color=pgkit.CYAN,
                       pos=(random.randint(50, w - 50), random.randint(50, h - 50)))
            b.velocity = pgkit.Vector2(random.uniform(-200, 200), random.uniform(-200, 200))
            self.balls.add(b)

        self.score = 0
        self.message = ""
        self.hit_timer = utils.Timer(0.6)

    def spawn_coins(self, n):
        w, h = self.app.size
        self.coins.empty()
        for _ in range(n):
            coin = Sprite(size=(18, 18), color=pgkit.YELLOW,
                          pos=(random.randint(30, w - 30), random.randint(30, h - 30)))
            self.coins.add(coin)

    def handle_event(self, event):
        import pygame
        if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            self.spawn_coins(6)

    def update(self, dt):
        if self.input.pressed("escape"):
            self.app.quit()

        # Player movement via input direction vector
        move = self.input.direction()
        if move.length_squared() > 0:
            self.player.acceleration = move * 1800
        else:
            self.player.acceleration = pgkit.Vector2(0, 0)
        self.player.update(dt)
        collision.keep_in_bounds(self.player, self.app.bounds)

        # Coins
        for coin in collision.collisions(self.player, self.coins):
            coin.destroy()
            self.score += 1
        if not self.coins:
            self.spawn_coins(6)

        # Chasers follow the player
        for chaser in self.chasers:
            movement.follow(chaser, self.player, speed=140, dt=dt)
            collision.keep_in_bounds(chaser, self.app.bounds)
            if collision.rect_collide(self.player, chaser):
                self.message = "Caught! -1"
                if not self.hit_timer.running:
                    self.score = max(0, self.score - 1)
                    self.hit_timer.start()
        self.hit_timer.update(dt)
        if not self.hit_timer.running:
            self.message = ""

        # Bouncing balls
        for ball in self.balls:
            ball.update(dt)
            collision.keep_in_bounds(ball, self.app.bounds, bounce=True)

    def draw(self, surface):
        for group in (self.coins, self.balls, self.chasers):
            group.draw(surface)
        self.player.draw(surface)

        utils.draw_text(surface, f"Score: {self.score}", (12, 10), size=30)
        utils.draw_text(surface, "WASD/arrows move · R respawn coins · Esc quit",
                        (12, self.app.height - 28), size=22, color=pgkit.LIGHT_GRAY)
        if self.message:
            utils.draw_text(surface, self.message, (self.app.width / 2, 40),
                            size=34, color=pgkit.ORANGE, anchor="midtop")


def pygame_group():
    import pygame
    return pygame.sprite.Group()


if __name__ == "__main__":
    app = pgkit.App(900, 600, title="pgkit demo", background=(28, 30, 44))
    app.run(DemoScene())
