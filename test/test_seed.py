import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED_PATH = ROOT / "data" / "seed.json"
IPIRANGA_RAW = ROOT / "data" / "raw" / "Tabela-Ipiranga-F1-Master-2025-raw.txt"

IPIRANGA_CODES = {
    "F1 Master Sintético 0W20 SP": 1,
    "F1 Master Sintético 5W30 SP": 2,
    "F1 Master Sintético 0W30 C2": 3,
    "F1 Master Sintético 5W30 C2/C3": 4,
    "F1 Master Sintético 5W40 SP": 5,
    "F1 Master Sintético 5W40 SN 508": 6,
    "F1 Master Sintético 5W40 SN 502": 7,
    "F1 Master Performance 10W30 SP": 8,
    "F1 Master Performance 10W40 SP": 9,
    "F1 Master Sintético 10W40 SP": 10,
    "Brutus Performance 15W40 CK-4": 11,
    "Brutus Sintético 10W40 E4": 12,
    "Brutus Performance CI 15W40": 13,
    "Brutus Alta Performance 15W40 CI-4": 14,
    "Brutus Protection T5 15W40 CH-4": 15,
}


def codes_in(text):
    return {int(value) for value in re.findall(r"\b(1[0-5]|[1-9])\b", text)}


def row_codes(lines, index):
    line = lines[index]
    parts = re.split(
        r"(?<![\d.])(?:1[0-5]|[1-9])(?:\s*,\s*(?:1[0-5]|[1-9]))*\s*$", line
    )
    found = codes_in(line[len(parts[0]) :]) if len(parts) > 1 else set()
    if found:
        return found
    if index + 1 < len(lines) and re.fullmatch(
        r"(?:\d{1,2}\s*,\s*)*\d{1,2}", lines[index + 1]
    ):
        return codes_in(lines[index + 1])
    return set()


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

    def test_no_concatenated_engines(self):
        for record in self.seed["records"]:
            engine = record.get("engine") or ""
            self.assertIsNone(
                re.search(r"\d\.\d\s+V\d\s+(?![-/(])\d\.\d\s+V\d", engine), engine
            )

    def test_no_impossible_model_engine_pairs(self):
        forbidden = {
            ("Chevrolet", "Camaro"): ("2.4 L4",),
            ("Chevrolet", "Celta"): ("1.8",),
            ("Nissan", "Sentra"): ("1.0 L3",),
            ("Ford", "F-150"): ("2.0 L4",),
        }
        for record in self.seed["records"]:
            for prefix in forbidden.get((record["make"], record["model"]), ()):
                self.assertFalse(
                    (record.get("engine") or "").startswith(prefix), record
                )

    def test_expected_models_present(self):
        models = {(record["make"], record["model"]) for record in self.seed["records"]}
        self.assertIn(("Chevrolet", "Camaro"), models)
        self.assertIn(("Ford", "F-150"), models)

    def test_no_elf_rubia_brand(self):
        for record in self.seed["records"]:
            if "Rubia" in record["oil_name"]:
                self.assertEqual(record["oil_brand"], "Total")

    def test_all_ipiranga_codes_match_source(self):
        lines = [
            line.strip()
            for line in IPIRANGA_RAW.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        unsupported = []
        for record in self.seed["records"]:
            if record["source_pdf"] != "Tabela-Ipiranga-F1-Master-2025.pdf":
                continue
            code = IPIRANGA_CODES.get(record["oil_name"])
            engine = record.get("engine") or ""
            supported = any(
                engine in line
                and (not record.get("year_from") or str(record["year_from"]) in line)
                and code in row_codes(lines, index)
                for index, line in enumerate(lines[43:], start=43)
            )
            if not supported:
                unsupported.append((record["model"], engine, record["oil_name"]))
        self.assertEqual(unsupported, [])

    def test_no_standalone_code_bleed(self):
        source = "Tabela-Ipiranga-F1-Master-2025.pdf"
        uncoded = [
            ("Chevrolet", "Equinox", "2.0 L4 DFI TB 16V", 2018),
            ("Chevrolet", "Montana", "1.4 L4 MPFI 8V", 2009),
            ("Toyota", "Corolla", "1.6 L4 MPFI 16V", 2007),
            ("Porsche", "Panamera", "3.0 V6 DFI Bi-TB 24V", 2017),
        ]
        for make, model, engine, year in uncoded:
            matches = [
                record
                for record in self.seed["records"]
                if record["source_pdf"] == source
                and record["make"] == make
                and record["model"] == model
                and record["engine"] == engine
                and record["year_from"] == year
            ]
            self.assertEqual(matches, [], (make, model, engine, year))

    def test_explicit_codes_are_kept(self):
        expected = [
            (
                "Toyota",
                "Corolla",
                "1.6 L4 MPFI 16V",
                2003,
                "F1 Master Sintético 5W30 C2/C3",
            ),
            (
                "Chevrolet",
                "Equinox",
                "1.5 L4 DFI TB 16V",
                2021,
                "F1 Master Sintético 0W20 SP",
            ),
        ]
        for make, model, engine, year, oil in expected:
            self.assertTrue(
                any(
                    record["source_pdf"] == "Tabela-Ipiranga-F1-Master-2025.pdf"
                    and record["make"] == make
                    and record["model"] == model
                    and record["engine"] == engine
                    and record["year_from"] == year
                    and record["oil_name"] == oil
                    for record in self.seed["records"]
                ),
                (make, model, engine, year, oil),
            )

    def test_suburban_year_from_source(self):
        records = [
            record
            for record in self.seed["records"]
            if record["make"] == "Chevrolet"
            and record["model"] == "SUBURBAN"
            and record["engine"] == "5.3 V8 DFI 16V(G)"
        ]
        self.assertTrue(records)
        self.assertTrue(
            all(
                record["year_from"] == 2017 and record["year_to"] == 2017
                for record in records
            )
        )

    def test_no_duplicates(self):
        keys = [tuple(sorted(record.items())) for record in self.seed["records"]]
        self.assertEqual(len(keys), len(set(keys)))


if __name__ == "__main__":
    unittest.main()
