import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.config import database_url
from app.main import app
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

    def test_forwarded_for_is_used_as_client_key(self):
        environment = {
            "RATE_LIMIT_PER_MINUTE": "2",
            "DATABASE_URL": database_url(test=True),
        }
        with patch.dict(os.environ, environment):
            client = TestClient(app)
            headers = {"X-Forwarded-For": "203.0.113.9, 10.0.0.1"}
            self.assertEqual(client.get("/api/makes", headers=headers).status_code, 200)
            self.assertEqual(client.get("/api/makes", headers=headers).status_code, 200)
            self.assertEqual(client.get("/api/makes", headers=headers).status_code, 429)
            other = client.get(
                "/api/makes", headers={"X-Forwarded-For": "203.0.113.10"}
            )
            self.assertEqual(other.status_code, 200)


if __name__ == "__main__":
    unittest.main()
