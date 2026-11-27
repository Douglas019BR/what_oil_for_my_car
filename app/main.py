import logging
import time
from pathlib import Path

import psycopg
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import db
from app.config import database_url
from app.log_config import configure_logging
from app.rate_limit import allow

configure_logging()
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
logger = logging.getLogger(__name__)
app = FastAPI(title="Qual óleo para meu carro")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.middleware("http")
async def request_pipeline(request: Request, call_next):
    start = time.monotonic()
    if request.url.path.startswith("/api/") and not allow(
        request.client.host if request.client else "unknown"
    ):
        logger.warning("rate_limit_exceeded path=%s", request.url.path)
        return JSONResponse(status_code=429, content={"detail": "Too many requests"})
    response = await call_next(request)
    elapsed_ms = round((time.monotonic() - start) * 1000, 1)
    logger.info(
        "request method=%s path=%s status=%s duration_ms=%s",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health():
    try:
        count = db.healthcheck(database_url())
        return {"status": "ok", "recommendations": count}
    except psycopg.Error:
        logger.exception("Database health check failed")
        return JSONResponse(status_code=503, content={"status": "error"})


@app.get("/api/makes")
def makes():
    with db.connection(database_url()) as conn:
        return db.list_makes(conn)


@app.get("/api/models")
def models(make: str):
    with db.connection(database_url()) as conn:
        return db.list_models(conn, make)


@app.get("/api/variants")
def variants(make: str, model: str):
    with db.connection(database_url()) as conn:
        return db.list_variants(conn, make, model)


@app.get("/api/recommendations")
def recommendations(
    make: str,
    model: str,
    engine: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    exact: bool = False,
):
    with db.connection(database_url()) as conn:
        return db.get_recommendations(
            conn, make, model, engine, year_from, year_to, exact
        )
