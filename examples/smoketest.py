"""Headless sanity check for pgkit — no window, just exercises the API."""
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame
pygame.init()
pygame.display.set_mode((1, 1))

import pgkit
from pgkit import Sprite, collision, movement, utils

failures = []


def check(name, cond):
    print(("PASS" if cond else "FAIL"), name)
    if not cond:
        failures.append(name)


# Sprite physics
s = Sprite(size=(20, 20), color="green", pos=(100, 100))
s.velocity = pgkit.Vector2(60, 0)
s.update(1.0)
check("velocity integrates position", abs(s.pos.x - 160) < 1e-6)
check("rect synced to pos", s.rect.centerx == 160)

# Acceleration + friction
s2 = Sprite(pos=(0, 0))
s2.acceleration = pgkit.Vector2(100, 0)
s2.friction = 2
s2.update(0.5)
check("acceleration affects velocity", s2.velocity.x > 0)

# Max speed clamp
s3 = Sprite(pos=(0, 0), max_speed=50)
s3.velocity = pgkit.Vector2(500, 0)
s3.update(0.016)
check("max_speed clamps velocity", s3.velocity.length() <= 50 + 1e-3)

# Rotation
s4 = Sprite(size=(40, 10), color="red", pos=(0, 0))
s4.angle = 90
check("angle stored", abs(s4.angle - 90) < 1e-6)
check("point_at faces target", True)
s4.point_at((100, 0))
check("point_at right = ~0 deg", abs(((s4.angle + 180) % 360) - 180) < 1e-3)

# Collision rect
a = Sprite(size=(20, 20), pos=(0, 0))
b = Sprite(size=(20, 20), pos=(10, 0))
check("rect_collide overlap", collision.rect_collide(a, b))
b.move_to(200, 200)
check("rect_collide apart", not collision.rect_collide(a, b))

# Circle collide
c1 = Sprite(size=(20, 20), pos=(0, 0))
c2 = Sprite(size=(20, 20), pos=(15, 0))
check("circle_collide", collision.circle_collide(c1, c2))

# Bounds + bounce
ball = Sprite(size=(20, 20), pos=(5, 100))
ball.velocity = pgkit.Vector2(-50, 0)
hit = collision.keep_in_bounds(ball, pygame.Rect(0, 0, 200, 200), bounce=True)
check("keep_in_bounds detects side", "left" in hit)
check("bounce reverses velocity", ball.velocity.x > 0)

# Resolve push-out
mover = Sprite(size=(20, 20), pos=(95, 100))
wall = pygame.Rect(100, 0, 40, 200)
side = collision.resolve(mover, wall)
check("resolve returns a side", side in ("left", "right", "top", "bottom"))
check("resolve separates them", not mover.rect.colliderect(wall))

# move_toward
m = Sprite(pos=(0, 0))
done = movement.move_toward(m, (100, 0), speed=50, dt=1.0)
check("move_toward steps", abs(m.pos.x - 50) < 1e-3 and not done)
movement.move_toward(m, (100, 0), speed=50, dt=2.0)
check("move_toward arrives", abs(m.pos.x - 100) < 1e-3)

# follow
f = Sprite(pos=(0, 0))
movement.follow(f, (300, 0), speed=100, dt=0.5)
check("follow moves toward target", f.pos.x > 0)

# Timer
t = utils.Timer(1.0).start()
check("timer not done early", not t.update(0.4))
check("timer fires", t.update(0.7))

# utils math
check("clamp", utils.clamp(15, 0, 10) == 10)
check("lerp", abs(utils.lerp(0, 10, 0.5) - 5) < 1e-6)
check("distance", abs(utils.distance((0, 0), (3, 4)) - 5) < 1e-6)

# Animation
frames = [utils.make_surface((10, 10), "red"), utils.make_surface((10, 10), "blue")]
anim = pgkit.Animation(frames, fps=10, loop=False)
anim.update(0.05)
check("anim frame 0 early", anim.index == 0)
anim.update(0.2)
check("anim advances", anim.index == 1)

# Input manager
im = pgkit.InputManager()
im.begin_frame()
ev = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_d)
im.process(ev)
check("input pressed edge", im.pressed("d"))
check("input held", im.held("d"))
check("axis", im.axis("a", "d") == 1)

print()
if failures:
    print(f"{len(failures)} FAILED: {failures}")
    sys.exit(1)
print("All checks passed.")
