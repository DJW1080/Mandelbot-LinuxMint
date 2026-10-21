"""User-visible quality, physical pixels, and very slow motion contracts."""

import math
import unittest

from mandelbot import config, tour


class QualityTests(unittest.TestCase):
    def test_maximum_quality_is_default_and_preserves_legacy_choices(self):
        self.assertEqual(config.Settings().quality, "Ultra")
        for name in ("Eco", "Balanced", "High", "Ultra"):
            self.assertEqual(config.Settings(quality=name).quality, name)

    def test_lowest_speed_is_fifty_times_slower_than_old_minimum(self):
        self.assertEqual(config.MIN_SPEED, 0.01)
        self.assertEqual(config.Settings(speed=0.01).speed, 0.01)
        self.assertEqual(tour.sample(50, 0.01), tour.sample(1, 0.5))

    def test_logarithmic_slider_preserves_endpoints_and_saved_speeds(self):
        from mandelbot.quality import speed_to_position, position_to_speed
        self.assertAlmostEqual(position_to_speed(0), config.MIN_SPEED)
        self.assertAlmostEqual(position_to_speed(1), config.MAX_SPEED)
        for speed in (0.01, 0.025, 0.1, 0.5, 1.3, 2):
            self.assertAlmostEqual(position_to_speed(speed_to_position(speed)), speed)
        midpoint = position_to_speed(0.5)
        self.assertAlmostEqual(midpoint, math.sqrt(config.MIN_SPEED * config.MAX_SPEED))

    def test_native_pixels_include_hidpi_and_portrait_displays(self):
        from mandelbot.quality import physical_dimensions
        self.assertEqual(physical_dimensions(1920, 1080, 2), (3840, 2160))
        self.assertEqual(physical_dimensions(1080, 1920, 2), (2160, 3840))
        self.assertEqual(physical_dimensions(640, 480, 1), (640, 480))

    def test_zoom_increases_detail_without_unbounded_gpu_work(self):
        from mandelbot.quality import iteration_limit, QUALITY
        wide = iteration_limit("Ultra", 3.6)
        deep = iteration_limit("Ultra", 0.00002)
        self.assertGreaterEqual(wide, 1024)
        self.assertGreater(deep, wide)
        self.assertLessEqual(iteration_limit("Ultra", 1e-7), 4096)
        self.assertEqual(QUALITY["Ultra"].samples, 4)


if __name__ == "__main__":
    unittest.main()
