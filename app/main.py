import logging
from pathlib import Path

import psycopg
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import db
from app.config import database_url

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
logger = logging.getLogger(__name__)
app = FastAPI(title="Qual óleo para meu carro")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


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
