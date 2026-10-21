"""Behaviour checks: fractal maths, validated settings, tours and idle safety."""

import importlib
import json
import math
from pathlib import Path
import tempfile
import unittest


class ApplicationTest(unittest.TestCase):
    def module(self, name):
        try:
            return importlib.import_module(f"mandelbot.{name}")
        except ModuleNotFoundError as error:
            if error.name.startswith("mandelbot"):
                self.fail(f"Expected first-run failure: {name} is not implemented yet")
            raise


class SettingsTests(ApplicationTest):
    def test_missing_file_uses_safe_opt_in_defaults(self):
        config = self.module("config")
        with tempfile.TemporaryDirectory() as folder:
            settings = config.load_settings(Path(folder) / "missing.json")
        self.assertFalse(settings.automatic)
        self.assertGreater(settings.idle_minutes, 0)

    def test_settings_round_trip_retains_user_choices(self):
        config = self.module("config")
        settings = config.Settings(palette="Ember", quality="High", speed=1.5,
                                   idle_minutes=7, automatic=True)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "nested/settings.json"
            config.save_settings(settings, path)
            self.assertEqual(config.load_settings(path), settings)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(list(path.parent.iterdir()), [path])

    def test_invalid_numbers_and_unknown_choices_are_rejected(self):
        config = self.module("config")
        for fields in [{"speed": float("nan")}, {"speed": float("inf")},
                       {"speed": True}, {"speed": 0}, {"speed": 9},
                       {"idle_minutes": -1}, {"idle_minutes": 1.5},
                       {"idle_minutes": True}, {"automatic": "yes"},
                       {"autostart": "yes"}, {"autostart": True, "automatic": False},
                       {"palette": "missing"}, {"quality": "missing"}]:
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                config.Settings(**fields)

    def test_corrupt_settings_are_reported_and_preserved(self):
        config = self.module("config")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            path.write_text('{"palette":', encoding="utf-8")
            with self.assertRaises(ValueError):
                config.load_settings(path)
            self.assertEqual(path.read_text(), '{"palette":')

    def test_unknown_settings_do_not_silently_disappear(self):
        config = self.module("config")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            path.write_text(json.dumps({"unknown": 42}))
            with self.assertRaises(ValueError):
                config.load_settings(path)


class FractalTests(ApplicationTest):
    def test_known_interior_and_exterior_points(self):
        renderer = self.module("renderer").Renderer()
        for real, imaginary in [(0, 0), (-1, 0), (-0.125, 0)]:
            self.assertEqual(renderer.escape(real, imaginary, 200), 200)
        self.assertEqual(renderer.escape(3, 0, 200), 1)
        self.assertEqual(renderer.escape(2, 0, 200), 2)
        self.assertLess(renderer.escape(0, 2, 200), 200)

    def test_complex_conjugates_have_equal_escape_counts(self):
        renderer = self.module("renderer").Renderer()
        for real, imaginary in [(-0.74, 0.18), (0.3, 0.6), (-1.4, 0.12)]:
            self.assertEqual(renderer.escape(real, imaginary, 400),
                             renderer.escape(real, -imaginary, 400))

    def test_render_has_opaque_interior_and_coloured_exterior(self):
        renderer = self.module("renderer").Renderer()
        pixels = renderer.render(65, 49, -0.5, 0, 3.5, 150, "Aurora", 0)
        import struct
        colours = struct.unpack(f"{65 * 49}I", pixels)
        self.assertTrue(all(colour >> 24 == 255 for colour in colours))
        self.assertGreater(len(set(colours)), 100)
        self.assertEqual(colours[24 * 65 + 32] & 0xFFFFFF, 0x05090F)

    def test_palette_changes_colour_without_changing_interior(self):
        renderer = self.module("renderer").Renderer()
        first = renderer.render(33, 25, -0.5, 0, 3.5, 120, "Aurora", 0)
        second = renderer.render(33, 25, -0.5, 0, 3.5, 120, "Ember", 0)
        self.assertNotEqual(first, second)
        offset = (12 * 33 + 16) * 4
        self.assertEqual(first[offset:offset + 4], second[offset:offset + 4])

    def test_render_rejects_unsafe_dimensions_and_nonfinite_coordinates(self):
        renderer = self.module("renderer").Renderer()
        for width, height, centre, span in [(0, 20, 0, 3), (-1, 20, 0, 3),
                                           (20000, 20000, 0, 3),
                                           (20, 20, math.nan, 3),
                                           (20, 20, 0, 0)]:
            with self.subTest(width=width, height=height, centre=centre):
                with self.assertRaises(ValueError):
                    renderer.render(width, height, centre, 0, span, 120, "Aurora", 0)


class TourTests(ApplicationTest):
    def test_tour_stays_finite_and_respects_precision_bounds(self):
        tour = self.module("tour")
        names = set()
        for seconds in range(0, 480, 3):
            view = tour.sample(seconds, 1)
            names.add(view.name)
            self.assertTrue(all(math.isfinite(value) for value in
                                [view.real, view.imaginary, view.span, view.opacity]))
            self.assertGreaterEqual(view.span, 0.000001)
            self.assertLessEqual(view.span, 4)
            self.assertGreaterEqual(view.opacity, 0)
            self.assertLessEqual(view.opacity, 1)
        self.assertGreaterEqual(len(names), 3)

    def test_speed_changes_journey_time_not_geometry(self):
        tour = self.module("tour")
        self.assertEqual(tour.sample(12, 2), tour.sample(24, 1))
        self.assertNotEqual(tour.sample(12, 1).span, tour.sample(24, 1).span)


class IdlePolicyTests(ApplicationTest):
    def test_waits_for_threshold_and_known_inactive_locker(self):
        policy = self.module("lifecycle").IdlePolicy(60)
        self.assertEqual(policy.evaluate(30, False), "wait")
        self.assertEqual(policy.evaluate(70, None), "wait")
        self.assertEqual(policy.evaluate(71, True), "wait")
        self.assertEqual(policy.evaluate(0, False), "wait")
        self.assertEqual(policy.evaluate(61, False), "start")

    def test_input_stops_saver_and_allows_a_future_idle_period(self):
        policy = self.module("lifecycle").IdlePolicy(60)
        self.assertEqual(policy.evaluate(61, False), "start")
        self.assertEqual(policy.evaluate(62, False), "wait")
        self.assertEqual(policy.evaluate(0, False), "stop")
        self.assertEqual(policy.evaluate(61, False), "start")

    def test_lock_activation_or_unknown_state_stops_visual(self):
        for lock_state in [True, None]:
            with self.subTest(lock_state=lock_state):
                policy = self.module("lifecycle").IdlePolicy(60)
                self.assertEqual(policy.evaluate(61, False), "start")
                self.assertEqual(policy.evaluate(62, lock_state), "stop")
                self.assertEqual(policy.evaluate(63, False), "wait")
                self.assertEqual(policy.evaluate(0, False), "wait")
                self.assertEqual(policy.evaluate(61, False), "start")

    def test_dismissal_does_not_immediately_reopen_saver(self):
        policy = self.module("lifecycle").IdlePolicy(60)
        policy.evaluate(61, False)
        policy.dismiss()
        self.assertEqual(policy.evaluate(62, False), "wait")
        self.assertEqual(policy.evaluate(0, False), "wait")
        self.assertEqual(policy.evaluate(61, False), "start")


if __name__ == "__main__":
    unittest.main()
