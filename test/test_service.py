import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from entrypoint import ensure_initialized, wait_for_database

from app import db
from app.config import database_url


class ServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        cls.compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        cls.dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
        cls.dsn = database_url(test=True)
        db.initialize(cls.dsn)

    def test_dockerfile_runs_entrypoint_as_non_root(self):
        self.assertIn("FROM python:3.12-slim", self.dockerfile)
        self.assertIn("USER appuser", self.dockerfile)
        self.assertIn('CMD ["python", "scripts/entrypoint.py"]', self.dockerfile)

    def test_compose_defines_app_and_db(self):
        self.assertIn("  db:", self.compose)
        self.assertIn("  app:", self.compose)
        self.assertIn("condition: service_healthy", self.compose)
        self.assertIn("restart: unless-stopped", self.compose)
        self.assertIn("what_oil_pgdata:", self.compose)
        self.assertIn("healthcheck:", self.compose)

    def test_dockerignore_excludes_dev_artifacts(self):
        self.assertIn(".venv", self.dockerignore)
        self.assertIn("images/", self.dockerignore)
        self.assertIn("data/raw/", self.dockerignore)

    def test_bootstrap_keeps_existing_data(self):
        before = db.healthcheck(self.dsn)
        wait_for_database(self.dsn, timeout=5)
        ensure_initialized(self.dsn)
        self.assertEqual(db.healthcheck(self.dsn), before)


if __name__ == "__main__":
    unittest.main()
