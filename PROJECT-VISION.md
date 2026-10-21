# Mandelbot for Linux Mint

Mandelbot is an independently written native Mandelbrot screensaver for Linux
Mint Cinnamon on X11. This document is the project's single source of truth.

## Public release

Version **0.1.0** is the first public release, prepared for
`DJW1080/Mandelbot-LinuxMint`. It includes the completed GPU renderer and twelve
colour themes. Earlier local development versions used 0.2.x labels; public
version numbering begins at 0.1.0 by the project owner's instruction.

## Product requirements

- Native GTK settings with an animated preview, pause, next region, fullscreen
  launch, quality controls and persistent preferences.
- Hardware OpenGL 4.0 or newer, double-precision Mandelbrot orbit calculations,
  physical display resolution including HiDPI scaling, and bounded zoom depth.
- Four quality levels, up to four samples per pixel, zoom-dependent iteration
  limits up to 4,096, smooth cyclic colours and linear-light averaging/filtering.
- Twelve original themes supplied by one shared colour-definition module.
- Logarithmic motion speed from 0.01× to 2.0×. Refine full-resolution images in
  GPU strips and present complete frames with camera reprojection between updates.
- Fullscreen input dismissal and per-monitor windows. Keep Cinnamon responsible
  for password locking and power management; never change those desktop settings.
- Optional idle activation and login startup, disabled until selected. Yield to
  Cinnamon's active or unknown lock state and honour session idle inhibitors.
- Atomic validated JSON preferences, clear error reporting, desktop menu actions,
  source-build instructions and an installable Debian package.

## Independence and provenance

The supplied Windows application served only as a reference for observable
user-facing capabilities. No original executable implementation was decompiled,
ported or incorporated. The Linux code, shaders, icon and colour themes are
original project material under the MIT licence. Windows MSI/ZIP/licence files
remain local references and are excluded from Git, release assets and packaging.
Matching every Windows feature or layout is not a completion requirement.

## Structure

- `mandelbot/`: GTK application, settings, desktop integration, GPU rendering and tours.
- `mandelbot/shaders/`: original OpenGL shaders.
- `native/`: CPU mathematical reference renderer, used for verification.
- `tests/`: mathematical, preferences, palette, quality and lifecycle tests.
- `scripts/`: build, package and reproducible verification helpers.
- `data/`: original icon and desktop entry.
- `docs/`: rendering research, release notes and published verification summary.
- `build/` and `dist/`: generated local evidence and release artifacts, excluded from Git.

## Engineering and release rules

Use descriptive constants and names, focused functions, useful comments and
readable tests. Keep detailed work and error history in local `LOG-BOOK.md`.
Pause on unexpected errors and report the error, possible causes and proposed
solution unless the user explicitly authorises diagnosis or repair. Git work
begins only after a working application has been tested; this prerequisite has
been met through unit, hardware GPU, packaged GUI and installed-app verification.

Before an installed upgrade, run `mandelbot --quit` and wait for the old process
to stop. Reopen after installation so in-memory code and shader files match.
A second launcher may normally exit after forwarding its command; verify the
actual owner of `org.mandelbot.Screensaver` on the session bus and its visible
window, not only the process ID returned by the launcher.

Publish only reviewed Linux source, documentation and original assets. Release
assets contain the Debian installer and its SHA-256 checksum. Exclude development
captures, workstation logs, caches, credentials and reference Windows materials.

## Acceptance boundaries

Source and packaged GUI checks have exercised native preview/fullscreen,
controls, all themes, saving, input dismissal and desktop integration. Mathematical
GPU comparisons use the independent CPU reference and exact escape counts.
Actual installed GPU rendering has been observed on an RX 7600. Details and
limits are in `docs/VERIFICATION.md`.

Do not equate a synthetic callback with a real password-lock cycle. Real
password lock/unlock, multi-monitor hardware, a fresh-login startup and Wayland
are not claimed as tested. The app creates ordinary fullscreen visuals and does
not replace Cinnamon's password lock screen. Software rendering is unsupported.
