"""Rendering budgets and logarithmic motion controls, independent of GTK."""

from dataclasses import dataclass
import math

MIN_SPEED, MAX_SPEED = 0.01, 2.0
MAX_ITERATIONS = 4096
REFERENCE_SPAN = 3.6


@dataclass(frozen=True)
class Quality:
    samples: int
    base_iterations: int
    iterations_per_octave: int


# Every preset uses physical pixels; sampling and orbit budgets control GPU work.
QUALITY = {
    "Eco": Quality(1, 256, 32),
    "Balanced": Quality(1, 512, 64),
    "High": Quality(2, 768, 96),
    "Ultra": Quality(4, 1024, 128),
}


def iteration_limit(quality, span):
    budget = QUALITY[quality]
    octaves = max(0.0, math.log2(REFERENCE_SPAN / span))
    return min(MAX_ITERATIONS, budget.base_iterations + math.ceil(octaves * budget.iterations_per_octave))


def physical_dimensions(width, height, scale_factor):
    return max(1, width * scale_factor), max(1, height * scale_factor)


def speed_to_position(speed):
    return math.log(speed / MIN_SPEED) / math.log(MAX_SPEED / MIN_SPEED)


def position_to_speed(position):
    return min(MAX_SPEED, max(MIN_SPEED, MIN_SPEED * (MAX_SPEED / MIN_SPEED) ** position))
