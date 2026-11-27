import os
import unittest
from unittest.mock import patch

from app.rate_limit import allow, limit_per_minute, reset


class RateLimitTests(unittest.TestCase):
    def setUp(self):
        reset()

    def test_default_limit(self):
        self.assertEqual(limit_per_minute(), 120)

    def test_blocks_after_limit(self):
        with patch.dict(os.environ, {"RATE_LIMIT_PER_MINUTE": "2"}):
            self.assertTrue(allow("10.0.0.1"))
            self.assertTrue(allow("10.0.0.1"))
            self.assertFalse(allow("10.0.0.1"))
            self.assertTrue(allow("10.0.0.2"))

    def test_disabled(self):
        with patch.dict(os.environ, {"RATE_LIMIT_PER_MINUTE": "0"}):
            for _ in range(10):
                self.assertTrue(allow("10.0.0.3"))

    def test_invalid_value_falls_back(self):
        with patch.dict(os.environ, {"RATE_LIMIT_PER_MINUTE": "invalid"}):
            self.assertEqual(limit_per_minute(), 120)


if __name__ == "__main__":
    unittest.main()
