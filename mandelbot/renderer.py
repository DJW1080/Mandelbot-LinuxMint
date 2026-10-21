"""Small, checked ctypes boundary around the independent native renderer."""

import ctypes
import math
from pathlib import Path

from .config import PALETTES
from .palettes import PALETTE_STOP_COUNT, palette_channels

MAX_DIMENSION = 1920
MAX_PIXELS = 4_000_000
MIN_SPAN, MAX_SPAN = 0.0000001, 8.0
MAX_ITERATIONS = 4096
BYTES_PER_PIXEL = 4


class Renderer:
    def __init__(self):
        root = Path(__file__).resolve().parent.parent
        library = root / "libmandelbot.so"
        if not library.is_file():
            library = root / "build/libmandelbot.so"
        if not library.is_file():
            raise RuntimeError("The renderer has not been built. Run 'make' in the project folder.")
        self.library = ctypes.CDLL(str(library))
        self.library.mb_escape.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_int]
        self.library.mb_escape.restype = ctypes.c_int
        self.library.mb_render.argtypes = [ctypes.POINTER(ctypes.c_uint32), ctypes.c_int,
            ctypes.c_int, ctypes.c_double, ctypes.c_double, ctypes.c_double,
            ctypes.c_int, ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int, ctypes.c_double]
        self.library.mb_render.restype = ctypes.c_int

    def escape(self, real, imaginary, iterations):
        if type(iterations) is not int or not 1 <= iterations <= MAX_ITERATIONS:
            raise ValueError("Invalid iteration limit.")
        result = self.library.mb_escape(real, imaginary, iterations)
        if result < 0:
            raise ValueError("Invalid Mandelbrot coordinate.")
        return result

    def render(self, width, height, real, imaginary, span, iterations, palette, phase):
        valid_size = (type(width) is int and type(height) is int
                      and 1 <= width <= MAX_DIMENSION and 1 <= height <= MAX_DIMENSION
                      and width * height <= MAX_PIXELS)
        valid_view = (all(math.isfinite(value) for value in (real, imaginary, span, phase))
                      and abs(real) <= 4 and abs(imaginary) <= 4 and MIN_SPAN <= span <= MAX_SPAN)
        if (not valid_size or not valid_view or palette not in PALETTES
                or type(iterations) is not int or not 1 <= iterations <= MAX_ITERATIONS):
            raise ValueError("Invalid render dimensions, viewport, palette, or iteration limit.")
        pixels = bytearray(width * height * BYTES_PER_PIXEL)
        buffer = (ctypes.c_uint32 * (width * height)).from_buffer(pixels)
        channels = palette_channels(palette)
        colours = (ctypes.c_ubyte * len(channels))(*channels)
        status = self.library.mb_render(buffer, width, height, real, imaginary, span,
                                       iterations, colours, PALETTE_STOP_COUNT, phase)
        if status:
            raise RuntimeError("The native renderer rejected the frame parameters.")
        return pixels
