# GPU rendering decisions — Mandelbot

Research checked on 2026-10-21. All code and palettes are original Linux project
material; the Windows reference implementation was not used.

## Primary sources

- [GTK 3 GLArea](https://docs.gtk.org/gtk3/class.GLArea.html): GTK manages the
  context and destination framebuffer. Resources are created with a current
  context and released before unrealization.
- [Khronos ARB_gpu_shader_fp64](https://registry.khronos.org/OpenGL/extensions/ARB/ARB_gpu_shader_fp64.txt):
  shaders support double-precision arithmetic and uniforms. Exponential and
  logarithmic colour calculations use float after the precision-sensitive orbit.
- [mathr: Deep zoom theory and practice](https://www.mathr.co.uk/blog/2021-05-14_deep_zoom_theory_and_practice.html):
  perturbation can reduce deep-zoom arithmetic cost, but needs precision/glitch
  detection and repair. It is not implemented here. The bounded existing tours
  can be calculated directly in double precision.

## Chosen implementation and measurements

The machine exposes an accelerated AMD Radeon RX 7600, 8 GiB VRAM, with Mesa
25.2.8 and OpenGL 4.6. Gtk.GLArea uses this actual renderer; the label is read
from its GL context, not inferred from hardware inventory.

Native physical pixels eliminate the old small-image enlargement. Ultra uses a
rotated four-sample pattern. Increasing the iteration limit with zoom avoids
prematurely marking fine exterior detail as interior. A larger bailout radius
stabilizes continuous escape colouring. Cyclic cubic palette interpolation,
linear-light sample averaging, and stationary dithering improve gradients.

The first direct FP64 Ultra benchmark at 3840×2160 took approximately 136 ms
for the whole set, 394 ms for Seahorse valley, and 806 ms at its deepest point.
These are completed detail-render times, not presentation frame rates. A trial
using compensated float pairs with a precision guard failed exact boundary
comparisons and did not improve speed enough. It was removed from the product.

The retained approach computes FP64 detail in bounded strips into a back
texture, then swaps only completed images. The front image follows the camera
through GPU texture reprojection between detail updates. This separates smooth
motion from expensive orbit calculation. Colour textures filter in linear
light. The normal display path performs no synchronous pixel readback and
does not upload CPU-rendered frames. During faster motion there can be temporary
magnification between refinements; pausing completes the exact current view.

## Correctness checks

- Pixel spacing is computed once in CPU double precision and sent as a double
  uniform. Shader coordinates explicitly preserve arithmetic ordering. This
  removed boundary mismatches caused by different coordinate rounding.
- Actual GPU escape counts are read back and compared exactly with the original
  CPU reference at 25,480 grid points across all four tour regions, including
  their closest zooms, plus five analytically known points.
- A fully refined, paused 4K image is compared against a direct 4K render;
  the allowed difference is at most two 8-bit channel levels from the sRGB
  presentation round trip, with no geometry tolerance or downscaling.
- Benchmarks wait for GPU completion. GUI checks separately measure presentation
  rate, minimum motion speed, actual framebuffer dimensions, pause/refinement,
  preference changes, fullscreen exit, and desktop integration.

The reproducible checks are `scripts/verify_gpu.py` and `scripts/smoke_gui.py`.
Final measured results and limitations are in `docs/VERIFICATION.md`.
