import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATABASE_URL = "postgresql://whatoil:whatoil@localhost:5433/whatoil"
DEFAULT_TEST_DATABASE = "what_oil_test"


def load_env():
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.split(" #", 1)[0].strip())


def replace_database(url, name):
    parts = urlsplit(url)
    return urlunsplit(
        (parts.scheme, parts.netloc, f"/{name}", parts.query, parts.fragment)
    )


def database_url(test=False):
    load_env()
    url = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    if not test:
        return url
    return os.environ.get("TEST_DATABASE_URL") or replace_database(
        url, DEFAULT_TEST_DATABASE
    )


def admin_url(dsn):
    return replace_database(dsn, "postgres")
