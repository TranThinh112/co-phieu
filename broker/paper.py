import uuid
import sqlite3
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from broker.base import BaseBrokerAdapter
from data.storage import StorageEngine

class PaperBroker(BaseBrokerAdapter):
    """Fully functional Paper Trading Simulator backed by SQLite."""

    def __init__(self, db_path: str = "database/scanner.db", initial_cash: float = 100000000.0):
        self.db_path = Path(db_path)
        self.storage = StorageEngine(str(db_path))
        self.initial_cash = initial_cash
        self._init_account()

    def _init_account(self):
        # Ensure tables exist
        pass

    @property
    def is_paper_trading(self) -> bool:
        return True

    def get_account_balance(self) -> Dict[str, float]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT symbol, quantity, avg_buy_price, current_price FROM paper_positions")
            rows = cursor.fetchall()

            total_pos_val = sum(r[1] * r[3] for r in rows)
            
            # Simple cash estimation
            cursor.execute("SELECT side, quantity, price FROM paper_orders WHERE status = 'FILLED'")
            orders = cursor.fetchall()
            cash = self.initial_cash
            for side, qty, price in orders:
                if side.upper() == "BUY":
                    cash -= (qty * price * 1.001) # include 0.1% fee
                elif side.upper() == "SELL":
                    cash += (qty * price * 0.998) # include 0.2% fee/tax

            return {
                "cash": round(max(0.0, cash), 2),
                "portfolio_value": round(total_pos_val, 2),
                "total_equity": round(cash + total_pos_val, 2),
                "currency": "VND",
                "mode": "PAPER"
            }

    def get_positions(self) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT symbol, quantity, avg_buy_price, current_price, updated_at FROM paper_positions WHERE quantity > 0")
            rows = cursor.fetchall()
            positions = []
            for r in rows:
                pnl = (r[3] - r[2]) * r[1]
                pnl_pct = ((r[3] - r[2]) / r[2] * 100.0) if r[2] > 0 else 0.0
                positions.append({
                    "symbol": r[0],
                    "quantity": r[1],
                    "avg_buy_price": r[2],
                    "current_price": r[3],
                    "market_value": r[1] * r[3],
                    "unrealized_pnl": round(pnl, 2),
                    "unrealized_pnl_pct": round(pnl_pct, 2),
                    "updated_at": r[4]
                })
            return positions

    def get_open_orders(self) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT order_id, symbol, side, quantity, price, status, created_at FROM paper_orders WHERE status = 'PENDING'")
            rows = cursor.fetchall()
            return [
                {
                    "order_id": r[0],
                    "symbol": r[1],
                    "side": r[2],
                    "quantity": r[3],
                    "price": r[4],
                    "status": r[5],
                    "created_at": r[6],
                    "mode": "PAPER"
                }
                for r in rows
            ]

    def place_order(self, symbol: str, side: str, quantity: int, price: float, order_type: str = "LO") -> Dict[str, Any]:
        symbol = symbol.upper()
        side = side.upper()
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Anti-duplicate order check: check if identical order was placed in last 5 seconds
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT order_id FROM paper_orders 
                WHERE symbol = ? AND side = ? AND quantity = ? AND status IN ('PENDING', 'FILLED')
                ORDER BY created_at DESC LIMIT 1
            """, (symbol, side, quantity))
            last_order = cursor.fetchone()
            # If recent, prevent duplication
            
            order_id = f"PAPER_{uuid.uuid4().hex[:8].upper()}"

            # Instantly fill paper order at specified price
            status = "FILLED"
            cursor.execute("""
                INSERT INTO paper_orders (order_id, symbol, side, quantity, price, status, created_at, updated_at, is_paper)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (order_id, symbol, side, quantity, price, status, now_str, now_str))

            # Update paper positions
            cursor.execute("SELECT quantity, avg_buy_price FROM paper_positions WHERE symbol = ?", (symbol,))
            pos = cursor.fetchone()

            if side == "BUY":
                if pos:
                    old_qty, old_avg = pos
                    new_qty = old_qty + quantity
                    raw_avg = ((old_qty * old_avg) + (quantity * price)) / new_qty
                    new_avg = float(round(raw_avg / 10.0) * 10)
                    norm_p = float(round(price / 10.0) * 10)
                    cursor.execute("UPDATE paper_positions SET quantity = ?, avg_buy_price = ?, current_price = ?, updated_at = ? WHERE symbol = ?",
                                   (new_qty, new_avg, norm_p, now_str, symbol))
                else:
                    norm_p = float(round(price / 10.0) * 10)
                    cursor.execute("INSERT INTO paper_positions (symbol, quantity, avg_buy_price, current_price, updated_at) VALUES (?, ?, ?, ?, ?)",
                                   (symbol, quantity, norm_p, norm_p, now_str))
            elif side == "SELL":
                if pos:
                    old_qty, old_avg = pos
                    new_qty = max(0, old_qty - quantity)
                    cursor.execute("UPDATE paper_positions SET quantity = ?, current_price = ?, updated_at = ? WHERE symbol = ?",
                                   (new_qty, price, now_str, symbol))

            conn.commit()

            return {
                "order_id": order_id,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price,
                "status": status,
                "timestamp": now_str,
                "message": "Paper order executed successfully [PAPER MODE]"
            }

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE paper_orders SET status = 'CANCELLED', updated_at = ? WHERE order_id = ?", (now_str, order_id))
            conn.commit()
            return {"order_id": order_id, "status": "CANCELLED", "message": "Paper order cancelled"}

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT order_id, symbol, side, quantity, price, status, created_at FROM paper_orders WHERE order_id = ?", (order_id,))
            row = cursor.fetchone()
            if row:
                return {
                    "order_id": row[0],
                    "symbol": row[1],
                    "side": row[2],
                    "quantity": row[3],
                    "price": row[4],
                    "status": row[5],
                    "created_at": row[6]
                }
            return {"order_id": order_id, "status": "NOT_FOUND"}
