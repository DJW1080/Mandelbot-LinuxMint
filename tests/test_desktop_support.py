"""File integration and presentation contracts, using isolated directories."""

import importlib
import json
from pathlib import Path
import tempfile
import time
import unittest


class SupportTests(unittest.TestCase):
    def module(self, name):
        try:
            return importlib.import_module(f"mandelbot.{name}")
        except ModuleNotFoundError as error:
            if error.name.startswith("mandelbot"):
                self.fail(f"Expected first-run failure: {name} is not implemented yet")
            raise

    def test_autostart_entry_round_trip_handles_spaces_and_percent(self):
        module = self.module("integration")
        from gi.repository import Gio
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "autostart/mandelbot.desktop"
            executable = Path(folder) / 'a folder 100%/mandelbot'
            executable.parent.mkdir()
            marker = Path(folder) / 'launched.json'
            executable.write_text('import json, sys\nfrom pathlib import Path\n'
                                  f'Path({str(marker)!r}).write_text(json.dumps(sys.argv[1:]))\n')
            executable.chmod(0o755)
            module.write_autostart(True, executable, path)
            entry = Gio.DesktopAppInfo.new_from_filename(str(path))
            self.assertIsNotNone(entry)
            self.assertIn("--watch", entry.get_commandline())
            self.assertIn('100%%', path.read_text())
            entry.launch([], None)
            deadline = time.monotonic() + 3
            while not marker.exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(marker.exists(), "The desktop entry must launch its actual target")
            self.assertEqual(json.loads(marker.read_text()), ['--watch'])
            module.write_autostart(False, executable, path)
            self.assertFalse(path.exists())

    def test_disabling_autostart_preserves_other_entries(self):
        module = self.module("integration")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "mandelbot.desktop"
            neighbour = Path(folder) / "other.desktop"
            neighbour.write_text("unrelated")
            module.write_autostart(False, Path('/usr/bin/mandelbot'), path)
            self.assertEqual(neighbour.read_text(), "unrelated")

    def test_dimensions_keep_aspect_and_bound_portrait_frames(self):
        module = self.module("presentation")
        for width, height in [(1920, 1080), (1080, 1920), (100, 3000)]:
            render_width, render_height = module.frame_dimensions(width, height, 1080)
            self.assertGreater(render_width, 0)
            self.assertGreater(render_height, 0)
            self.assertLessEqual(max(render_width, render_height), 1080)
            self.assertAlmostEqual(render_width / render_height, width / height, delta=0.01)

    def test_motion_grace_and_jitter_do_not_dismiss(self):
        module = self.module("presentation")
        self.assertFalse(module.motion_dismisses((100, 100), (500, 500), 0.1))
        self.assertFalse(module.motion_dismisses((100, 100), (102, 101), 2))
        self.assertTrue(module.motion_dismisses((100, 100), (120, 100), 2))


if __name__ == '__main__':
    unittest.main()
