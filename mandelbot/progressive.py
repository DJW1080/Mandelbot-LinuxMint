"""Bounded GPU refinement with smooth reprojection of completed native images."""

import ctypes as ct
from dataclasses import replace

from . import gl_api as api
from .gpu_renderer import GpuRenderer, SHADER_DIRECTORY

TARGET_TILE_PIXELS = 130_000
MIN_TILE_HEIGHT = 1


class FrameTarget:
    def __init__(self, gl, width, height):
        self.gl = gl
        self.width, self.height = width, height
        self.framebuffer, self.texture = ct.c_uint(), ct.c_uint()
        gl.glGenFramebuffers(1, ct.byref(self.framebuffer))
        gl.glGenTextures(1, ct.byref(self.texture))
        gl.glBindTexture(api.GL_TEXTURE_2D, self.texture)
        gl.glTexImage2D(api.GL_TEXTURE_2D, 0, api.GL_SRGB8_ALPHA8, width, height, 0,
                        api.GL_RGBA, api.GL_UNSIGNED_BYTE, None)
        for option in (api.GL_TEXTURE_MIN_FILTER, api.GL_TEXTURE_MAG_FILTER):
            gl.glTexParameteri(api.GL_TEXTURE_2D, option, api.GL_LINEAR)
        for option in (api.GL_TEXTURE_WRAP_S, api.GL_TEXTURE_WRAP_T):
            gl.glTexParameteri(api.GL_TEXTURE_2D, option, api.GL_CLAMP_TO_EDGE)
        self.bind()
        gl.glFramebufferTexture2D(api.GL_FRAMEBUFFER, api.GL_COLOR_ATTACHMENT0, api.GL_TEXTURE_2D, self.texture, 0)
        if gl.glCheckFramebufferStatus(api.GL_FRAMEBUFFER) != api.GL_FRAMEBUFFER_COMPLETE:
            self.close()
            raise RuntimeError(f"Cannot allocate a {width} × {height} GPU frame.")
        gl.check()
        self.view = None
        self.settings = None
        self.phase = None

    def bind(self):
        self.gl.glBindFramebuffer(api.GL_FRAMEBUFFER, self.framebuffer)

    def close(self):
        self.gl.glDeleteFramebuffers(1, ct.byref(self.framebuffer))
        self.gl.glDeleteTextures(1, ct.byref(self.texture))


class ProgressiveRenderer:
    """Two immutable camera snapshots prevent partially rendered tiles being shown."""

    def __init__(self):
        self.orbit_renderer = GpuRenderer()
        self.gl = self.orbit_renderer.gl
        self.name, self.version = self.orbit_renderer.name, self.orbit_renderer.version
        self.front = None
        self.back = None
        self.next_row = 0
        self.refining = False
        self.settled = False
        self.detail_frames = 0
        shaders = []
        try:
            for filename, kind in [('fullscreen.vert', api.GL_VERTEX_SHADER), ('present.frag', api.GL_FRAGMENT_SHADER)]:
                shaders.append(self.gl.compile_shader(kind, (SHADER_DIRECTORY / filename).read_text()))
            self.program = self.gl.link_program(shaders)
        finally:
            for shader in shaders:
                self.gl.glDeleteShader(shader)
        self.uniforms = {name: self.gl.glGetUniformLocation(self.program, name.encode())
                         for name in ['uImage', 'uResolution', 'uScale', 'uOpacity']}

    @property
    def ready(self):
        return self.front is not None and self.front.view is not None

    def _allocate(self, width, height):
        if self.front is not None and (self.front.width, self.front.height) == (width, height):
            return
        for target in (self.front, self.back):
            if target:
                target.close()
        self.front = FrameTarget(self.gl, width, height)
        self.back = FrameTarget(self.gl, width, height)
        self.refining = False

    def _refine(self, width, height, view, settings, phase):
        target = self.back
        if (not self.refining or target.settings != settings or target.view.name != view.name):
            target.view, target.settings, target.phase = replace(view, opacity=1), settings, phase
            self.next_row = 0
            self.refining = True
        target.bind()
        tile_height = max(MIN_TILE_HEIGHT, TARGET_TILE_PIXELS // width)
        rows = min(tile_height, height - self.next_row)
        self.gl.glEnable(api.GL_SCISSOR_TEST)
        self.gl.glScissor(0, self.next_row, width, rows)
        self.orbit_renderer.draw(width, height, target.view, target.settings, target.phase)
        self.gl.glDisable(api.GL_SCISSOR_TEST)
        self.next_row += rows
        if self.next_row >= height:
            self.front, self.back = self.back, self.front
            self.refining = False
            self.detail_frames += 1

    def _present(self, width, height, view):
        gl = self.gl
        gl.glViewport(0, 0, width, height)
        gl.glDisable(api.GL_SCISSOR_TEST)
        gl.glDisable(api.GL_FRAMEBUFFER_SRGB)
        if not self.ready or self.front.view.name != view.name:
            gl.glClearColor(0.02, 0.035, 0.06, 1)
            gl.glClear(api.GL_COLOR_BUFFER_BIT)
            return
        gl.glUseProgram(self.program)
        gl.glBindVertexArray(self.orbit_renderer.vertex_array)
        gl.glActiveTexture(api.GL_TEXTURE0)
        gl.glBindTexture(api.GL_TEXTURE_2D, self.front.texture)
        gl.glUniform1i(self.uniforms['uImage'], 0)
        gl.glUniform2f(self.uniforms['uResolution'], width, height)
        scale = view.span / self.front.view.span
        gl.glUniform2f(self.uniforms['uScale'], scale, scale)
        gl.glUniform1f(self.uniforms['uOpacity'], view.opacity)
        gl.glDrawArrays(api.GL_TRIANGLES, 0, 3)

    def draw(self, width, height, view, settings, phase):
        previous = ct.c_int()
        self.gl.glGetIntegerv(api.GL_FRAMEBUFFER_BINDING, ct.byref(previous))
        try:
            self._allocate(width, height)
            complete = (self.ready and self.front.view == replace(view, opacity=1)
                        and self.front.settings == settings and self.front.phase == phase)
            if not complete:
                self._refine(width, height, view, settings, phase)
        finally:
            self.gl.glDisable(api.GL_SCISSOR_TEST)
            self.gl.glBindFramebuffer(api.GL_FRAMEBUFFER, previous.value)
        self._present(width, height, view)
        self.settled = (self.ready and self.front.view == replace(view, opacity=1)
                        and self.front.settings == settings and self.front.phase == phase)

    def read_pixels(self, width, height):
        return self.orbit_renderer.read_pixels(width, height)

    def close(self):
        for target in (self.front, self.back):
            if target:
                target.close()
        self.gl.glDeleteProgram(self.program)
        self.orbit_renderer.close()
