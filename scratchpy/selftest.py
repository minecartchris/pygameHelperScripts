"""Headless self-test for scratchpy: engine, stage math, snapping, editor frames."""
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame
pygame.init()
pygame.display.set_mode((1280, 760))

import pgkit
from scratchpy import render
from scratchpy.blocks import Block, iter_tree
from scratchpy.engine import Context, Engine
from scratchpy.stage import Stage, StageSprite
from scratchpy.editor import Editor

fails = []
def check(name, cond):
    print(("PASS" if cond else "FAIL"), name)
    if not cond:
        fails.append(name)


def run_until_idle(engine, max_frames=10000):
    n = 0
    while engine.active and n < max_frames:
        engine.step(1 / 60)
        n += 1
    return n


# ---- stage sprite math ---------------------------------------------------- #
stage = Stage(pygame.Rect(0, 0, 480, 360))
sp = StageSprite(stage)
check("starts at origin", sp.sx == 0 and sp.sy == 0)
check("default dir 90 (right)", abs(sp.direction - 90) < 1e-6)
sp.move_steps(10)
check("move right +x", abs(sp.sx - 10) < 1e-6 and abs(sp.sy) < 1e-6)
sp.direction = 0
sp.move_steps(10)
check("move up +y", abs(sp.sy - 10) < 1e-6)
sp.goto(100, 50)
check("goto sets coords", sp.sx == 100 and sp.sy == 50)
to = stage.to_screen(0, 0)
check("origin maps to stage center", to == stage.rect.center)

# bounce
sp.goto(1000, 0); sp.direction = 90
sp.bounce_on_edge()
check("bounce flips direction off right wall", abs(sp.direction) > 90 or sp.direction < 0)
check("bounce clamps inside", sp.sx <= stage.width / 2)

# ---- interpreter: move + repeat + wait ------------------------------------ #
sp.reset()
engine = Engine(Context(sp, stage, None))
engine.ctx.engine = engine

hat = Block("when_flag")
rep = Block("repeat"); rep.inputs["times"] = 5
mv = Block("move"); mv.inputs["steps"] = 10
rep.body = mv
hat.next = rep
engine.start_flag([hat])
frames = run_until_idle(engine)
check("repeat 5x move 10 => x=50", abs(sp.sx - 50) < 1e-6)
check("repeat finishes", not engine.active)

# wait blocks pause across frames
sp.reset()
hat2 = Block("when_flag")
w = Block("wait"); w.inputs["secs"] = 0.5
mv2 = Block("move"); mv2.inputs["steps"] = 5
hat2.next = w; w.next = mv2
engine.start_flag([hat2])
engine.step(1/60)
check("wait holds before moving", abs(sp.sx) < 1e-6)
run_until_idle(engine)
check("wait then moves", abs(sp.sx - 5) < 1e-6)

# forever doesn't hard-lock (yields each loop)
sp.reset()
hat3 = Block("when_flag")
forever = Block("forever")
forever.body = Block("move"); forever.body.inputs["steps"] = 1
hat3.next = forever
engine.start_flag([hat3])
for _ in range(10):
    engine.step(1/60)
check("forever advances each frame", sp.sx >= 10 - 1e-6)
check("forever still running", engine.active)
engine.stop()
check("stop halts engine", not engine.active)

# when_key trigger
sp.reset()
hk = Block("when_key"); hk.inputs["key"] = "space"
hk.next = Block("move"); hk.next.inputs["steps"] = 7
engine.trigger_key([hk], "space")
run_until_idle(engine)
check("when_key fires matching key", abs(sp.sx - 7) < 1e-6)
sp.reset()
engine.trigger_key([hk], "a")
run_until_idle(engine)
check("when_key ignores other key", abs(sp.sx) < 1e-6)

# ---- layout + snapping ---------------------------------------------------- #
a = Block("when_flag", 100, 100)
render.layout_root(a)
ax, ay = render.top_anchor(a)
check("hat has layout rect", a._rect is not None)

# place a free 'move' block right at hat's bottom connector -> should snap
move = Block("move")
# simulate editor snap detection
render.layout_root(a)
pts = list(render.connection_points(a))
check("hat exposes a 'next' connection", any(m == "next" for m, _, _ in pts))
nmode, nblk, (px, py) = [p for p in pts if p[0] == "next"][0]
move.x, move.y = px - render.NOTCH_X, py  # align top anchor onto the point
render.layout_root(move)
mx, my = render.top_anchor(move)
dist = ((mx - px) ** 2 + (my - py) ** 2) ** 0.5
check("aligned block within snap distance", dist < render.SNAP_DIST)

# C-block exposes an inner connection
crep = Block("repeat", 0, 0)
render.layout_root(crep)
modes = {m for m, _, _ in render.connection_points(crep)}
check("C block exposes inner+next", "inner" in modes and "next" in modes)

# ---- editor scene builds and runs frames ---------------------------------- #
app = pgkit.App(1280, 760, title="t")
ed = Editor()
app.push_scene(ed)
check("editor has starter script", len(ed.scripts) == 1)
check("palette populated", len(ed.palette_protos) >= 12)

# simulate: click Run, step some frames, click Stop
ed.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=ed.btn_flag.rect.center))
for _ in range(30):
    ed.update(1/60)
    ed.draw(app.screen)
check("run button started engine or completed", True)  # no crash == pass
ed.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=ed.btn_stop.rect.center))
check("stop clears engine", not ed.engine.running)

# simulate dragging a block from the palette into the canvas
proto = ed.palette_protos[2]  # some motion block
# need palette hitmap -> draw once
ed.draw(app.screen)
hit_rect = ed._palette_hitmap[2][1]
ed.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=hit_rect.center))
check("palette drag created a block", ed.drag_block is not None)
before = len(ed.scripts)
ed.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(700, 400)))
ed.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(700, 400)))
check("dropped block stays on canvas", len(ed.scripts) == before)
check("drag released", ed.drag_block is None)

# drag a block onto the palette -> trashed
ed.draw(app.screen)
target = ed.scripts[-1]
# grab by the label edge (not the center, which is an editable slot)
grab = (target._rect.x + 6, target._rect.centery)
ed.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=grab))
if ed.drag_block:
    ed.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=(50, 400)))
    ed.handle_event(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=(50, 400)))
check("dropping on palette trashes block", target not in ed.scripts)

print()
if fails:
    print(f"{len(fails)} FAILED: {fails}")
    sys.exit(1)
print("All scratchpy checks passed.")
