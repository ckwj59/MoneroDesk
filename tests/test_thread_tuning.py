import unittest

import app


class ThreadRecommendationTests(unittest.TestCase):
    def test_8940hx_recommends_measured_middle_ground(self):
        # 16 physical / 32 logical cores and 64 MiB L3: 24 was faster than
        # either 16 or 32 in repeated local RandomX worker measurements.
        self.assertEqual(app.recommend_threads(16, 32, 64 * 1024**2), 24)

    def test_small_cache_limits_physical_worker_count(self):
        self.assertEqual(app.recommend_threads(16, 32, 16 * 1024**2), 16)

    def test_missing_cache_uses_physical_core_estimate(self):
        self.assertEqual(app.recommend_threads(8, 16, 0), 12)


if __name__ == '__main__':
    unittest.main(verbosity=2)
