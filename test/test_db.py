import unittest

from app import db
from app.config import database_url


class DatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dsn = database_url(test=True)
        db.initialize(cls.dsn)

    def test_row_counts(self):
        self.assertGreater(db.healthcheck(self.dsn), 4000)

    def test_makes_and_models(self):
        with db.connection(self.dsn) as conn:
            self.assertIn("Audi", db.list_makes(conn))
            self.assertIn("A1", db.list_models(conn, "Audi"))
            self.assertEqual(db.list_models(conn, "MarcaInexistente"), [])

    def test_variants(self):
        with db.connection(self.dsn) as conn:
            variants = db.list_variants(conn, "Audi", "A1")
        self.assertTrue(variants)
        self.assertTrue(all(variant["label"] for variant in variants))

    def test_filtered_recommendations(self):
        with db.connection(self.dsn) as conn:
            rows = db.get_recommendations(
                conn,
                "Volkswagen",
                "FOX",
                "1.6 L4 MSI 16V (F)",
                2015,
                2021,
                exact=True,
            )
        self.assertTrue(rows)
        self.assertTrue(all(row["oil_brand"] for row in rows))

    def test_unfiltered_recommendations(self):
        with db.connection(self.dsn) as conn:
            all_rows = db.get_recommendations(conn, "Volkswagen", "FOX")
            filtered_rows = db.get_recommendations(
                conn, "Volkswagen", "FOX", "1.6 L4 MSI 16V (F)", 2015, 2021, exact=True
            )
        self.assertGreater(len(all_rows), len(filtered_rows))

    def test_exact_variant_with_null_year_to(self):
        with db.connection(self.dsn) as conn:
            exact = db.get_recommendations(
                conn, "BMW", "M5", "4.4 V8 DFI/Bi-TB 32V", 2017, None, exact=True
            )
            expected = conn.execute(
                "SELECT COUNT(*) AS count FROM vehicles v "
                "JOIN recommendations r ON r.vehicle_id = v.id "
                "WHERE v.make = 'BMW' AND v.model = 'M5' "
                "AND v.engine = '4.4 V8 DFI/Bi-TB 32V' "
                "AND v.year_from = 2017 AND v.year_to IS NULL"
            ).fetchone()["count"]
            unfiltered = db.get_recommendations(conn, "BMW", "M5")
        self.assertTrue(exact)
        self.assertEqual(len(exact), expected)
        self.assertLess(len(exact), len(unfiltered))

    def test_empty_result(self):
        with db.connection(self.dsn) as conn:
            rows = db.get_recommendations(conn, "MarcaInexistente", "ModeloInexistente")
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
