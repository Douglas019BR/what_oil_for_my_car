import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from entrypoint import wait_for_database

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

    def test_compose_defines_services(self):
        for service in ("  db:", "  app:", "  caddy:", "  backup:"):
            self.assertIn(service, self.compose)
        self.assertIn("condition: service_healthy", self.compose)
        self.assertIn("restart: unless-stopped", self.compose)
        self.assertIn("what_oil_pgdata:", self.compose)
        self.assertIn("caddy_data:", self.compose)
        self.assertIn("healthcheck:", self.compose)

    def test_app_is_loopback_only_and_hardened(self):
        self.assertIn("127.0.0.1:${APP_PORT:-8000}:8000", self.compose)
        self.assertIn("read_only: true", self.compose)
        self.assertIn("init: true", self.compose)
        self.assertIn("mem_limit: 512m", self.compose)
        self.assertIn("what_oil_for_my_car:${VERSION:-0.2.0}", self.compose)

    def test_deploy_files_exist(self):
        self.assertTrue((ROOT / "deploy" / "Caddyfile").exists())
        self.assertTrue((ROOT / "deploy" / "Caddyfile.auth").exists())
        self.assertTrue((ROOT / "deploy" / "backup.sh").exists())
        self.assertTrue((ROOT / "sql" / "migrations" / "001_initial.sql").exists())

    def test_dockerignore_excludes_dev_artifacts(self):
        self.assertIn(".venv", self.dockerignore)
        self.assertIn("images/", self.dockerignore)
        self.assertIn("data/raw/", self.dockerignore)

    def test_bootstrap_keeps_existing_data(self):
        before = db.healthcheck(self.dsn)
        wait_for_database(self.dsn, timeout=5)
        db.initialize(self.dsn, reset=False)
        self.assertEqual(db.healthcheck(self.dsn), before)
        with db.connection(self.dsn) as conn:
            versions = {
                row["version"]
                for row in conn.execute(
                    "SELECT version FROM schema_migrations"
                ).fetchall()
            }
        self.assertIn("001_initial", versions)


if __name__ == "__main__":
    unittest.main()
