#!/usr/bin/python3
"""Build a Debian package from an explicit allowlist of new Linux material."""

import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from mandelbot import __version__


def copy(source, destination, mode=0o644):
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    destination.chmod(mode)


def main():
    architecture = subprocess.check_output(['dpkg', '--print-architecture'], text=True).strip()
    output = ROOT / 'dist'
    output.mkdir(exist_ok=True)
    package = output / f'mandelbot_{__version__}_{architecture}.deb'
    with tempfile.TemporaryDirectory(prefix='mandelbot-package-') as folder:
        stage = Path(folder)
        library = stage / 'usr/lib/mandelbot'
        for source in sorted((ROOT / 'mandelbot').glob('*.py')):
            copy(source, library / 'mandelbot' / source.name)
        for filename in ['fullscreen.vert', 'mandelbrot.frag', 'present.frag']:
            copy(ROOT / 'mandelbot/shaders' / filename, library / 'mandelbot/shaders' / filename)
        copy(ROOT / 'build/libmandelbot.so', library / 'libmandelbot.so')
        copy(ROOT / 'bin/mandelbot', stage / 'usr/bin/mandelbot', 0o755)
        copy(ROOT / 'data/mandelbot.desktop', stage / 'usr/share/applications/mandelbot.desktop')
        copy(ROOT / 'data/mandelbot.svg', stage / 'usr/share/icons/hicolor/scalable/apps/mandelbot.svg')
        copy(ROOT / 'README.md', stage / 'usr/share/doc/mandelbot/README.md')
        copy(ROOT / 'docs/GPU-RESEARCH.md', stage / 'usr/share/doc/mandelbot/docs/GPU-RESEARCH.md')
        copy(ROOT / 'LICENSE', stage / 'usr/share/doc/mandelbot/copyright')
        control = stage / 'DEBIAN'
        control.mkdir()
        installed_kib = sum(path.stat().st_size for path in stage.rglob('*') if path.is_file()) // 1024 + 1
        (control / 'control').write_text(
            f'Package: mandelbot\nVersion: {__version__}\nSection: graphics\nPriority: optional\n'
            f'Architecture: {architecture}\nMaintainer: Mandelbot Project <maintainer@localhost>\n'
            f'Installed-Size: {installed_kib}\n'
            'Depends: python3 (>= 3.10), python3-gi, python3-cairo, python3-gi-cairo, '
            'gir1.2-gtk-3.0, libgl1, libx11-6, libxss1, libc6 (>= 2.35), cinnamon-screensaver\n'
            'Description: Native Mandelbrot journeys for Linux Mint\n'
            ' Independent fractal renderer, live settings, fullscreen display and an\n'
            ' optional Cinnamon X11 idle watcher. Desktop locking remains with Cinnamon.\n')
        checksums = []
        for path in sorted((stage / 'usr').rglob('*')):
            if path.is_file():
                checksums.append(f'{hashlib.md5(path.read_bytes()).hexdigest()}  {path.relative_to(stage)}')
        (control / 'md5sums').write_text('\n'.join(checksums) + '\n')
        # A developer's permissive umask must not make installed code writable.
        for directory in [stage, *(path for path in stage.rglob('*') if path.is_dir())]:
            directory.chmod(0o755)
        for metadata in control.iterdir():
            metadata.chmod(0o644)
        subprocess.run(['dpkg-deb', '--root-owner-group', '--build', str(stage), str(package)], check=True)
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    (output / 'SHA256SUMS').write_text(f'{digest}  {package.name}\n')
    print(f'Built {package}\nSHA256 {digest}')


if __name__ == '__main__':
    main()
