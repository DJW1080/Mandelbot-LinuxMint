"""Original bounded camera journeys through the Mandelbrot plane."""

from dataclasses import dataclass
import math

REGION_SECONDS = 40.0
FADE_SECONDS = 1.6


@dataclass(frozen=True)
class Region:
    name: str
    real: float
    imaginary: float
    start_span: float
    end_span: float


@dataclass(frozen=True)
class View:
    name: str
    real: float
    imaginary: float
    span: float
    opacity: float


REGIONS = (
    Region("Seahorse valley", -0.743643887037151, 0.13182590420533, 0.09, 0.00002),
    Region("The whole set", -0.55, 0.0, 3.6, 1.6),
    Region("Spiral garden", -0.7453, 0.1127, 0.03, 0.0005),
    Region("Northern filaments", -0.16, 1.0405, 0.16, 0.012),
)


def sample(seconds, speed):
    elapsed = max(0.0, seconds) * speed
    region = REGIONS[int(elapsed // REGION_SECONDS) % len(REGIONS)]
    local_time = elapsed % REGION_SECONDS
    progress = local_time / REGION_SECONDS
    span = region.start_span * (region.end_span / region.start_span) ** progress
    opacity = min(1.0, local_time / FADE_SECONDS, (REGION_SECONDS - local_time) / FADE_SECONDS)
    # The fade reaches black at the exact jump between unrelated regions.
    return View(region.name, region.real, region.imaginary, span, opacity)
