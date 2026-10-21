"""Bounded render dimensions and input dismissal rules."""

import math

MOTION_GRACE_SECONDS = 0.8
MOTION_THRESHOLD_PIXELS = 8


def frame_dimensions(width, height, longest_side):
    width, height = max(1, width), max(1, height)
    scale = min(1.0, longest_side / max(width, height))
    return max(1, round(width * scale)), max(1, round(height * scale))


def motion_dismisses(origin, position, elapsed):
    return (elapsed >= MOTION_GRACE_SECONDS
            and math.hypot(position[0] - origin[0], position[1] - origin[1])
            >= MOTION_THRESHOLD_PIXELS)
