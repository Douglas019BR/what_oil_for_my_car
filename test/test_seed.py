import json
import re
import unittest
from pathlib import Path

SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "seed.json"


class SeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))

    def test_sources(self):
        sources = self.seed["meta"]["sources"]
        self.assertEqual(len(sources), 6)
        self.assertIn("Tabela-TotalEnergies-Leves-2026.pdf", sources)
        self.assertIn("Tabela-Ipiranga-F1-Master-2025.pdf", sources)
        self.assertIn("Tabela-YPF-Leves-2026-06.pdf", sources)
        self.assertNotIn("Tabela-Total.pdf", sources)
        self.assertNotIn("tabela-lubrificantes-carros.pdf", sources)

    def test_record_count(self):
        self.assertGreater(len(self.seed["records"]), 6000)

    def test_recent_brands_present(self):
        brands = {record["oil_brand"] for record in self.seed["records"]}
        self.assertIn("YPF", brands)
        self.assertIn("Total", brands)
        self.assertIn("Ipiranga", brands)

    def test_required_fields(self):
        for record in self.seed["records"]:
            for field in ("make", "model", "oil_brand", "oil_name", "source_pdf"):
                self.assertTrue(record.get(field), f"missing {field} in {record}")
            self.assertIn(record["source_pdf"], self.seed["meta"]["sources"])

    def test_value_ranges(self):
        for record in self.seed["records"]:
            for field in ("year_from", "year_to"):
                value = record.get(field)
                if value is not None:
                    self.assertTrue(1900 <= value <= 2100)
            capacity = record.get("capacity_liters")
            if capacity is not None:
                self.assertTrue(0 < capacity <= 50)

    def test_no_manual_check_rows(self):
        for record in self.seed["records"]:
            self.assertNotEqual(record["oil_name"].lower(), "verificar manual")
            self.assertNotEqual((record.get("notes") or "").lower(), "verificar manual")

    def test_engine_years_match_year_fields(self):
        for record in self.seed["records"]:
            years = [
                int(year)
                for year in re.findall(r"(?:19|20)\d{2}", record.get("engine") or "")
            ]
            if len(set(years)) == 1 and record.get("year_from"):
                self.assertIn(years[0], (record["year_from"], record["year_to"]))

    def test_no_duplicates(self):
        keys = [tuple(sorted(record.items())) for record in self.seed["records"]]
        self.assertEqual(len(keys), len(set(keys)))


if __name__ == "__main__":
    unittest.main()
