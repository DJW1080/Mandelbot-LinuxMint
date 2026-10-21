"""Every selectable theme must persist and cross the native colour boundary."""

from pathlib import Path
import tempfile
import unittest

from mandelbot.config import Settings, load_settings, save_settings
from mandelbot.palettes import (PALETTES, PALETTE_COLOURS, PALETTE_STOP_COUNT,
                                RGB_CHANNEL_COUNT, MAX_CHANNEL_VALUE)
from mandelbot.renderer import Renderer


class PaletteTests(unittest.TestCase):
    def test_colour_stops_are_complete_and_valid(self):
        for name, stops in PALETTE_COLOURS.items():
            with self.subTest(palette=name):
                self.assertEqual(len(stops), PALETTE_STOP_COUNT)
                for stop in stops:
                    self.assertEqual(len(stop), RGB_CHANNEL_COUNT)
                    for channel in stop:
                        self.assertIs(type(channel), int)
                        self.assertTrue(0 <= channel <= MAX_CHANNEL_VALUE)

    def test_every_theme_survives_save_and_reload(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            for name in PALETTES:
                with self.subTest(palette=name):
                    settings = Settings(palette=name, speed=0.01, quality="Ultra")
                    save_settings(settings, path)
                    self.assertEqual(load_settings(path), settings)

    def test_native_themes_are_distinct_with_identical_interiors(self):
        renderer = Renderer()
        frames = []
        centre_offset = (12 * 33 + 16) * 4
        for name in PALETTES:
            with self.subTest(palette=name):
                pixels = bytes(renderer.render(33, 25, -0.5, 0, 3.5, 120, name, 0))
                if frames:
                    self.assertEqual(pixels[centre_offset:centre_offset + 4],
                                     frames[0][centre_offset:centre_offset + 4])
                self.assertNotIn(pixels, frames)
                frames.append(pixels)


if __name__ == "__main__":
    unittest.main()
