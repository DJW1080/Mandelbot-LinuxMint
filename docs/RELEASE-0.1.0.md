# Mandelbot 0.1.0

First public release of an independently written Mandelbrot screensaver for
Linux Mint Cinnamon on X11.

## Included

- Native GTK settings window with live preview, pause, next-region and fullscreen controls.
- Hardware OpenGL rendering with double-precision orbit calculations at native display resolution.
- Ultra quality with four samples per pixel, smooth colour gradients and progressive refinement.
- Twelve original colour themes: Aurora, Ember, Ocean, Forest, Violet, Sunset, Ice,
  Rose, Copper, Neon, Sandstone and Monochrome.
- Logarithmic journey speed from 0.01× to 2.00×.
- Optional X11 idle activation and login startup, with Cinnamon retaining control of screen locking.
- Debian installer, desktop menu entry, source code and verification scripts.

## Install

Requires Linux Mint Cinnamon on X11, an amd64 system and hardware OpenGL 4.0 or
newer. Tested on Linux Mint 22.3 with an AMD Radeon RX 7600.

Download `mandelbot_0.1.0_amd64.deb` and `SHA256SUMS` into the same directory:

```sh
sha256sum --check SHA256SUMS
sudo apt install ./mandelbot_0.1.0_amd64.deb
```

Then open **Mandelbot** from the application menu. To update an existing copy,
run `mandelbot --quit` before replacing its files, then reopen it after installation.

Local experimental builds were numbered 0.2.x before the first public version
was selected. Users of those development builds must explicitly allow the
version change with `sudo apt install --allow-downgrades ./mandelbot_0.1.0_amd64.deb`.
The public 0.1.0 release includes the GPU and colour-theme improvements.

## Verification and limits

The release is checked with the unit suite, package-content audit and extracted
launcher/reference renderer. Hardware GPU and interactive GUI verification cover
the same rendering implementation; see `docs/VERIFICATION.md` for exact evidence.

Mandelbot is a visual screensaver, not a replacement password lock screen.
Wayland and software OpenGL rendering are unsupported. Password lock/unlock,
multi-monitor hardware and a fresh login are not claimed as end-to-end tested.
At faster speeds the previous complete image can be magnified between detail
updates; pausing finishes the exact current view.

The project is MIT licensed. No original Windows application code or assets are
included in the repository, source archive or installer.
