# Mandelbot

A new native Mandelbrot screensaver for **Linux Mint Cinnamon on X11**.
Written independently in Python/GTK, GLSL and C, with original colour palettes and
an original icon. No Windows code or assets are included in the application.

## Install

Download `mandelbot_0.1.0_amd64.deb` from the
[v0.1.0 release](https://github.com/DJW1080/Mandelbot-LinuxMint/releases/tag/v0.1.0).
Open it with Mint's package installer, or run this from your download folder:

```sh
sudo apt install ./mandelbot_0.1.0_amd64.deb
```

Then open **Mandelbot** from the application menu. Installation adds the launcher
and application files; it does not change desktop locking, enable automatic
mode, or enable login startup.

Before upgrading an existing installation, run `mandelbot --quit` to stop both
its window and background watcher. Install the update, then reopen Mandelbot.
This ensures the running renderer and its shader files come from the same version.

The release includes `SHA256SUMS`. From the download folder, verify the installer
with `sha256sum --check SHA256SUMS`.

## Use

- Choose from 12 colour themes: Aurora, Ember, Ocean, Forest, Violet, Sunset,
  Ice, Rose, Copper, Neon, Sandstone and Monochrome. Changes appear in the live
  preview; use **Save preferences** to keep your choice. Existing saved themes
  remain compatible. Quality and journey speed update the
  live GPU preview. All qualities use native physical display resolution. Eco
  reduces orbit work; Ultra uses four samples per pixel and increases iterations
  as the camera zooms in (up to 4,096). Ultra is the default for new settings.
- Journey speed ranges from **0.01× to 2.00×**. The logarithmic slider gives
  useful control over slow speeds. Very slow is 50 times slower than the old
  0.5× minimum; a full region takes about 67 minutes at 0.01×.
- **Start fullscreen** displays the journey on each connected monitor.
  Any key, a click, scrolling, or moving the pointer dismisses the fullscreen
  display. A brief pointer grace period prevents the launch click from closing it.
- **Pause preview** pauses the window's animation. **Next region** changes the
  preview journey. Fullscreen starts its own journey.
- **Save preferences** keeps your choices. To enable the idle watcher, turn on
  **Start when idle**, choose a delay, and save. It keeps running after you close
  the settings window. Disable the switch and save to stop automatic mode.
- **Start automatically when I sign in** is a separate opt-in setting. Saving
  creates a per-user login entry. Closing the window while automatic mode is off
  ends the application.
- Use the application-menu **Stop Mandelbot** action or `mandelbot --quit` to
  stop both the window and background watcher for the current session.

Mandelbot displays visuals before Cinnamon's own screensaver takes over. It
does **not** replace the password lock screen or render behind its password
prompt. For a visible idle period, choose a Mandelbot delay shorter than the
desktop's own blanking/locking delay. The app never changes those settings or
inhibits desktop locking/suspend. Existing session idle inhibitors, such as those
used by presentations, suppress automatic display. Unknown desktop state also
stops the visual. Automatic activation requires an X11 Cinnamon session.

## Graphics and image quality

An accelerated **OpenGL 4.0 or newer** graphics driver is required. The settings
window identifies the actual renderer. Software rasterizers produce a clear
error instead of silently rendering on the CPU. No CUDA or ROCm installation
is needed. The included C renderer is retained as a mathematical test reference;
it does not render the application's preview or fullscreen image.

The GPU uses double-precision coordinates and orbit arithmetic, four spatial
samples per pixel in Ultra, smooth cyclic palette interpolation, linear-light
sample averaging, a larger escape radius for stable colouring, and subtle
stationary dithering. The renderer includes the monitor's HiDPI scale factor.

To keep controls and slow movement responsive, the GPU refines small sections
of a second native-resolution image. Only complete images become visible. The
last complete image follows the camera smoothly between detail updates, using
linear-light texture filtering. At faster speeds, some detail is temporarily
magnified between updates. Pause lets the exact current view finish refining.
Initial images and palette changes can take a short time to finish. The target
presentation rate is 30 fps; detail-update speed depends on the view and GPU.

Research, verification methods and performance evidence are recorded in
`docs/GPU-RESEARCH.md` and `docs/VERIFICATION.md`.

## Run from source

The compiler is needed only for source builds. On Mint 22.x the required packages
are GCC, make, Python 3, PyGObject, Pycairo, GTK 3 introspection, OpenGL, X11, and XScreenSaver:

```sh
sudo apt install gcc make python3-gi python3-gi-cairo python3-cairo gir1.2-gtk-3.0 libgl1 libx11-6 libxss1
make
./bin/mandelbot
```

```sh
./bin/mandelbot --fullscreen
./bin/mandelbot --watch
./bin/mandelbot --quit
```

`--watch` starts only if saved preferences enable automatic activation. If you
enable login startup while running from source, keep the project at the same
path, or save the startup preference again after moving/installing it.

## Verify and build the installer

```sh
make test
python3 scripts/verify_gpu.py
python3 scripts/smoke_gui.py
dbus-run-session --config-file scripts/private-bus.conf -- python3 scripts/smoke_private_bus.py
make package
python3 scripts/verify_package.py dist/mandelbot_0.1.0_amd64.deb --gui
```

The GUI check opens windows briefly, uses a temporary settings directory, and
checks a shortened idle interval. If password locking is already disabled, it
also briefly activates/deactivates Cinnamon's visual screensaver to check the
handoff. It never enables/disables password locking. Results and captures go to
`build/evidence/`. Do not run this interactive check while another person is
using the desktop.

`make package` builds an architecture-specific Debian package without installing
it. The package contains only allowlisted new application files. See
`docs/VERIFICATION.md` for the checks actually performed and their limitations.

## Settings, logs, and removal

- Preferences: `~/.config/mandelbot/settings.json`
- Optional login entry: `~/.config/autostart/mandelbot.desktop`
- Rotating log: `~/.local/state/mandelbot/application.log`

The corresponding XDG directory overrides are respected. Invalid settings are
reported and preserved. To reset preferences, first stop Mandelbot and move the
settings file aside. To remove it, disable login startup and save, quit Mandelbot,
then run `sudo apt remove mandelbot`. Personal settings are retained by apt.

`PROJECT-VISION.md` is the project's source of truth. Development work and errors
are recorded locally in `LOG-BOOK.md`; the published verification summary is in
`docs/VERIFICATION.md`. The Linux application uses the MIT licence in `LICENSE`.
The original Windows reference materials and local workstation logs are excluded
from this repository and its release assets.
