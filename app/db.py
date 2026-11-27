import json
from contextlib import contextmanager
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "sql" / "schema.sql"
SEED_PATH = ROOT / "data" / "seed.json"


@contextmanager
def connection(dsn):
    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        yield conn


def apply_schema(conn):
    conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))


def _sort_key(values):
    return tuple(
        (value is None, value if value is not None else "") for value in values
    )


def _unique_records(records):
    result = {}
    for record in records:
        key = (
            record["make"],
            record["model"],
            record["engine"],
            record["year_from"],
            record["year_to"],
            record["oil_brand"],
            record["oil_name"],
            record["capacity_liters"],
            record["source_pdf"],
            record["notes"],
        )
        result[key] = record
    return list(result.values())


def initialize(dsn, seed_path=SEED_PATH):
    seed = json.loads(Path(seed_path).read_text(encoding="utf-8"))
    records = _unique_records(seed["records"])
    brands = sorted({record["oil_brand"] for record in records}, key=_sort_key)
    oils = sorted(
        {
            (
                record["oil_brand"],
                record["oil_name"],
                record["sae_viscosity"],
                record["oil_type"],
            )
            for record in records
        },
        key=_sort_key,
    )
    vehicles = sorted(
        {
            (
                record["make"],
                record["model"],
                record["engine"],
                record["year_from"],
                record["year_to"],
            )
            for record in records
        },
        key=_sort_key,
    )

    with connection(dsn) as conn, conn.transaction():
        apply_schema(conn)
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO oil_brands (name) VALUES (%s)",
                [(brand,) for brand in brands],
            )
            cur.execute("SELECT id, name FROM oil_brands")
            brand_ids = {row["name"]: row["id"] for row in cur.fetchall()}

            cur.executemany(
                "INSERT INTO oils (brand_id, name, sae_viscosity, oil_type) "
                "VALUES (%s, %s, %s, %s)",
                [
                    (brand_ids[brand], name, viscosity, oil_type)
                    for brand, name, viscosity, oil_type in oils
                ],
            )
            cur.execute(
                "SELECT o.id, o.name, o.sae_viscosity, o.oil_type, b.name AS brand "
                "FROM oils o JOIN oil_brands b ON b.id = o.brand_id"
            )
            oil_ids = {
                (row["brand"], row["name"], row["sae_viscosity"], row["oil_type"]): row[
                    "id"
                ]
                for row in cur.fetchall()
            }

            cur.executemany(
                "INSERT INTO vehicles (make, model, engine, year_from, year_to) "
                "VALUES (%s, %s, %s, %s, %s)",
                vehicles,
            )
            cur.execute(
                "SELECT id, make, model, engine, year_from, year_to FROM vehicles"
            )
            vehicle_ids = {
                (
                    row["make"],
                    row["model"],
                    row["engine"],
                    row["year_from"],
                    row["year_to"],
                ): row["id"]
                for row in cur.fetchall()
            }

            candidates = sorted(
                (
                    (
                        vehicle_ids[
                            (
                                record["make"],
                                record["model"],
                                record["engine"],
                                record["year_from"],
                                record["year_to"],
                            )
                        ],
                        oil_ids[
                            (
                                record["oil_brand"],
                                record["oil_name"],
                                record["sae_viscosity"],
                                record["oil_type"],
                            )
                        ],
                        record["capacity_liters"],
                        record["source_pdf"],
                        record["notes"],
                    )
                    for record in records
                ),
                key=lambda item: (item[2] is None, _sort_key(item)),
            )
            unique_recommendations = {}
            for item in candidates:
                unique_recommendations.setdefault(tuple(item), item)
            recommendations = sorted(unique_recommendations.values(), key=_sort_key)
            cur.executemany(
                "INSERT INTO recommendations "
                "(vehicle_id, oil_id, capacity_liters, source_pdf, notes) "
                "VALUES (%s, %s, %s, %s, %s)",
                recommendations,
            )

    return {
        "brands": len(brands),
        "oils": len(oils),
        "vehicles": len(vehicles),
        "recommendations": len(recommendations),
    }


def list_makes(conn):
    rows = conn.execute("SELECT DISTINCT make FROM vehicles ORDER BY make").fetchall()
    return [row["make"] for row in rows]


def list_models(conn, make):
    rows = conn.execute(
        "SELECT DISTINCT model FROM vehicles WHERE make = %s ORDER BY model", (make,)
    ).fetchall()
    return [row["model"] for row in rows]


def _variant_label(engine, year_from, year_to):
    parts = [engine] if engine else []
    if year_from and year_to:
        parts.append(f"{year_from}-{year_to}")
    elif year_from or year_to:
        parts.append(str(year_from or year_to))
    return " ".join(parts) or "Todas as versões"


def list_variants(conn, make, model):
    rows = conn.execute(
        "SELECT DISTINCT engine, year_from, year_to FROM vehicles "
        "WHERE make = %s AND model = %s "
        "ORDER BY engine NULLS LAST, year_from NULLS LAST, year_to NULLS LAST",
        (make, model),
    ).fetchall()
    return [
        {
            "engine": row["engine"],
            "year_from": row["year_from"],
            "year_to": row["year_to"],
            "label": _variant_label(row["engine"], row["year_from"], row["year_to"]),
        }
        for row in rows
    ]


def get_recommendations(
    conn, make, model, engine=None, year_from=None, year_to=None, exact=False
):
    query = (
        "SELECT b.name AS oil_brand, o.name AS oil_name, o.sae_viscosity, o.oil_type, "
        "r.capacity_liters, r.source_pdf, r.notes "
        "FROM vehicles v "
        "JOIN recommendations r ON r.vehicle_id = v.id "
        "JOIN oils o ON o.id = r.oil_id "
        "JOIN oil_brands b ON b.id = o.brand_id "
        "WHERE v.make = %s AND v.model = %s "
    )
    params = [make, model]
    if exact:
        query += (
            "AND v.engine IS NOT DISTINCT FROM %s::text "
            "AND v.year_from IS NOT DISTINCT FROM %s::int "
            "AND v.year_to IS NOT DISTINCT FROM %s::int "
        )
        params.extend((engine, year_from, year_to))
    query += "ORDER BY b.name, o.name"
    rows = conn.execute(query, params).fetchall()
    return [
        {
            "oil_brand": row["oil_brand"],
            "oil_name": row["oil_name"],
            "sae_viscosity": row["sae_viscosity"],
            "oil_type": row["oil_type"],
            "capacity_liters": float(row["capacity_liters"])
            if row["capacity_liters"] is not None
            else None,
            "source_pdf": row["source_pdf"],
            "notes": row["notes"],
        }
        for row in rows
    ]


def healthcheck(dsn):
    with connection(dsn) as conn:
        return conn.execute("SELECT COUNT(*) AS count FROM recommendations").fetchone()[
            "count"
        ]
