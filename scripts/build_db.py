import argparse
import re
import sys
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import admin_url, database_url
from app.db import SEED_PATH, healthcheck, initialize


def ensure_database(dsn):
    admin = admin_url(dsn)
    name = conninfo_to_dict(dsn).get("dbname", "")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"Invalid database name in DSN: {name!r}")
    with psycopg.connect(admin, autocommit=True) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (name,)
        ).fetchone()
        if not exists:
            conn.execute(f'CREATE DATABASE "{name}"')
            print(f"Created database {name}")


def main():
    parser = argparse.ArgumentParser(
        description="Build the oil recommendation database"
    )
    parser.add_argument("--test", action="store_true", help="Use TEST_DATABASE_URL")
    parser.add_argument("--dsn", help="Override the database URL")
    parser.add_argument("--seed", default=str(SEED_PATH), help="Path to seed.json")
    parser.add_argument("--create-database", action="store_true")
    args = parser.parse_args()

    dsn = args.dsn or database_url(test=args.test)
    if args.create_database:
        ensure_database(dsn)
    stats = initialize(dsn, Path(args.seed))
    print(f"Loaded {dsn.rstrip('/').split('/')[-1]}: {stats}")
    print(f"Verified {healthcheck(dsn)} recommendation rows")


if __name__ == "__main__":
    main()
