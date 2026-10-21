"""Native-resolution Mandelbrot shaders; orbit calculations run on the GPU."""

import ctypes as ct
from pathlib import Path

from . import gl_api as api
from .palettes import PALETTES, PALETTE_STOP_COUNT, palette_channels
from .quality import QUALITY, iteration_limit

SHADER_DIRECTORY = Path(__file__).resolve().parent / "shaders"
SOFTWARE_RENDERERS = ("llvmpipe", "softpipe", "software rasterizer", "swrast")


class GpuRenderer:
    """Own resources in the current GLArea context, never a worker thread."""

    def __init__(self):
        self.gl = api.GL()
        self.name = self.gl.glGetString(api.GL_RENDERER).decode("utf-8")
        self.version = self.gl.glGetString(api.GL_VERSION).decode("utf-8")
        if any(name in self.name.lower() for name in SOFTWARE_RENDERERS):
            raise RuntimeError(f"Hardware graphics acceleration is required. OpenGL selected {self.name}.")
        self.program = 0
        self.vertex_array = ct.c_uint()
        self.palette_buffers = {name: (ct.c_float * len(palette_channels(name)))(*palette_channels(name))
                                for name in PALETTES}
        shaders = []
        try:
            for filename, kind in [("fullscreen.vert", api.GL_VERTEX_SHADER),
                                   ("mandelbrot.frag", api.GL_FRAGMENT_SHADER)]:
                source = (SHADER_DIRECTORY / filename).read_text()
                source = source.replace("__PALETTE_STOP_COUNT__", str(PALETTE_STOP_COUNT))
                shaders.append(self.gl.compile_shader(kind, source))
            self.program = self.gl.link_program(shaders)
        finally:
            for shader in shaders:
                self.gl.glDeleteShader(shader)
        self.gl.glGenVertexArrays(1, ct.byref(self.vertex_array))
        names = ["uCentre", "uPixelSpan", "uResolution", "uIterations", "uSamples",
                 "uPaletteStops[0]", "uPhase", "uOpacity", "uDiagnostic"]
        self.uniforms = {name: self.gl.glGetUniformLocation(self.program, name.encode()) for name in names}
        self.gl.check()

    def draw(self, width, height, view, settings, phase, diagnostic=False, iterations=None):
        gl, uniforms = self.gl, self.uniforms
        gl.glViewport(0, 0, width, height)
        for feature in (api.GL_DITHER, api.GL_FRAMEBUFFER_SRGB, api.GL_DEPTH_TEST, api.GL_BLEND):
            gl.glDisable(feature)
        gl.glUseProgram(self.program)
        gl.glBindVertexArray(self.vertex_array)
        gl.glUniform2d(uniforms["uCentre"], view.real, view.imaginary)
        gl.glUniform1d(uniforms["uPixelSpan"], view.span / width)
        gl.glUniform2f(uniforms["uResolution"], width, height)
        gl.glUniform1i(uniforms["uIterations"], iterations or iteration_limit(settings.quality, view.span))
        gl.glUniform1i(uniforms["uSamples"], QUALITY[settings.quality].samples)
        gl.glUniform3fv(uniforms["uPaletteStops[0]"], PALETTE_STOP_COUNT,
                        self.palette_buffers[settings.palette])
        gl.glUniform1f(uniforms["uPhase"], phase % 1.0)
        gl.glUniform1f(uniforms["uOpacity"], view.opacity)
        gl.glUniform1i(uniforms["uDiagnostic"], int(diagnostic))
        gl.glDrawArrays(api.GL_TRIANGLES, 0, 3)

    def read_pixels(self, width, height):
        """Synchronous RGBA readback for verification only, bottom row first."""
        pixels = (ct.c_ubyte * (width * height * 4))()
        self.gl.glReadPixels(0, 0, width, height, api.GL_RGBA, api.GL_UNSIGNED_BYTE, pixels)
        self.gl.check()
        return bytes(pixels)

    def close(self):
        if self.program:
            self.gl.glDeleteProgram(self.program)
            self.gl.glDeleteVertexArrays(1, ct.byref(self.vertex_array))
            self.program = 0
