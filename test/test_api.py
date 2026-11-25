import os
import unittest
from unittest.mock import patch

import psycopg
from fastapi.testclient import TestClient

from app import db
from app.config import database_url
from app.main import app


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dsn = database_url(test=True)
        db.initialize(cls.dsn)
        cls.environment = patch.dict(os.environ, {"DATABASE_URL": cls.dsn})
        cls.environment.start()
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls.environment.stop()

    def test_health(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_health_error_hides_diagnostics(self):
        with patch(
            "app.main.db.healthcheck", side_effect=psycopg.Error("secret diagnostic")
        ):
            response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("secret diagnostic", response.text)
        self.assertNotIn("detail", response.json())

    def test_index(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Qual óleo para meu carro?", response.text)

    def test_makes(self):
        response = self.client.get("/api/makes")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Audi", response.json())

    def test_models_and_variants(self):
        models = self.client.get("/api/models", params={"make": "Audi"}).json()
        self.assertIn("A1", models)
        variants = self.client.get(
            "/api/variants", params={"make": "Audi", "model": "A1"}
        ).json()
        self.assertTrue(variants)
        self.assertIn("label", variants[0])

    def test_recommendations(self):
        response = self.client.get(
            "/api/recommendations",
            params={"make": "Audi", "model": "A1", "engine": "1.4", "exact": "true"},
        )
        self.assertEqual(response.status_code, 200)
        rows = response.json()
        self.assertTrue(rows)
        self.assertIn("oil_name", rows[0])

    def test_exact_variant_filters_null_fields(self):
        params = {"make": "Chevrolet", "model": "COBALT"}
        unfiltered = self.client.get("/api/recommendations", params=params).json()
        exact = self.client.get(
            "/api/recommendations", params={**params, "year_to": 2016, "exact": "true"}
        ).json()
        self.assertTrue(exact)
        self.assertLess(len(exact), len(unfiltered))

    def test_recommendations_empty(self):
        response = self.client.get(
            "/api/recommendations", params={"make": "NaoExiste", "model": "NaoExiste"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])


if __name__ == "__main__":
    unittest.main()
