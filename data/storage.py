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
                CREATE TABLE IF NOT EXISTS user_positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL UNIQUE,
                    quantity INTEGER NOT NULL,
                    avg_buy_price REAL NOT NULL,
                    note TEXT,
                    created_at TEXT,
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

    def _ensure_user_positions_table(self, conn):
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL UNIQUE,
                quantity INTEGER NOT NULL,
                avg_buy_price REAL NOT NULL,
                note TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_trade_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                old_avg_price REAL,
                new_avg_price REAL,
                realized_pnl REAL DEFAULT 0.0,
                pnl_pct REAL DEFAULT 0.0,
                trade_time TEXT NOT NULL,
                note TEXT
            )
        """)
        conn.commit()

    def get_user_positions(self) -> list:
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            self._ensure_user_positions_table(conn)
            cursor = conn.cursor()
            cursor.execute("SELECT id, symbol, quantity, avg_buy_price, note, created_at, updated_at FROM user_positions ORDER BY updated_at DESC")
            rows = cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "symbol": r[1],
                    "quantity": r[2],
                    "avg_buy_price": r[3],
                    "note": r[4] or "",
                    "created_at": r[5],
                    "updated_at": r[6]
                }
                for r in rows
            ]

    def execute_user_buy(self, symbol: str, buy_qty: int, buy_price: float = None, fee_rate: float = 0.0015, note: str = "") -> dict:
        """Mua them vao: Tang so luong va tinh lai gia mua trung binh (DCA) chuan 100% gom ca phi giao dich/thue hoac thi gia tu dong."""
        import sqlite3, datetime
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sym_clean = str(symbol).strip().upper()

        # Neu khong truyen gia mua cu the hoac truyen 0, tu dong lay thi gia khop lenh moi nhat
        effective_buy_price = float(buy_price) if (buy_price is not None and float(buy_price) > 0) else 0.0
        if effective_buy_price <= 0:
            try:
                from data.providers.vnstock_provider import VnstockProvider
                df_hist = VnstockProvider().get_historical_prices(sym_clean)
                if df_hist is not None and not df_hist.empty and "close" in df_hist.columns:
                    effective_buy_price = float(df_hist["close"].iloc[-1])
            except Exception:
                pass

        with sqlite3.connect(self.db_path) as conn:
            self._ensure_user_positions_table(conn)
            cur = conn.cursor()
            cur.execute("SELECT quantity, avg_buy_price FROM user_positions WHERE symbol = ?", (sym_clean,))
            row = cur.fetchone()

            buy_cost_with_fee = int(buy_qty) * effective_buy_price * (1.0 + float(fee_rate))

            if row:
                old_qty, old_price = int(row[0]), float(row[1])
                new_qty = old_qty + int(buy_qty)
                old_total_cost = old_qty * old_price
                new_avg_price = round((old_total_cost + buy_cost_with_fee) / new_qty, 1) if new_qty > 0 else effective_buy_price
                cur.execute("""
                    UPDATE user_positions SET quantity = ?, avg_buy_price = ?, note = ?, updated_at = ? WHERE symbol = ?
                """, (new_qty, new_avg_price, note, now_str, sym_clean))
            else:
                old_qty, old_price = 0, 0.0
                new_qty = int(buy_qty)
                new_avg_price = round(buy_cost_with_fee / new_qty, 1) if new_qty > 0 else effective_buy_price
                cur.execute("""
                    INSERT INTO user_positions (symbol, quantity, avg_buy_price, note, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (sym_clean, new_qty, new_avg_price, note, now_str, now_str))

            cur.execute("""
                INSERT INTO user_trade_history (symbol, side, quantity, price, old_avg_price, new_avg_price, realized_pnl, pnl_pct, trade_time, note)
                VALUES (?, 'BUY', ?, ?, ?, ?, 0.0, 0.0, ?, ?)
            """, (sym_clean, int(buy_qty), effective_buy_price, old_price, new_avg_price, now_str, note))
            conn.commit()
            return {
                "symbol": sym_clean,
                "old_qty": old_qty,
                "old_avg_price": old_price,
                "added_qty": int(buy_qty),
                "buy_price": effective_buy_price,
                "fee_rate": float(fee_rate),
                "new_qty": new_qty,
                "new_avg_price": new_avg_price
            }

    def execute_user_sell(self, symbol: str, sell_qty: int, sell_price: float, note: str = "") -> dict:
        """Ban ra mot phan hoac toan bo: Giu nguyen gia TB cua so CP con lai va chot loi/lo thuc te."""
        import sqlite3, datetime
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sym_clean = str(symbol).strip().upper()
        with sqlite3.connect(self.db_path) as conn:
            self._ensure_user_positions_table(conn)
            cur = conn.cursor()
            cur.execute("SELECT quantity, avg_buy_price FROM user_positions WHERE symbol = ?", (sym_clean,))
            row = cur.fetchone()
            if not row:
                return {"success": False, "error": f"Khong tim thay ma {sym_clean} trong danh muc"}


            curr_qty, curr_price = int(row[0]), float(row[1])
            qty_to_sell = min(int(sell_qty), curr_qty)
            rem_qty = curr_qty - qty_to_sell

            realized_pnl = (float(sell_price) - curr_price) * qty_to_sell
            pnl_pct = ((float(sell_price) - curr_price) / curr_price * 100.0) if curr_price > 0 else 0.0

            if rem_qty <= 0:
                cur.execute("DELETE FROM user_positions WHERE symbol = ?", (sym_clean,))
            else:
                cur.execute("UPDATE user_positions SET quantity = ?, updated_at = ? WHERE symbol = ?", (rem_qty, now_str, sym_clean))

            cur.execute("""
                INSERT INTO user_trade_history (symbol, side, quantity, price, old_avg_price, new_avg_price, realized_pnl, pnl_pct, trade_time, note)
                VALUES (?, 'SELL', ?, ?, ?, ?, ?, ?, ?, ?)
            """, (sym_clean, qty_to_sell, float(sell_price), curr_price, curr_price if rem_qty > 0 else 0.0, realized_pnl, pnl_pct, now_str, note))
            conn.commit()

            return {
                "success": True,
                "symbol": sym_clean,
                "sold_qty": qty_to_sell,
                "sell_price": float(sell_price),
                "cost_price": curr_price,
                "remaining_qty": rem_qty,
                "realized_pnl": realized_pnl,
                "pnl_pct": pnl_pct
            }

    def get_user_trade_history(self, limit: int = 30) -> list:
        """Lay lich su cac lenh mua them va chot loi / cat lo da thuc hien."""
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            self._ensure_user_positions_table(conn)
            cur = conn.cursor()
            cur.execute("""
                SELECT id, symbol, side, quantity, price, old_avg_price, new_avg_price, realized_pnl, pnl_pct, trade_time, note
                FROM user_trade_history
                ORDER BY trade_time DESC, id DESC
                LIMIT ?
            """, (limit,))
            cols = ["id", "symbol", "side", "quantity", "price", "old_avg_price", "new_avg_price", "realized_pnl", "pnl_pct", "trade_time", "note"]
            return [dict(zip(cols, r)) for r in cur.fetchall()]

    def save_user_position(self, symbol: str, quantity: int, avg_buy_price: float, note: str = ""):
        """Luu vi the: Neu da co ma nay trong danh muc thi TU DONG tinh DCA cong don, khong bi de mat data cu."""
        return self.execute_user_buy(symbol, quantity, avg_buy_price, fee_rate=0.0, note=note or "Them vao danh muc")

    def update_user_position_direct(self, symbol: str, quantity: int, avg_buy_price: float, note: str = ""):
        """Cap nhat truc tiep gia von va so luong khop 100% theo app chung khoan cua nguoi dung."""
        import sqlite3, datetime
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sym_clean = str(symbol).strip().upper()
        with sqlite3.connect(self.db_path) as conn:
            self._ensure_user_positions_table(conn)
            cur = conn.cursor()
            cur.execute("""
                UPDATE user_positions
                SET quantity = ?, avg_buy_price = ?, note = ?, updated_at = ?
                WHERE symbol = ?
            """, (int(quantity), float(avg_buy_price), note, now_str, sym_clean))
            
            # Ghi log dieu chinh
            cur.execute("""
                INSERT INTO user_trade_history (symbol, side, quantity, price, old_avg_price, new_avg_price, realized_pnl, pnl_pct, trade_time, note)
                VALUES (?, "ADJUST", ?, ?, ?, ?, 0.0, 0.0, ?, ?)
            """, (sym_clean, int(quantity), float(avg_buy_price), float(avg_buy_price), float(avg_buy_price), now_str, note or "Dieu chinh khop app"))
            conn.commit()

    def delete_user_position(self, symbol: str):
        import sqlite3
        sym_clean = str(symbol).strip().upper()
        with sqlite3.connect(self.db_path) as conn:
            self._ensure_user_positions_table(conn)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_positions WHERE symbol = ?", (sym_clean,))
            conn.commit()
    def export_full_snapshot(self) -> dict:
        """XUat toan bo du lieu danh muc, theo doi 14 ngay va dot quet gan nhat."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            def fetch_tbl(name, limit=None):
                try:
                    q = f"SELECT * FROM {name}"
                    if limit:
                        q += f" LIMIT {limit}"
                    cur.execute(q)
                    return [dict(r) for r in cur.fetchall()]
                except Exception:
                    return []
            return {
                "user_positions": fetch_tbl("user_positions"),
                "tracked_recommendations": fetch_tbl("tracked_recommendations"),
                "scan_runs": fetch_tbl("scan_runs", 20),
                "scan_results": fetch_tbl("scan_results", 50),
                "trade_plans": fetch_tbl("trade_plans", 50)
            }

    def import_full_snapshot(self, snapshot_data: dict) -> bool:
        """Nap du lieu snapshot (nhaping tul local len Cloud hoac nguoc lai)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                if "scan_runs" in snapshot_data:
                    for r in snapshot_data["scan_runs"]:
                        cur.execute("INSERT OR IGNORE INTO scan_runs (run_id, timestamp, symbols_count, provider_type, is_synthetic) VALUES(?, ?, ?, ?, ?)", (r.get("run_id"), r.get("timestamp"), r.get("symbols_count"), r.get("provider_type"), r.get("is_synthetic", 0)))
                if "user_positions" in snapshot_data:
                    sql_u = "INSERT OR REPLACE INTO user_positions (symbol, quantity, avg_buy_price, note, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)"
                    for p in snapshot_data["user_positions"]:
                        cur.execute(sql_u, (p.get("symbol"), p.get("quantity", 100), p.get("avg_buy_price", 0.0), p.get("note", ""), p.get("created_at", ""), p.get("updated_at", "")))
                if "tracked_recommendations" in snapshot_data:
                    t_cols = [
                        "symbol", "recommendation_date", "entry_price", "stop_loss", "take_profit_1", "take_profit_2",
                        "rule_score", "positive_factors", "risk_factors", "catalysts", "status", "days_tracked",
                        "current_price", "highest_price", "lowest_price", "return_pct", "outcome", "post_mortem_reason",
                        "lesson_learned", "closed_date", "features_snapshot"
                    ]
                    sql_t = "INSERT OR IGNORE INTO tracked_recommendations (" + ", ".join(t_cols) + ") VALUES (" + ", ".join(["?"] * len(t_cols)) + ")"
                    for tr in snapshot_data["tracked_recommendations"]:
                        cur.execute(sql_t, tuple(tr.get(c) for c in t_cols))
                conn.commit()
            return True
        except Exception as e:
            print(f"Import snapshot error: {e}")
            return False

    def clear_all_user_positions(self):
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            self._ensure_user_positions_table(conn)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_positions")
            conn.commit()

    def seed_initial_market_data_if_empty(self):
        """Tu dong nap du lieu phan tich thi truong ban dau neu database moi khoi tao tren Cloud (Railway)."""
        import json
        import sqlite3
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM scan_results")
            count = cursor.fetchone()[0]
            if count > 0:
                return

            seed_path = Path(__file__).resolve().parent.parent / "database" / "initial_market_seed.json"
            if not seed_path.exists():
                return

            try:
                with open(seed_path, "r", encoding="utf-8") as sf:
                    seed_data = json.load(sf)

                run_item = seed_data.get("scan_run", {})
                if run_item:
                    cursor.execute("""
                        INSERT OR IGNORE INTO scan_runs (run_id, timestamp, symbols_count, provider_type, is_synthetic)
                        VALUES (?, ?, ?, ?, ?)
                    """, (run_item.get("run_id"), run_item.get("timestamp"), run_item.get("symbols_count"), run_item.get("provider_type"), run_item.get("is_synthetic", 0)))

                results = seed_data.get("scan_results", [])
                for r in results:
                    cursor.execute("""
                        INSERT OR IGNORE INTO scan_results (
                            run_id, symbol, exchange, close_price, price_change, avg_volume_20d, avg_value_20d,
                            trend, rs_index, rsi, volume_ratio, breakout_status, rule_score, category,
                            ai_prob_5d, ai_prob_10d, ai_prob_20d, risk_level, positive_factors, risk_factors,
                            news_sentiment, news_catalysts, news_score_adj, data_timestamp
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        r.get("run_id"), r.get("symbol"), r.get("exchange"), r.get("close_price"), r.get("price_change"),
                        r.get("avg_volume_20d"), r.get("avg_value_20d"), r.get("trend"), r.get("rs_index"), r.get("rsi"),
                        r.get("volume_ratio"), r.get("breakout_status"), r.get("rule_score"), r.get("category"),
                        r.get("ai_prob_5d"), r.get("ai_prob_10d"), r.get("ai_prob_20d"), r.get("risk_level"),
                        r.get("positive_factors"), r.get("risk_factors"), r.get("news_sentiment"), r.get("news_catalysts"),
                        r.get("news_score_adj"), r.get("data_timestamp")
                    ))

                plans = seed_data.get("trade_plans", [])
                for p in plans:
                    cursor.execute("""
                        INSERT OR IGNORE INTO trade_plans (
                            plan_id, created_at, symbol, decision, entry_price, stop_loss, take_profit_1, take_profit_2,
                            quantity, position_value, risk_amount, holding_period_sessions, execution_mode, reason,
                            invalidates_if, scan_run_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        p.get("plan_id"), p.get("created_at"), p.get("symbol"), p.get("decision"), p.get("entry_price"),
                        p.get("stop_loss"), p.get("take_profit_1"), p.get("take_profit_2"), p.get("quantity"),
                        p.get("position_value"), p.get("risk_amount"), p.get("holding_period_sessions"),
                        p.get("execution_mode"), p.get("reason"), p.get("invalidates_if"), p.get("scan_run_id")
                    ))

                # Nap user_positions tu seed_data neu chua co
                cursor.execute("SELECT COUNT(*) FROM user_positions")
                if cursor.fetchone()[0] == 0:
                    for pos in seed_data.get("user_positions", []):
                        cursor.execute(
                            "INSERT OR REPLACE INTO user_positions (symbol, quantity, avg_buy_price, note, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                            (pos.get("symbol"), pos.get("quantity", 100), pos.get("avg_buy_price", 0.0), pos.get("note", ""), pos.get("created_at", ""), pos.get("updated_at", ""))
                        )

                # Nap tracked_recommendations tu seed_data neu chua co
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tracked_recommendations'")
                if cursor.fetchone():
                    cursor.execute("SELECT COUNT(*) FROM tracked_recommendations")
                    if cursor.fetchone()[0] == 0:
                        t_cols = [
                            "symbol", "recommendation_date", "entry_price", "stop_loss", "take_profit_1", "take_profit_2",
                            "rule_score", "positive_factors", "risk_factors", "catalysts", "status", "days_tracked",
                            "current_price", "highest_price", "lowest_price", "return_pct", "outcome", "post_mortem_reason",
                            "lesson_learned", "closed_date", "features_snapshot"
                        ]
                        sql_t = "INSERT OR IGNORE INTO tracked_recommendations (" + ", ".join(t_cols) + ") VALUES (" + ", ".join(["?"] * len(t_cols)) + ")"
                        for tr in seed_data.get("tracked_recommendations", []):
                            cursor.execute(sql_t, tuple(tr.get(c) for c in t_cols))
                conn.commit()
            except Exception as e:
                pass

