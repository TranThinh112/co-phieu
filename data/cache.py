import sqlite3
import datetime
import json
import pandas as pd
from pathlib import Path
from typing import Optional

class DataCache:
    """Manages SQLite cache for downloaded daily stock price bars."""

    def __init__(self, db_path: str = "database/cache.db", ttl_hours: float = 12.0):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.ttl_hours = ttl_hours
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_cache (
                    symbol TEXT PRIMARY KEY,
                    updated_at TEXT,
                    data_json TEXT
                )
            """)
            conn.commit()

    def get(self, symbol: str) -> Optional[pd.DataFrame]:
        symbol = symbol.upper()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT updated_at, data_json FROM price_cache WHERE symbol = ?", (symbol,))
            row = cursor.fetchone()
            if not row:
                return None

            updated_at_str, data_json = row
            try:
                updated_at = datetime.datetime.strptime(updated_at_str, "%Y-%m-%d %H:%M:%S")
                if (datetime.datetime.now() - updated_at).total_seconds() > self.ttl_hours * 3600:
                    return None

                data = json.loads(data_json)
                df = pd.DataFrame(data)
                return df
            except Exception as e:
                print(f"[DataCache] Cache read error for {symbol}: {e}")
                return None

    def set(self, symbol: str, df: pd.DataFrame):
        if df is None or df.empty:
            return
        symbol = symbol.upper()
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data_json = df.to_json(orient="records")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO price_cache (symbol, updated_at, data_json)
                VALUES (?, ?, ?)
            """, (symbol, now_str, data_json))
            conn.commit()

    def clear(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM price_cache")
            conn.commit()
