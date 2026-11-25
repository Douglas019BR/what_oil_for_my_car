import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
TARGET = ROOT / "data" / "seed.json"
CORRECTIONS_PATH = ROOT / "data" / "corrections.json"

FRAGMENTS = [
    "seed_pdv.json",
    "seed_ipiranga.json",
    "seed_petronas.json",
    "seed_total.json",
    "seed_valvoline.json",
]

REQUIRED_TEXT = ("make", "model", "oil_brand", "oil_name")
OPTIONAL_TEXT = ("engine", "sae_viscosity", "oil_type", "notes")
NUMERIC = ("year_from", "year_to", "capacity_liters")


def normalize(record):
    result = dict(record)
    for key in REQUIRED_TEXT + OPTIONAL_TEXT:
        value = result.get(key)
        if isinstance(value, str):
            value = " ".join(value.split())
            result[key] = value or None
        else:
            result[key] = None
    engine_years = [
        int(year)
        for year in re.findall(r"(?:19|20)\d{2}", result.get("engine") or "")
        if 1900 <= int(year) <= 2100
    ]
    for key in ("year_from", "year_to"):
        value = result.get(key)
        if not (isinstance(value, int) and 1900 <= value <= 2100):
            value = engine_years[0] if engine_years else None
        result[key] = value
    capacity = result.get("capacity_liters")
    result["capacity_liters"] = (
        float(capacity)
        if isinstance(capacity, (int, float)) and 0 < capacity <= 50
        else None
    )
    if (
        result["year_from"]
        and result["year_to"]
        and result["year_from"] > result["year_to"]
    ):
        result["year_from"], result["year_to"] = result["year_to"], result["year_from"]
    return result


def is_valid(record):
    if any(not record.get(key) for key in REQUIRED_TEXT):
        return False
    if record["oil_name"].lower() == "verificar manual":
        return False
    if (record.get("notes") or "").lower() == "verificar manual":
        return False
    for key in NUMERIC:
        value = record.get(key)
        if value is not None and not isinstance(value, (int, float)):
            return False
    return True


def apply_corrections(records):
    corrections = json.loads(CORRECTIONS_PATH.read_text(encoding="utf-8"))["items"]
    keep = []
    for record in records:
        for item in corrections:
            if all(record.get(key) == value for key, value in item["match"].items()):
                if item["action"] == "drop":
                    break
                if item["action"] == "fix":
                    record.update(item["set"])
        else:
            keep.append(record)
    return keep


def main():
    records = []
    sources = []
    for name in FRAGMENTS:
        path = RAW_DIR / name
        fragment = json.loads(path.read_text(encoding="utf-8"))
        sources.append(fragment["source_pdf"])
        for item in fragment["records"]:
            record = normalize(item)
            record["source_pdf"] = fragment["source_pdf"]
            records.append(record)

    records = apply_corrections(records)

    unique = {}
    for record in records:
        if is_valid(record):
            key = tuple(sorted(record.items()))
            unique[key] = record

    ordered = sorted(
        unique.values(),
        key=lambda r: (
            r["make"],
            r["model"],
            r["engine"] or "",
            r["oil_brand"],
            r["oil_name"],
        ),
    )
    payload = {
        "meta": {
            "sources": sources,
            "record_count": len(ordered),
        },
        "records": ordered,
    }
    TARGET.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"Wrote {TARGET.relative_to(ROOT)} with {len(ordered)} unique records from {len(sources)} PDFs"
    )
    print(
        f"Dropped {len(records) - len(ordered)} invalid/duplicate/manual-check records"
    )


if __name__ == "__main__":
    main()
