import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from merge_seeds import normalize


class NormalizeTests(unittest.TestCase):
    def make_record(self, engine, year_from=None, year_to=None):
        return normalize(
            {
                "make": "Fiat",
                "model": "Uno",
                "engine": engine,
                "year_from": year_from,
                "year_to": year_to,
                "capacity_liters": 3.5,
                "oil_brand": "Petronas",
                "oil_name": "Selènia K 15W-40",
                "sae_viscosity": "15W-40",
                "oil_type": "Semissintético",
                "notes": None,
            }
        )

    def test_engine_year_range_sets_both_endpoints(self):
        record = self.make_record("1.6 (2016-2020)", 20, 20)
        self.assertEqual(record["year_from"], 2016)
        self.assertEqual(record["year_to"], 2020)

    def test_engine_single_year_sets_both_endpoints(self):
        record = self.make_record("1.8 8V Flex (2010)", 20, 20)
        self.assertEqual(record["year_from"], 2010)
        self.assertEqual(record["year_to"], 2010)

    def test_explicit_years_are_preserved(self):
        record = self.make_record("2.0 (2016-2020)", 2014, 2015)
        self.assertEqual(record["year_from"], 2014)
        self.assertEqual(record["year_to"], 2015)


if __name__ == "__main__":
    unittest.main()
