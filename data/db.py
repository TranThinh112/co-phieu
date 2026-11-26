"""PostgreSQL connection helper used by all application persistence code."""
from __future__ import annotations

import os

import psycopg


def _database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        return url.replace("postgres://", "postgresql://", 1)
    host = os.getenv("PGHOST", os.getenv("POSTGRES_HOST", "localhost"))
    port = os.getenv("PGPORT", os.getenv("POSTGRES_PORT", "5432"))
    database = os.getenv("PGDATABASE", os.getenv("POSTGRES_DB", "postgres"))
    user = os.getenv("PGUSER", os.getenv("POSTGRES_USER", "postgres"))
    password = os.getenv("PGPASSWORD", os.getenv("POSTGRES_PASSWORD", ""))
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def connect(_connection_hint=None):
    """Open the configured PostgreSQL connection."""
    return psycopg.connect(_database_url())
