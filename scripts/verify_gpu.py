#!/usr/bin/python3
"""Compare real GPU pixels to CPU maths and time full-resolution GPU completion."""

import argparse
from contextlib import contextmanager
import ctypes as ct
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser()
parser.add_argument('--application-root', type=Path, default=ROOT)
parser.add_argument('--output', type=Path, default=ROOT / 'build/evidence/gpu')
options = parser.parse_args()
sys.path.insert(0, str(options.application_root))

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import GdkPixbuf, GLib, Gtk
from mandelbot import gl_api as api
from mandelbot.config import Settings
from mandelbot.palettes import PALETTES
from mandelbot.gpu_renderer import GpuRenderer
from mandelbot.progressive import ProgressiveRenderer
from mandelbot.renderer import Renderer
from mandelbot.tour import REGIONS, View

CHECK_WIDTH, CHECK_HEIGHT = 65, 49
CHECK_ITERATIONS = 4096
BENCHMARK_WIDTH, BENCHMARK_HEIGHT = 3840, 2160
BENCHMARK_REPEATS = 3
PALETTE_WIDTH, PALETTE_HEIGHT = 480, 300


@contextmanager
def render_target(gl, width, height):
    previous, framebuffer, texture = ct.c_int(), ct.c_uint(), ct.c_uint()
    gl.glGetIntegerv(api.GL_FRAMEBUFFER_BINDING, ct.byref(previous))
    gl.glGenFramebuffers(1, ct.byref(framebuffer))
    gl.glGenTextures(1, ct.byref(texture))
    try:
        gl.glBindTexture(api.GL_TEXTURE_2D, texture)
        gl.glTexImage2D(api.GL_TEXTURE_2D, 0, api.GL_RGBA8, width, height, 0,
                        api.GL_RGBA, api.GL_UNSIGNED_BYTE, None)
        gl.glTexParameteri(api.GL_TEXTURE_2D, api.GL_TEXTURE_MIN_FILTER, api.GL_NEAREST)
        gl.glTexParameteri(api.GL_TEXTURE_2D, api.GL_TEXTURE_MAG_FILTER, api.GL_NEAREST)
        gl.glBindFramebuffer(api.GL_FRAMEBUFFER, framebuffer)
        gl.glFramebufferTexture2D(api.GL_FRAMEBUFFER, api.GL_COLOR_ATTACHMENT0, api.GL_TEXTURE_2D, texture, 0)
        assert gl.glCheckFramebufferStatus(api.GL_FRAMEBUFFER) == api.GL_FRAMEBUFFER_COMPLETE
        gl.check()
        yield
    finally:
        gl.glBindFramebuffer(api.GL_FRAMEBUFFER, previous.value)
        gl.glDeleteFramebuffers(1, ct.byref(framebuffer))
        gl.glDeleteTextures(1, ct.byref(texture))


def mathematical_checks(gpu):
    reference = Renderer()
    settings = Settings()
    records = []
    with render_target(gpu.gl, CHECK_WIDTH, CHECK_HEIGHT):
        for region in REGIONS:
            for span in (region.start_span, region.end_span):
                view = View(region.name, region.real, region.imaginary, span, 1)
                gpu.draw(CHECK_WIDTH, CHECK_HEIGHT, view, settings, 0, diagnostic=True,
                         iterations=CHECK_ITERATIONS)
                pixels = gpu.read_pixels(CHECK_WIDTH, CHECK_HEIGHT)
                mismatches = []
                pixel_span = span / CHECK_WIDTH
                for row in range(CHECK_HEIGHT):
                    imaginary = view.imaginary + (row + 0.5 - CHECK_HEIGHT * 0.5) * pixel_span
                    for column in range(CHECK_WIDTH):
                        real = view.real + (column + 0.5 - CHECK_WIDTH * 0.5) * pixel_span
                        expected = reference.escape(real, imaginary, CHECK_ITERATIONS)
                        offset = (row * CHECK_WIDTH + column) * 4
                        actual = pixels[offset] + (pixels[offset + 1] << 8)
                        if expected != actual:
                            mismatches.append({'x': column, 'y': row, 'cpu': expected, 'gpu': actual})
                record = {'region': region.name, 'span': span, 'pixels': CHECK_WIDTH * CHECK_HEIGHT,
                          'mismatches': mismatches}
                records.append(record)
        # Analytically known samples, including bounded interior and immediate escape.
        for real, imaginary in [(0, 0), (-1, 0), (2, 2), (1, 0), (-2, 0)]:
            gpu.draw(1, 1, View('Known point', real, imaginary, 1, 1), settings, 0,
                     diagnostic=True, iterations=CHECK_ITERATIONS)
            pixels = gpu.read_pixels(1, 1)
            assert pixels[0] + (pixels[1] << 8) == reference.escape(real, imaginary, CHECK_ITERATIONS)
    return records


def save_frame(gpu, width, height, name):
    pixels = gpu.read_pixels(width, height)
    assert all(pixels[index] == 255 for index in range(3, len(pixels), 4))
    assert len(set(pixels[0::4])) > 32, 'Expected a detailed, nonblank frame'
    stride = width * 4
    top_down = b''.join(pixels[row * stride:(row + 1) * stride] for row in reversed(range(height)))
    image = GdkPixbuf.Pixbuf.new_from_bytes(GLib.Bytes.new(top_down), GdkPixbuf.Colorspace.RGB,
                                          True, 8, width, height, stride)
    image.savev(str(options.output / name), 'png', [], [])


def benchmark(gpu):
    records = []
    with render_target(gpu.gl, BENCHMARK_WIDTH, BENCHMARK_HEIGHT):
        for name, real, imaginary, span in [
                ('whole-set', -0.55, 0, 3.6),
                ('seahorse', REGIONS[0].real, REGIONS[0].imaginary, 0.06),
                ('deep-seahorse', REGIONS[0].real, REGIONS[0].imaginary, 0.00002)]:
            view = View(name, real, imaginary, span, 1)
            timings = []
            # Warm up shader compilation/cache and measure completed work, not submissions.
            gpu.draw(BENCHMARK_WIDTH, BENCHMARK_HEIGHT, view, Settings(), 0)
            gpu.gl.glFinish()
            for _ in range(BENCHMARK_REPEATS):
                start = time.perf_counter()
                gpu.draw(BENCHMARK_WIDTH, BENCHMARK_HEIGHT, view, Settings(), 0)
                gpu.gl.glFinish()
                timings.append((time.perf_counter() - start) * 1000)
            gpu.gl.check()
            save_frame(gpu, BENCHMARK_WIDTH, BENCHMARK_HEIGHT, name + '.png')
            records.append({'view': name, 'width': BENCHMARK_WIDTH, 'height': BENCHMARK_HEIGHT,
                            'quality': 'Ultra', 'milliseconds': timings,
                            'median_ms': statistics.median(timings)})
    return records


def palette_checks(gpu):
    """Exercise real uniform uploads, cyclic colour and all selectable themes."""
    view = View('Theme check', -0.5, 0, 3.5, 1)
    records, hashes = [], set()
    interior = None
    centre = ((PALETTE_HEIGHT // 2) * PALETTE_WIDTH + PALETTE_WIDTH // 2) * 4
    with render_target(gpu.gl, PALETTE_WIDTH, PALETTE_HEIGHT):
        for name in PALETTES:
            settings = Settings(palette=name)
            gpu.draw(PALETTE_WIDTH, PALETTE_HEIGHT, view, settings, 0)
            pixels = gpu.read_pixels(PALETTE_WIDTH, PALETTE_HEIGHT)
            digest = hashlib.sha256(pixels).hexdigest()
            assert digest not in hashes, f'{name} must produce a distinct image'
            hashes.add(digest)
            if interior is None:
                interior = pixels[centre:centre + 4]
            assert pixels[centre:centre + 4] == interior, 'Themes must retain the set interior'
            filename = f'theme-{name.lower()}.png'
            save_frame(gpu, PALETTE_WIDTH, PALETTE_HEIGHT, filename)
            gpu.draw(PALETTE_WIDTH, PALETTE_HEIGHT, view, settings, 1)
            assert gpu.read_pixels(PALETTE_WIDTH, PALETTE_HEIGHT) == pixels, 'Colour must wrap seamlessly'
            records.append({'theme': name, 'sha256': digest, 'image': filename,
                            'opaque_and_detailed': True, 'cyclic_phase_matches': True})
        # Switching away and back must restore the original palette uniforms.
        gpu.draw(PALETTE_WIDTH, PALETTE_HEIGHT, view, Settings(palette=PALETTES[0]), 0)
        assert hashlib.sha256(gpu.read_pixels(PALETTE_WIDTH, PALETTE_HEIGHT)).hexdigest() == records[0]['sha256']
    return records


def progressive_checks(gpu):
    view = View('Seahorse valley', REGIONS[0].real, REGIONS[0].imaginary, 0.00002, 1)
    progressive = ProgressiveRenderer()
    timings = []
    try:
        with render_target(gpu.gl, BENCHMARK_WIDTH, BENCHMARK_HEIGHT):
            gpu.draw(BENCHMARK_WIDTH, BENCHMARK_HEIGHT, view, Settings(), 0)
            expected = gpu.read_pixels(BENCHMARK_WIDTH, BENCHMARK_HEIGHT)
            for _ in range(256):
                start = time.perf_counter()
                progressive.draw(BENCHMARK_WIDTH, BENCHMARK_HEIGHT, view, Settings(), 0)
                gpu.gl.glFinish()
                timings.append((time.perf_counter() - start) * 1000)
                if progressive.settled:
                    break
            assert progressive.settled, 'A paused image must refine to its exact camera position'
            actual = progressive.read_pixels(BENCHMARK_WIDTH, BENCHMARK_HEIGHT)
            maximum_error = max(abs(first - second) for first, second in zip(expected, actual))
            assert maximum_error <= 2, f'Progressive pixels differ by {maximum_error} channel levels'
            return {'physical_pixels': [BENCHMARK_WIDTH, BENCHMARK_HEIGHT],
                    'refinement_tiles': len(timings), 'median_tile_ms': statistics.median(timings),
                    'maximum_tile_ms': max(timings), 'max_channel_error_vs_direct': maximum_error,
                    'paused_refinement_completes': True}
    finally:
        progressive.close()


def main():
    options.output.mkdir(parents=True, exist_ok=True)
    results = {}
    window = Gtk.Window(title='Mandelbot GPU verification')
    area = Gtk.GLArea()
    area.set_required_version(4, 0)
    area.set_use_es(False)
    window.set_default_size(320, 200)
    window.add(area)
    started = False

    def verify(widget, context):
        nonlocal started
        if started:
            return True
        started = True
        gpu = None
        try:
            assert area.get_error() is None, area.get_error()
            gpu = GpuRenderer()
            results.update(renderer=gpu.name, opengl=gpu.version)
            results['mathematical_checks'] = mathematical_checks(gpu)
            results['colour_themes'] = palette_checks(gpu)
            results['native_4k_benchmark'] = benchmark(gpu)
            results['progressive_4k'] = progressive_checks(gpu)
            assert all(not record['mismatches'] for record in results['mathematical_checks']), 'GPU escape counts differ from the CPU reference'
            results['status'] = 'passed'
        except Exception:
            results['status'] = 'failed'
            results['error'] = traceback.format_exc()
        finally:
            if gpu:
                gpu.close()
            GLib.idle_add(Gtk.main_quit)
        return True

    area.connect('render', verify)
    window.show_all()
    Gtk.main()
    window.destroy()
    (options.output / 'gpu-verification.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(results, indent=2))
    return 0 if results.get('status') == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
