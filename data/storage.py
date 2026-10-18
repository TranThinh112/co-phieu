import sqlite3
import json
import datetime
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional

class StorageEngine:
    """Manages SQLite persistent storage for scan results, watchlists, models and paper orders."""

    def __init__(self, db_path: str = "database/scanner.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    def _init_tables(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Scan runs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scan_runs (
                    run_id TEXT PRIMARY KEY,
                    timestamp TEXT,
                    symbols_count INTEGER,
                    provider_type TEXT,
                    is_synthetic INTEGER
                )
            """)

            # Scan results table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scan_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT,
                    symbol TEXT,
                    exchange TEXT,
                    close_price REAL,
                    price_change REAL,
                    avg_volume_20d REAL,
                    avg_value_20d REAL,
                    trend TEXT,
                    rs_index REAL,
                    rsi REAL,
                    volume_ratio REAL,
                    breakout_status TEXT,
                    rule_score REAL,
                    category TEXT,
                    ai_prob_5d REAL,
                    ai_prob_10d REAL,
                    ai_prob_20d REAL,
                    risk_level TEXT,
                    positive_factors TEXT,
                    risk_factors TEXT,
                    news_sentiment TEXT,
                    news_catalysts TEXT,
                    news_score_adj REAL,
                    data_timestamp TEXT,
                    FOREIGN KEY(run_id) REFERENCES scan_runs(run_id)
                )
            """)

            # Watchlists table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS watchlists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    watchlist_name TEXT,
                    symbol TEXT,
                    added_at TEXT,
                    notes TEXT,
                    UNIQUE(watchlist_name, symbol)
                )
            """)

            # Model metadata registry table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS model_registry (
                    model_id TEXT PRIMARY KEY,
                    horizon INTEGER,
                    trained_at TEXT,
                    train_samples INTEGER,
                    features TEXT,
                    metrics_json TEXT,
                    filepath TEXT
                )
            """)

            # Paper Trading tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paper_orders (
                    order_id TEXT PRIMARY KEY,
                    symbol TEXT,
                    side TEXT,
                    quantity INTEGER,
                    price REAL,
                    status TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    is_paper INTEGER DEFAULT 1
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paper_positions (
                    symbol TEXT PRIMARY KEY,
                    quantity INTEGER,
                    avg_buy_price REAL,
                    current_price REAL,
                    updated_at TEXT
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS news_cache (
                    article_id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT,
                    source TEXT NOT NULL,
                    url TEXT NOT NULL,
                    published_at TEXT,
                    fetched_at TEXT NOT NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_news_cache_symbol ON news_cache(symbol)")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trade_plans (
                    plan_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    entry_price REAL,
                    stop_loss REAL,
                    take_profit_1 REAL,
                    take_profit_2 REAL,
                    quantity INTEGER,
                    position_value REAL,
                    risk_amount REAL,
                    holding_period_sessions INTEGER,
                    execution_mode TEXT NOT NULL,
                    reason TEXT,
                    invalidates_if TEXT,
                    scan_run_id TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trade_plans_symbol ON trade_plans(symbol)")
            conn.commit()

    def save_scan_run(self, run_id: str, results_df: pd.DataFrame, provider_type: str = "public_api", is_synthetic: bool = False):
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO scan_runs (run_id, timestamp, symbols_count, provider_type, is_synthetic)
                VALUES (?, ?, ?, ?, ?)
            """, (run_id, now_str, len(results_df), provider_type, 1 if is_synthetic else 0))

            for _, row in results_df.iterrows():
                cursor.execute("""
                    INSERT INTO scan_results (
                        run_id, symbol, exchange, close_price, price_change,
                        avg_volume_20d, avg_value_20d, trend, rs_index, rsi,
                        volume_ratio, breakout_status, rule_score, category,
                        ai_prob_5d, ai_prob_10d, ai_prob_20d, risk_level,
                        positive_factors, risk_factors, news_sentiment, news_catalysts, news_score_adj, data_timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    run_id,
                    str(row.get('symbol', '')),
                    str(row.get('exchange', 'HOSE')),
                    float(row.get('close_price', 0.0)),
                    float(row.get('price_change', 0.0)),
                    float(row.get('avg_volume_20d', 0.0)),
                    float(row.get('avg_value_20d', 0.0)),
                    str(row.get('trend', '')),
                    float(row.get('rs_index', 0.0)),
                    float(row.get('rsi', 0.0)),
                    float(row.get('volume_ratio', 0.0)),
                    str(row.get('breakout_status', '')),
                    float(row.get('rule_score', 0.0)),
                    str(row.get('category', 'Watchlist')),
                    float(row.get('ai_prob_5d')) if pd.notna(row.get('ai_prob_5d')) and row.get('ai_prob_5d') is not None else None,
                    float(row.get('ai_prob_10d')) if pd.notna(row.get('ai_prob_10d')) and row.get('ai_prob_10d') is not None else None,
                    float(row.get('ai_prob_20d')) if pd.notna(row.get('ai_prob_20d')) and row.get('ai_prob_20d') is not None else None,
                    str(row.get('risk_level', 'Medium')),
                    json.dumps(row.get('positive_factors', []), ensure_ascii=False) if isinstance(row.get('positive_factors'), list) else str(row.get('positive_factors', '')),
                    json.dumps(row.get('risk_factors', []), ensure_ascii=False) if isinstance(row.get('risk_factors'), list) else str(row.get('risk_factors', '')),
                    str(row.get('news_sentiment', 'NEUTRAL')),
                    json.dumps(row.get('news_catalysts', []), ensure_ascii=False) if isinstance(row.get('news_catalysts'), list) else str(row.get('news_catalysts', '')),
                    float(row.get('news_score_adj', 0.0)),
                    str(row.get('data_timestamp', now_str))
                ))
            conn.commit()

    def get_latest_scan_results(self) -> pd.DataFrame:
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT * FROM scan_results
                WHERE run_id = (SELECT run_id FROM scan_runs ORDER BY is_synthetic ASC, timestamp DESC LIMIT 1)
            """
            df = pd.read_sql_query(query, conn)
            return df

    def get_scan_history(self, symbol: Optional[str] = None) -> pd.DataFrame:
        with sqlite3.connect(self.db_path) as conn:
            if symbol:
                query = "SELECT r.*, s.timestamp FROM scan_results r JOIN scan_runs s ON r.run_id = s.run_id WHERE r.symbol = ? ORDER BY s.timestamp DESC"
                return pd.read_sql_query(query, conn, params=(symbol.upper(),))
            else:
                query = "SELECT r.*, s.timestamp FROM scan_results r JOIN scan_runs s ON r.run_id = s.run_id ORDER BY s.timestamp DESC LIMIT 500"
                return pd.read_sql_query(query, conn)

    def add_to_watchlist(self, watchlist_name: str, symbol: str, notes: str = ""):
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO watchlists (watchlist_name, symbol, added_at, notes)
                VALUES (?, ?, ?, ?)
            """, (watchlist_name, symbol.upper(), now_str, notes))
            conn.commit()

    def get_watchlist(self, watchlist_name: str = "Default") -> List[str]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT symbol FROM watchlists WHERE watchlist_name = ?", (watchlist_name,))
            rows = cursor.fetchall()
            return [r[0] for r in rows]

    def remove_from_watchlist(self, watchlist_name: str, symbol: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM watchlists WHERE watchlist_name = ? AND symbol = ?", (watchlist_name, symbol.upper()))
            conn.commit()
    def get_cached_news(self, symbol: str, cache_minutes: int = 30) -> List[Dict[str, Any]]:
        cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=cache_minutes)).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT article_id, symbol, title, summary, source, url, published_at, fetched_at
                FROM news_cache WHERE symbol = ? AND fetched_at >= ? ORDER BY published_at DESC
            """, (symbol.upper(), cutoff))
            columns = ["article_id", "symbol", "title", "summary", "source", "url", "published_at", "fetched_at"]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def replace_cached_news(self, symbol: str, articles: List[Dict[str, Any]]):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM news_cache WHERE symbol = ?", (symbol.upper(),))
            cursor.executemany("""
                INSERT OR REPLACE INTO news_cache
                (article_id, symbol, title, summary, source, url, published_at, fetched_at)
                VALUES (:article_id, :symbol, :title, :summary, :source, :url, :published_at, :fetched_at)
            """, articles)
            conn.commit()
    def save_trade_plans(self, scan_run_id: str, plans: List[Dict[str, Any]]):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for plan in plans:
                cursor.execute("""
                    INSERT OR REPLACE INTO trade_plans
                    (plan_id, created_at, symbol, decision, entry_price, stop_loss, take_profit_1, take_profit_2,
                     quantity, position_value, risk_amount, holding_period_sessions, execution_mode, reason,
                     invalidates_if, scan_run_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    plan["plan_id"], now, plan["symbol"], plan["decision"], plan["entry_price"], plan["stop_loss"],
                    plan.get("take_profit_1"), plan.get("take_profit_2"), plan["quantity"], plan["position_value"],
                    plan["risk_amount"], plan["holding_period_sessions"], plan["execution_mode"], plan["reason"],
                    plan["invalidates_if"], scan_run_id,
                ))
            conn.commit()

    def get_latest_trade_plans(self) -> pd.DataFrame:
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT * FROM trade_plans 
                WHERE scan_run_id = (SELECT run_id FROM scan_runs ORDER BY is_synthetic ASC, timestamp DESC LIMIT 1)
                ORDER BY symbol
            """
            df = pd.read_sql_query(query, conn)
            if df.empty:
                df = pd.read_sql_query("SELECT * FROM trade_plans ORDER BY created_at DESC, symbol LIMIT 30", conn)
            return df
    def get_latest_run_summary(self) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT run_id, timestamp, symbols_count, provider_type, is_synthetic FROM scan_runs ORDER BY is_synthetic ASC, timestamp DESC LIMIT 1")
            row = cursor.fetchone()
            if not row:
                return {}
            run_id, timestamp, symbols_count, provider_type, is_synthetic = row
            cursor.execute("SELECT trend, close_price, price_change FROM scan_results WHERE run_id = ?", (run_id,))
            results = cursor.fetchall()
            uptrends = sum(1 for r in results if "Tăng" in str(r[0]) or "Uptrend" in str(r[0]))
            total = len(results) or 1
            pct_uptrend = round((uptrends / total) * 100.0, 1)
            regime = "Bullish (Xu hướng Tăng mạnh)" if pct_uptrend >= 60 else ("Bearish (Xu hướng Giảm giá)" if pct_uptrend <= 40 else "Sideways (Đi ngang)")
            return {
                "run_id": run_id,
                "timestamp": timestamp,
                "symbols_count": len(results),
                "provider_type": provider_type,
                "is_synthetic": bool(is_synthetic),
                "pct_above_sma20": pct_uptrend,
                "pct_above_sma50": pct_uptrend,
                "regime": regime
            }


