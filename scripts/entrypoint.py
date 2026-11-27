import os
import sys
import time
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import database_url
from app.db import initialize


def wait_for_database(dsn, timeout=60):
    deadline = time.monotonic() + timeout
    while True:
        try:
            with psycopg.connect(dsn, connect_timeout=3) as conn:
                conn.execute("SELECT 1")
            return
        except psycopg.Error:
            if time.monotonic() >= deadline:
                raise
            time.sleep(2)


def main():
    dsn = database_url()
    wait_for_database(dsn)
    initialize(dsn, reset=False)
    port = os.environ.get("PORT", "8000")
    os.execv(
        sys.executable,
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            port,
        ],
    )


if __name__ == "__main__":
    main()
