import unittest
from urllib.parse import parse_qs, urlsplit

from app.config import admin_url, replace_database


class ConfigTests(unittest.TestCase):
    def test_replace_database_drops_dbname_query(self):
        url = replace_database(
            "postgresql://user:pass@localhost:5432/prod?dbname=other&sslmode=require",  # pragma: allowlist secret
            "what_oil_test",
        )
        parts = urlsplit(url)
        self.assertEqual(parts.path, "/what_oil_test")
        self.assertEqual(parse_qs(parts.query), {"sslmode": ["require"]})

    def test_admin_url_drops_dbname_query(self):
        url = admin_url("postgresql://localhost:5432/prod?dbname=other")
        parts = urlsplit(url)
        self.assertEqual(parts.path, "/postgres")
        self.assertEqual(parts.query, "")


if __name__ == "__main__":
    unittest.main()
