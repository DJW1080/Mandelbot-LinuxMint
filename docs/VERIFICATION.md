# Mandelbot 0.1.0 verification

Release preparation date: 2026-10-21 (Australia/Melbourne).

Public 0.1.0 contains the rendering implementation previously exercised in local
0.2.1 development builds. Renumbering changes the release identifier and public
documentation, not the rendering, themes, controls or desktop integration.

## Release-specific checks

Fresh checks for the public 0.1.0 package passed:

- `make package`: all 28 unit tests passed and the Debian installer was rebuilt.
- `verify_package.py`: all 29 payload files matched current source bytes; root
  ownership, safe permissions, archive structure and payload checksums passed.
- Extracted `--version` returned `Mandelbot 0.1.0`; the extracted mathematical
  renderer and desktop entry/actions passed.
- APT simulation changes only Mandelbot. On the development workstation, moving
  from the local 0.2.1 label to public 0.1.0 is correctly reported as a downgrade;
  no dependencies or other packages are added or removed. The installed copy was
  not replaced as part of publishing this release.
- Installer SHA-256:
  `0081f114eecac4bf51a045323bfc9658212446023dcff74e0a268a88afffd65c`.

GPU and interactive GUI tests below were performed on the unchanged rendering
implementation before release renumbering; they were not repeated for this
version-only change.

## Hardware and GUI evidence

Checks performed on Linux Mint 22.3 Cinnamon X11 with AMD Radeon RX 7600,
Mesa 25.2.8 and OpenGL 4.6:

- All twelve themes produced distinct, detailed, opaque GPU images, identical
  interior pixels and seamless full-cycle colour wrapping. Switching back restored
  the same original pixels. The packaged selector rendered and saved every theme.
- 25,480 grid escape counts matched the CPU reference exactly at a 4,096 iteration
  cap, plus five analytically known points across all four tour regions.
- Native 3840×2160 Ultra rendering passed. A paused progressive image matched
  the direct render with zero channel differences. Median refinement strip time
  was approximately 14.8 ms; complete detail images took 159–812 ms by view.
  Detail-render time is distinct from presentation frame rate.
- Packaged GUI checks passed animation, paused control changes, 0.01× minimum
  motion, fullscreen dimensions, Escape dismissal, idle/login controls and
  simulated desktop-active dismissal. Desktop lock/power preferences were unchanged.
- The last theme GUI run skipped real idle activation because a session inhibitor
  was active. Earlier GPU-release checks exercised real X11 idle activation and
  D-Bus signal delivery on an isolated bus.
- Installed-app verification confirmed a visible window, actual amdgpu graphics
  work, no new errors and unchanged user preferences after a clean restart.
- A second launcher correctly exited 0 after forwarding to the same live app.

## Upgrade lesson

Leaving a development process running while its installed shader files were
replaced produced a shader compilation error. Gracefully stopping the old app
and reopening the installed version resolved it. The installation instructions
now explicitly require stopping Mandelbot before an upgrade. Launch verification
uses the session-bus owner and window PID, since the short-lived second launcher
is not the running application.

## Limits

No real password-lock/unlock cycle, multi-monitor hardware trial, fresh-login
startup or Wayland trial is claimed. Hardware results describe the tested GPU,
not a performance guarantee for other graphics cards. The app yields to Cinnamon
and is not a password lock screen. Software OpenGL contexts are rejected.

## Reproduce

```sh
make test
python3 scripts/verify_gpu.py
python3 scripts/smoke_gui.py
dbus-run-session --config-file scripts/private-bus.conf -- python3 scripts/smoke_private_bus.py
make package
python3 scripts/verify_package.py dist/mandelbot_0.1.0_amd64.deb --gui
```

Interactive checks briefly open windows and must run while the desktop is free.
They use isolated app preferences and never change Cinnamon lock/power settings.
Generated evidence is written to `build/evidence/` and is excluded from Git.
