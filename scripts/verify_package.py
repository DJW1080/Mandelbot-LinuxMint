#!/usr/bin/python3
"""Check the actual Debian payload and exercise its extracted application."""

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from mandelbot import __version__


def run(arguments, **kwargs):
    return subprocess.run(arguments, check=True, capture_output=True, text=True, **kwargs).stdout.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('package', type=Path)
    parser.add_argument('--gui', action='store_true', help='also run the interactive packaged GUI check')
    options = parser.parse_args()
    package = options.package.resolve()
    evidence = ROOT / 'build/evidence'
    evidence.mkdir(parents=True, exist_ok=True)
    results = {'package_file': str(package), 'sha256': hashlib.sha256(package.read_bytes()).hexdigest()}
    for field in ['Package', 'Version', 'Architecture', 'Depends']:
        results[field.lower()] = run(['dpkg-deb', '-f', str(package), field])
    assert results['package'] == 'mandelbot'
    assert results['version'] == __version__
    assert results['architecture'] == run(['dpkg', '--print-architecture'])
    archive_bytes = subprocess.check_output(['dpkg-deb', '--fsys-tarfile', str(package)])
    with tarfile.open(fileobj=io.BytesIO(archive_bytes)) as archive:
        for member in archive.getmembers():
            assert member.uid == member.gid == 0, 'Package files must belong to root'
            assert member.isfile() or member.isdir(), 'Unexpected archive member type'
            assert '..' not in Path(member.name).parts and not member.name.startswith('/')
            assert member.mode & 0o022 == 0, 'Package files must not be writable by group/others'
    expected = {f'usr/lib/mandelbot/mandelbot/{path.name}': path for path in (ROOT / 'mandelbot').glob('*.py')}
    for filename in ['fullscreen.vert', 'mandelbrot.frag', 'present.frag']:
        expected[f'usr/lib/mandelbot/mandelbot/shaders/{filename}'] = ROOT / 'mandelbot/shaders' / filename
    expected.update({
        'usr/lib/mandelbot/libmandelbot.so': ROOT / 'build/libmandelbot.so',
        'usr/bin/mandelbot': ROOT / 'bin/mandelbot',
        'usr/share/applications/mandelbot.desktop': ROOT / 'data/mandelbot.desktop',
        'usr/share/icons/hicolor/scalable/apps/mandelbot.svg': ROOT / 'data/mandelbot.svg',
        'usr/share/doc/mandelbot/README.md': ROOT / 'README.md',
        'usr/share/doc/mandelbot/docs/GPU-RESEARCH.md': ROOT / 'docs/GPU-RESEARCH.md',
        'usr/share/doc/mandelbot/copyright': ROOT / 'LICENSE',
    })
    with tempfile.TemporaryDirectory(prefix='mandelbot-package-check-') as folder:
        stage = Path(folder)
        run(['dpkg-deb', '-x', str(package), str(stage)])
        actual = {str(path.relative_to(stage)) for path in stage.rglob('*') if path.is_file()}
        assert actual == set(expected), 'The payload differs from the exact allowlist'
        for relative, source in expected.items():
            assert (stage / relative).read_bytes() == source.read_bytes(), relative
        results['matched_payload_files'] = len(expected)
        run(['dpkg-deb', '-e', str(package), str(stage / 'control')])
        for line in (stage / 'control/md5sums').read_text().splitlines():
            checksum, relative = line.split('  ', 1)
            assert hashlib.md5((stage / relative).read_bytes()).hexdigest() == checksum
        results['payload_checksums'] = 'passed'
        launcher = stage / 'usr/bin/mandelbot'
        assert os.access(launcher, os.X_OK)
        results['extracted_launcher'] = run([str(launcher), '--version'])
        assert results['extracted_launcher'] == f'Mandelbot {__version__}'
        menu_code = ('import sys;from gi.repository import Gio;'
                     'entry=Gio.DesktopAppInfo.new_from_filename(sys.argv[1]);'
                     'assert entry is not None;'
                     'assert set(entry.list_actions())=={"Fullscreen","Quit"};'
                     'print("desktop menu entry and actions passed")')
        environment = dict(os.environ, PATH=str(stage / 'usr/bin') + os.pathsep + os.environ['PATH'])
        results['desktop_menu_entry'] = run(['/usr/bin/python3', '-c', menu_code,
            str(stage / 'usr/share/applications/mandelbot.desktop')], env=environment)
        application_root = stage / 'usr/lib/mandelbot'
        code = ('import sys;sys.path.insert(0,sys.argv[1]);'
                'from mandelbot.renderer import Renderer;'
                'r=Renderer();assert r.escape(0,0,100)==100;'
                'assert len(r.render(32,24,-0.5,0,3.5,100,"Aurora",0))==3072;'
                'print("packaged renderer passed")')
        results['extracted_renderer'] = run(['/usr/bin/python3', '-c', code, str(application_root)])
        if options.gui:
            results['extracted_gui'] = json.loads(run(['/usr/bin/python3', str(ROOT / 'scripts/smoke_gui.py'),
                '--application-root', str(application_root), '--output', str(evidence / 'packaged')]))
    results['apt_simulation'] = run(['apt-get', '--simulate', 'install', str(package)])
    results['status'] = 'passed'
    (evidence / 'package-verification.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
