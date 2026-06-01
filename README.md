# pgkit — a pygame toolkit

A small library that takes the boilerplate out of pygame: a smarter sprite
class, collision & movement helpers, a polled input manager, scenes, a ready-made
game loop, and frame animation.

> Requires `pygame` (tested on 2.6.1, Python 3.11).
> `pip install pygame`

## Hello world

```python
import pgkit
from pgkit import Sprite, collision

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
```

Run the examples:

```
python examples/demo.py    # movement, collisions, chasers, bouncing balls
python examples/pong.py    # full Pong with Easy/Medium/Hard difficulty
```

## What's inside

### `App` — window + game loop + scene stack
```python
app = pgkit.App(width=800, height=600, title="...", fps=60, background=(30,30,40))
app.run(MyScene())
```
- `app.input` — the shared `InputManager`
- `app.bounds` — a `Rect` covering the window (great for `keep_in_bounds`)
- `app.dt`, `app.time` — frame delta / total seconds
- Scene stack: `app.push_scene()`, `app.pop_scene()`, `app.set_scene()` (overlays like pause menus work)
- `app.quit()` to stop the loop

### `Scene` — a game screen
Subclass and override any of: `on_enter()`, `on_exit()`, `handle_event(event)`,
`update(dt)`, `draw(surface)`. Inside, use `self.input`, `self.app`, and
`self.go_to() / self.push() / self.pop()` to switch scenes.

### `Sprite` — float position + physics
```python
s = Sprite(image=surf, pos=(100, 100))          # from an image
s = Sprite(size=(32, 32), color="red", pos=...)  # placeholder block
```
- `s.pos` (Vector2 center, float), `s.velocity`, `s.acceleration`
- `s.speed`, `s.max_speed`, `s.friction`
- `s.move(dx,dy)`, `s.move_to(x,y)`, `s.move_in_direction(vec, speed)`
- `s.angle` (rotates the image), `s.point_at(target)`, `s.facing`
- `s.update(dt)` integrates physics and syncs `s.rect`
- Works inside a normal `pygame.sprite.Group`.

### `collision` — detection & resolution
`rect_collide`, `circle_collide`, `point_in`, `collides_with_any`,
`collisions`, `overlapping_pairs`, `keep_in_bounds(..., bounce=)`,
`wrap_around`, `resolve(sprite, obstacle, bounce=)`.

### `movement` — behaviors to call each frame
`move_toward`, `follow`, `flee`, `orbit`, `apply_gravity`, `patrol`,
`smooth_follow` (camera easing).

### `InputManager` (`app.input`)
- `held("space")`, `pressed("a")` (edge), `released("a")`
- `mouse_held()/mouse_pressed()/mouse_released()`, `mouse_pos`, `scroll`
- `axis("a","d")` → -1/0/1, `direction("wasd"|"arrows"|"both")` → normalized Vector2

### `animation`
`SpriteSheet(image).grid(fw, fh)` slices frames; `Animation(frames, fps, loop)`
plays them — call `anim.update(dt)` then `sprite.set_image(anim.current)`.

### `utils` & `constants`
`clamp`, `lerp`, `remap`, `distance`, `angle_to`, `vector_from_angle`,
`lerp_color`, `random_color`, `Timer`, `draw_text`, `load_image`, `make_surface`.
Colors (`pgkit.RED`, `pgkit.GREEN`, …) and directions (`pgkit.UP`, …) are top-level.

## Project layout
```
pgkit/            the library
examples/         demo.py (playable) + smoketest.py (headless API check)
```

A separate Scratch-style block-coding app (built on pgkit) will live in its own
root folder.
```
python examples/smoketest.py   # verify everything works on your machine
```
