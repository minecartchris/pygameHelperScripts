"""Common constants: colors and directions."""

from pygame.math import Vector2

# --- Colors (R, G, B) ---
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
LIGHT_GRAY = (200, 200, 200)
DARK_GRAY = (64, 64, 64)

RED = (220, 50, 50)
GREEN = (50, 200, 80)
BLUE = (50, 120, 220)
YELLOW = (240, 220, 60)
ORANGE = (240, 150, 50)
PURPLE = (170, 80, 220)
CYAN = (60, 200, 220)
MAGENTA = (220, 60, 200)
PINK = (250, 150, 200)
BROWN = (140, 90, 50)

# A pleasant default background
CORNFLOWER = (100, 149, 237)

# --- Directions (unit-ish vectors, screen coords: +y is down) ---
UP = Vector2(0, -1)
DOWN = Vector2(0, 1)
LEFT = Vector2(-1, 0)
RIGHT = Vector2(1, 0)

DIRECTIONS = {
    "up": UP,
    "down": DOWN,
    "left": LEFT,
    "right": RIGHT,
}
