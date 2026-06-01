"""Pong, built with pgkit.

Run from the repo root:   python examples/pong.py

Menu:   Up/Down (or 1/2/3) to pick difficulty, Enter to start.
Game:   W/S or Up/Down move your paddle (left).  Esc returns to menu.
First to 7 points wins.
"""

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame
import pgkit
from pgkit import Sprite, collision, utils


WIDTH, HEIGHT = 900, 600
WIN_SCORE = 7

# difficulty -> (ai_speed px/s, base ball speed, ai aim error px)
DIFFICULTIES = {
    "Easy":   dict(ai_speed=190, ball_speed=300, ai_error=45),
    "Medium": dict(ai_speed=320, ball_speed=430, ai_error=20),
    "Hard":   dict(ai_speed=470, ball_speed=560, ai_error=7),
}
ORDER = ["Easy", "Medium", "Hard"]


class MenuScene(pgkit.Scene):
    def on_enter(self):
        self.selected = 1  # default Medium

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_UP, pygame.K_w):
            self.selected = (self.selected - 1) % len(ORDER)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.selected = (self.selected + 1) % len(ORDER)
        elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
            self.selected = event.key - pygame.K_1
            self.start()
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.start()
        elif event.key == pygame.K_ESCAPE:
            self.app.quit()

    def start(self):
        self.go_to(PongScene(ORDER[self.selected]))

    def draw(self, surface):
        utils.draw_text(surface, "PONG", (WIDTH / 2, 110), size=96,
                        color=pgkit.WHITE, anchor="center")
        utils.draw_text(surface, "Select difficulty", (WIDTH / 2, 200), size=32,
                        color=pgkit.LIGHT_GRAY, anchor="center")
        for i, name in enumerate(ORDER):
            chosen = i == self.selected
            color = pgkit.YELLOW if chosen else pgkit.GRAY
            label = f"> {name} <" if chosen else name
            utils.draw_text(surface, label, (WIDTH / 2, 280 + i * 60),
                            size=44, color=color, anchor="center")
        utils.draw_text(surface, "Up/Down + Enter  ·  or press 1/2/3  ·  Esc quits",
                        (WIDTH / 2, HEIGHT - 40), size=22,
                        color=pgkit.DARK_GRAY, anchor="center")


class PongScene(pgkit.Scene):
    def __init__(self, difficulty):
        super().__init__()
        self.difficulty = difficulty
        self.cfg = DIFFICULTIES[difficulty]

    def on_enter(self):
        margin = 40
        self.player = Sprite(size=(16, 110), color=pgkit.WHITE,
                             pos=(margin, HEIGHT / 2))
        self.player.speed = 460

        self.ai = Sprite(size=(16, 110), color=pgkit.WHITE,
                         pos=(WIDTH - margin, HEIGHT / 2))

        self.ball = Sprite(size=(18, 18), color=pgkit.YELLOW,
                           pos=(WIDTH / 2, HEIGHT / 2))

        self.player_score = 0
        self.ai_score = 0
        self.winner = None
        self.serve_timer = utils.Timer(1.0).start()
        self.pending_dir = random.choice((-1, 1))

    # ------------------------------------------------------------------ #
    def serve(self, direction):
        self.ball.move_to(WIDTH / 2, HEIGHT / 2)
        angle = random.uniform(-35, 35)
        vec = utils.vector_from_angle(angle, self.cfg["ball_speed"])
        vec.x *= direction
        self.ball.velocity = vec

    def update(self, dt):
        if self.input.pressed("escape"):
            self.go_to(MenuScene())
            return

        if self.winner:
            if self.input.pressed("return") or self.input.pressed("space"):
                self.go_to(MenuScene())
            return

        # serve delay between points
        if self.serve_timer.running:
            if self.serve_timer.update(dt):
                self.serve(self.pending_dir)
            return

        self._move_player(dt)
        self._move_ai(dt)
        self._move_ball(dt)

    def _move_player(self, dt):
        move = self.input.axis("up", "down") + self.input.axis("w", "s")
        move = max(-1, min(1, move))
        self.player.pos.y += move * self.player.speed * dt
        self.player.sync_rect()
        collision.keep_in_bounds(self.player, self.app.bounds)

    def _move_ai(self, dt):
        # Track the ball, but only react when it's heading our way, and with
        # an error margin that shrinks with difficulty.
        if self.ball.velocity.x > 0:
            target_y = self.ball.pos.y + random.uniform(-1, 1) * self.cfg["ai_error"]
        else:
            target_y = HEIGHT / 2  # recenter when ball is moving away
        diff = target_y - self.ai.pos.y
        step = self.cfg["ai_speed"] * dt
        self.ai.pos.y += max(-step, min(step, diff))
        self.ai.sync_rect()
        collision.keep_in_bounds(self.ai, self.app.bounds)

    def _move_ball(self, dt):
        self.ball.update(dt)
        r = self.ball.rect

        # top / bottom walls
        if r.top <= 0:
            self.ball.pos.y += -r.top
            self.ball.velocity.y = abs(self.ball.velocity.y)
            self.ball.sync_rect()
        elif r.bottom >= HEIGHT:
            self.ball.pos.y -= r.bottom - HEIGHT
            self.ball.velocity.y = -abs(self.ball.velocity.y)
            self.ball.sync_rect()

        # paddles
        if self.ball.velocity.x < 0 and collision.rect_collide(self.ball, self.player):
            self._bounce_off(self.player, going_right=True)
        elif self.ball.velocity.x > 0 and collision.rect_collide(self.ball, self.ai):
            self._bounce_off(self.ai, going_right=False)

        # scoring
        if r.right < 0:
            self.ai_score += 1
            self._after_point(direction=-1)
        elif r.left > WIDTH:
            self.player_score += 1
            self._after_point(direction=1)

    def _bounce_off(self, paddle, going_right):
        # Reflect horizontally, nudge out of the paddle, and add "english"
        # based on where the ball struck the paddle face.
        offset = (self.ball.pos.y - paddle.pos.y) / (paddle.height / 2)  # -1..1
        offset = utils.clamp(offset, -1, 1)
        speed = self.ball.velocity.length() * 1.04  # speed up a touch each hit
        angle = offset * 55  # degrees from horizontal
        vec = utils.vector_from_angle(angle, speed)
        vec.x = abs(vec.x) if going_right else -abs(vec.x)
        self.ball.velocity = vec
        # push ball clear of the paddle so it can't get stuck inside
        if going_right:
            self.ball.x = paddle.rect.right + self.ball.width / 2
        else:
            self.ball.x = paddle.rect.left - self.ball.width / 2

    def _after_point(self, direction):
        self.ball.stop()
        self.ball.move_to(WIDTH / 2, HEIGHT / 2)
        if self.player_score >= WIN_SCORE:
            self.winner = "You win!"
        elif self.ai_score >= WIN_SCORE:
            self.winner = "CPU wins!"
        else:
            self.pending_dir = direction
            self.serve_timer.start()

    # ------------------------------------------------------------------ #
    def draw(self, surface):
        # center net
        for y in range(0, HEIGHT, 30):
            pygame.draw.rect(surface, pgkit.DARK_GRAY, (WIDTH // 2 - 2, y + 5, 4, 18))

        self.player.draw(surface)
        self.ai.draw(surface)
        self.ball.draw(surface)

        utils.draw_text(surface, str(self.player_score), (WIDTH / 2 - 80, 30),
                        size=64, color=pgkit.WHITE, anchor="midtop")
        utils.draw_text(surface, str(self.ai_score), (WIDTH / 2 + 80, 30),
                        size=64, color=pgkit.WHITE, anchor="midtop")
        utils.draw_text(surface, self.difficulty, (WIDTH / 2, 18),
                        size=24, color=pgkit.GRAY, anchor="midtop")

        if self.winner:
            utils.draw_text(surface, self.winner, (WIDTH / 2, HEIGHT / 2 - 20),
                            size=72, color=pgkit.YELLOW, anchor="center")
            utils.draw_text(surface, "Enter / Space for menu",
                            (WIDTH / 2, HEIGHT / 2 + 50), size=28,
                            color=pgkit.LIGHT_GRAY, anchor="center")


if __name__ == "__main__":
    app = pgkit.App(WIDTH, HEIGHT, title="pgkit · Pong", background=(15, 18, 28))
    app.run(MenuScene())
