"""Small typed OpenGL interface using the existing Linux GL dispatch library."""

import ctypes as ct

GL_VERTEX_SHADER = 0x8B31
GL_FRAGMENT_SHADER = 0x8B30
GL_COMPILE_STATUS = 0x8B81
GL_LINK_STATUS = 0x8B82
GL_INFO_LOG_LENGTH = 0x8B84
GL_RENDERER = 0x1F01
GL_VERSION = 0x1F02
GL_TRIANGLES = 0x0004
GL_RGBA = 0x1908
GL_UNSIGNED_BYTE = 0x1401
GL_DITHER = 0x0BD0
GL_FRAMEBUFFER_SRGB = 0x8DB9
GL_DEPTH_TEST = 0x0B71
GL_BLEND = 0x0BE2
GL_NO_ERROR = 0
GL_FRAMEBUFFER = 0x8D40
GL_FRAMEBUFFER_BINDING = 0x8CA6
GL_FRAMEBUFFER_COMPLETE = 0x8CD5
GL_COLOR_ATTACHMENT0 = 0x8CE0
GL_TEXTURE_2D = 0x0DE1
GL_RGBA8 = 0x8058
GL_TEXTURE_MIN_FILTER = 0x2801
GL_TEXTURE_MAG_FILTER = 0x2800
GL_NEAREST = 0x2600
GL_LINEAR = 0x2601
GL_SRGB8_ALPHA8 = 0x8C43
GL_TEXTURE_WRAP_S = 0x2802
GL_TEXTURE_WRAP_T = 0x2803
GL_CLAMP_TO_EDGE = 0x812F
GL_TEXTURE0 = 0x84C0
GL_SCISSOR_TEST = 0x0C11
GL_COLOR_BUFFER_BIT = 0x4000


class GL:
    def __init__(self):
        self.library = ct.CDLL("libGL.so.1")
        uint, integer, pointer = ct.c_uint, ct.c_int, ct.c_void_p
        definitions = {
            "glGetString": (ct.c_char_p, [uint]),
            "glGetError": (uint, []),
            "glCreateShader": (uint, [uint]),
            "glShaderSource": (None, [uint, integer, ct.POINTER(ct.c_char_p), pointer]),
            "glCompileShader": (None, [uint]),
            "glGetShaderiv": (None, [uint, uint, ct.POINTER(integer)]),
            "glGetShaderInfoLog": (None, [uint, integer, pointer, pointer]),
            "glDeleteShader": (None, [uint]),
            "glCreateProgram": (uint, []),
            "glAttachShader": (None, [uint, uint]),
            "glLinkProgram": (None, [uint]),
            "glGetProgramiv": (None, [uint, uint, ct.POINTER(integer)]),
            "glGetProgramInfoLog": (None, [uint, integer, pointer, pointer]),
            "glDeleteProgram": (None, [uint]),
            "glUseProgram": (None, [uint]),
            "glGenVertexArrays": (None, [integer, ct.POINTER(uint)]),
            "glBindVertexArray": (None, [uint]),
            "glDeleteVertexArrays": (None, [integer, ct.POINTER(uint)]),
            "glGetUniformLocation": (integer, [uint, ct.c_char_p]),
            "glUniform1i": (None, [integer, integer]),
            "glUniform1f": (None, [integer, ct.c_float]),
            "glUniform1d": (None, [integer, ct.c_double]),
            "glUniform2d": (None, [integer, ct.c_double, ct.c_double]),
            "glUniform2f": (None, [integer, ct.c_float, ct.c_float]),
            "glUniform3fv": (None, [integer, integer, ct.POINTER(ct.c_float)]),
            "glViewport": (None, [integer, integer, integer, integer]),
            "glDisable": (None, [uint]),
            "glEnable": (None, [uint]),
            "glScissor": (None, [integer, integer, integer, integer]),
            "glClearColor": (None, [ct.c_float, ct.c_float, ct.c_float, ct.c_float]),
            "glClear": (None, [uint]),
            "glActiveTexture": (None, [uint]),
            "glDrawArrays": (None, [uint, integer, integer]),
            "glReadPixels": (None, [integer, integer, integer, integer, uint, uint, pointer]),
            "glFinish": (None, []),
            "glGetIntegerv": (None, [uint, ct.POINTER(integer)]),
            "glGenFramebuffers": (None, [integer, ct.POINTER(uint)]),
            "glBindFramebuffer": (None, [uint, uint]),
            "glDeleteFramebuffers": (None, [integer, ct.POINTER(uint)]),
            "glFramebufferTexture2D": (None, [uint, uint, uint, uint, integer]),
            "glCheckFramebufferStatus": (uint, [uint]),
            "glGenTextures": (None, [integer, ct.POINTER(uint)]),
            "glBindTexture": (None, [uint, uint]),
            "glTexImage2D": (None, [uint, integer, integer, integer, integer, integer, uint, uint, pointer]),
            "glTexParameteri": (None, [uint, uint, integer]),
            "glDeleteTextures": (None, [integer, ct.POINTER(uint)]),
        }
        for name, (result, arguments) in definitions.items():
            function = getattr(self.library, name)
            function.restype, function.argtypes = result, arguments
            setattr(self, name, function)

    def check(self):
        error = self.glGetError()
        if error != GL_NO_ERROR:
            raise RuntimeError(f"OpenGL reported error 0x{error:04x}.")

    def compile_shader(self, kind, source):
        shader = self.glCreateShader(kind)
        source_pointer = ct.c_char_p(source.encode("utf-8"))
        self.glShaderSource(shader, 1, ct.byref(source_pointer), None)
        self.glCompileShader(shader)
        status = ct.c_int()
        self.glGetShaderiv(shader, GL_COMPILE_STATUS, ct.byref(status))
        if not status.value:
            length = ct.c_int()
            self.glGetShaderiv(shader, GL_INFO_LOG_LENGTH, ct.byref(length))
            message = ct.create_string_buffer(max(1, length.value))
            self.glGetShaderInfoLog(shader, len(message), None, message)
            self.glDeleteShader(shader)
            raise RuntimeError("GPU shader compilation failed: " + message.value.decode("utf-8", "replace"))
        return shader

    def link_program(self, shaders):
        program = self.glCreateProgram()
        for shader in shaders:
            self.glAttachShader(program, shader)
        self.glLinkProgram(program)
        status = ct.c_int()
        self.glGetProgramiv(program, GL_LINK_STATUS, ct.byref(status))
        if not status.value:
            length = ct.c_int()
            self.glGetProgramiv(program, GL_INFO_LOG_LENGTH, ct.byref(length))
            message = ct.create_string_buffer(max(1, length.value))
            self.glGetProgramInfoLog(program, len(message), None, message)
            self.glDeleteProgram(program)
            raise RuntimeError("GPU program linking failed: " + message.value.decode("utf-8", "replace"))
        return program
