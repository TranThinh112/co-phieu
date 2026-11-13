import json
import sqlite3
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd


class RecommendationTracker:
    """Theo dõi các mã cổ phiếu được đề xuất mua liên tục trong 14 ngày.
    Đánh giá kết quả Thắng/Thua, phân tích nguyên nhân và cung cấp dữ liệu cho Bot tự học."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            project_root = Path(__file__).resolve().parent.parent
            self.db_path = str(project_root / "database" / "scanner.db")
        else:
            self.db_path = str(db_path)
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tracked_recommendations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    recommendation_date TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    stop_loss REAL NOT NULL,
                    take_profit_1 REAL NOT NULL,
                    take_profit_2 REAL NOT NULL,
                    rule_score REAL NOT NULL,
                    positive_factors TEXT,
                    risk_factors TEXT,
                    catalysts TEXT,
                    status TEXT NOT NULL,
                    days_tracked INTEGER NOT NULL DEFAULT 0,
                    current_price REAL NOT NULL,
                    highest_price REAL NOT NULL,
                    lowest_price REAL NOT NULL,
                    return_pct REAL NOT NULL DEFAULT 0.0,
                    outcome TEXT NOT NULL DEFAULT 'DANG_THEO_DOI',
                    post_mortem_reason TEXT,
                    lesson_learned TEXT,
                    closed_date TEXT,
                    features_snapshot TEXT
                );
            """)
            conn.commit()

    def enroll_candidate(
        self,
        symbol: str,
        entry_price: float,
        rule_score: float,
        positive_factors: List[str],
        risk_factors: List[str] = None,
        catalysts: List[str] = None,
        date_str: Optional[str] = None,
        features_snapshot: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Thêm mã cổ phiếu vào danh sách theo dõi 14 ngày nếu chưa có lệnh mở."""
        today = date_str or datetime.datetime.now().strftime("%Y-%m-%d")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Kiểm tra xem mã này có đang trong chu kỳ theo dõi không
            cursor.execute("""
                SELECT id FROM tracked_recommendations
                WHERE symbol = ? AND status = 'DANG_THEO_DOI'
            """, (symbol.upper(),))
            if cursor.fetchone():
                return False  # Đã có trong danh sách đang theo dõi

            sl = round(entry_price * 0.95, 0)
            tp1 = round(entry_price * 1.08, 0)
            tp2 = round(entry_price * 1.15, 0)

            cursor.execute("""
                INSERT INTO tracked_recommendations (
                    symbol, recommendation_date, entry_price, stop_loss,
                    take_profit_1, take_profit_2, rule_score, positive_factors,
                    risk_factors, catalysts, status, days_tracked, current_price,
                    highest_price, lowest_price, return_pct, outcome, features_snapshot
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'DANG_THEO_DOI', 0, ?, ?, ?, 0.0, 'DANG_THEO_DOI', ?)
            """, (
                symbol.upper(),
                today,
                entry_price,
                sl,
                tp1,
                tp2,
                rule_score,
                json.dumps(positive_factors, ensure_ascii=False),
                json.dumps(risk_factors or [], ensure_ascii=False),
                json.dumps(catalysts or [], ensure_ascii=False),
                entry_price,
                entry_price,
                entry_price,
                json.dumps(features_snapshot or {}, ensure_ascii=False)
            ))
            conn.commit()
            return True

    def update_daily_tracking(self, price_map: Dict[str, float], current_date: Optional[str] = None):
        """Cập nhật giá đóng cửa hàng ngày sau phiên cho tất cả các mã đang theo dõi."""
        today = current_date or datetime.datetime.now().strftime("%Y-%m-%d")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()


            # Dam bao cot last_tracked_date co trong bang
            try:
                cursor.execute("ALTER TABLE tracked_recommendations ADD COLUMN last_tracked_date TEXT")
            except Exception:
                pass

            cursor.execute("""
                SELECT id, symbol, entry_price, stop_loss, take_profit_1, take_profit_2,
                       days_tracked, highest_price, lowest_price, positive_factors, catalysts,
                       recommendation_date, last_tracked_date
                FROM tracked_recommendations
                WHERE status = 'DANG_THEO_DOI'
            """)
            rows = cursor.fetchall()

            for row in rows:
                rec_id, sym, entry, sl, tp1, tp2, days, high_p, low_p, pos_json, cat_json, rec_date, last_t_date = row
                if sym not in price_map:
                    continue

                curr_p = float(price_map[sym])
                
                # Chi tang so ngay neu hom nay la ngay lam viec moi chua duoc chot
                import datetime
                try:
                    r_d = datetime.datetime.strptime(str(rec_date), "%Y-%m-%d").date()
                    cur_d = datetime.datetime.strptime(str(today), "%Y-%m-%d").date()
                    if cur_d > r_d:
                        trading_days = len([d for d in (r_d + datetime.timedelta(n) for n in range(1, (cur_d - r_d).days + 1)) if d.weekday() < 5])
                    else:
                        trading_days = 0
                except Exception:
                    trading_days = days + (1 if last_t_date != today else 0)
                
                new_days = max(1, trading_days) if str(today) > str(rec_date) else 1
                new_high = max(high_p, curr_p)
                new_low = min(low_p, curr_p)
                ret_pct = round(((curr_p - entry) / entry) * 100.0, 2)

                try:
                    pos_list = json.loads(pos_json) if pos_json else []
                except Exception:
                    pos_list = []
                pos_summary = "; ".join(pos_list[:2]) if pos_list else "Xu hướng kỹ thuật tích lũy tốt"

                # 1. Kiểm tra Chốt Lời TP1 (+8%)
                if new_high >= tp1 or ret_pct >= 8.0:
                    status = "HOAN_THANH_THANG"
                    outcome = "THANG_DAT_TP1"
                    reason = f"THẮNG VANG DỘI (+{ret_pct:+.2f}%): Giá bứt phá vượt kỳ vọng, chạm mục tiêu chốt lời TP1 ({tp1:,.0f} đ). Động lực thành công: {pos_summary}."
                    lesson = "Mô hình xác nhận hiệu quả cao: Cổ phiếu hội tụ đủ dòng tiền lớn và chất xúc tác doanh nghiệp duy trì quán tính tăng giá rất khỏe."
                    cursor.execute("""
                        UPDATE tracked_recommendations SET
                            days_tracked = ?, current_price = ?, highest_price = ?, lowest_price = ?,
                            return_pct = ?, status = ?, outcome = ?, post_mortem_reason = ?,
                            lesson_learned = ?, closed_date = ?
                        , last_tracked_date = ? WHERE id = ?
                    """, (new_days, curr_p, new_high, new_low, ret_pct, status, outcome, reason, lesson, today, today, rec_id))
                    continue

                # 2. Kiểm tra Cắt Lỗ SL (-5%)
                if new_low <= sl or ret_pct <= -5.0:
                    status = "HOAN_THANH_THUA"
                    outcome = "THUA_DUNG_SL"
                    reason = f"DỪNG LỖ BẢO TOÀN VỐN ({ret_pct:+.2f}%): Giá chạm ngưỡng cắt lỗ {sl:,.0f} đ (-5%). Nguyên nhân: Áp lực chốt lời ngắn hạn, gãy mốc hỗ trợ SMA20 hoặc chịu tác động xấu từ thị trường chung."
                    lesson = "Bài học kiểm soát rủi ro: Kỷ luật cắt lỗ nghiêm ngặt giúp bảo toàn 95% vốn, tránh sa lầy vào những nhịp điều chỉnh sâu hơn."
                    cursor.execute("""
                        UPDATE tracked_recommendations SET
                            days_tracked = ?, current_price = ?, highest_price = ?, lowest_price = ?,
                            return_pct = ?, status = ?, outcome = ?, post_mortem_reason = ?,
                            lesson_learned = ?, closed_date = ?
                        , last_tracked_date = ? WHERE id = ?
                    """, (new_days, curr_p, new_high, new_low, ret_pct, status, outcome, reason, lesson, today, today, rec_id))
                    continue

                # 3. Kiểm tra Hết Chu Kỳ 14 Ngày
                if new_days >= 14:
                    if ret_pct > 0:
                        status = "HOAN_THANH_THANG"
                        outcome = "THANG_TANG_TRUONG"
                        reason = f"THẮNG SAU 14 NGÀY (+{ret_pct:+.2f}%): Sau trọn vẹn 14 phiên nắm giữ, cổ phiếu duy trì tăng trưởng dương tốt. Điểm tựa: {pos_summary}."
                        lesson = "Chiến lược Swing hiệu quả: Nắm giữ trọn vẹn sóng tăng theo chu kỳ 14 ngày mang lại hiệu suất vượt trội so với giao dịch lướt sóng T+."
                    else:
                        status = "HOAN_THANH_THUA"
                        outcome = "THUA_GIAM_DIEM"
                        reason = f"KHÔNG ĐẠT KỲ VỌNG ({ret_pct:+.2f}%): Sau 14 phiên theo dõi giá suy yếu, đóng cửa thấp hơn mức khuyến nghị ban đầu."
                        lesson = "Kinh nghiệm cơ cấu: Cổ phiếu đi ngang hoặc suy yếu quá 10 phiên không có dòng tiền tham gia cần chủ động bán hạ tỷ trọng sớm."
                    cursor.execute("""
                        UPDATE tracked_recommendations SET
                            days_tracked = ?, current_price = ?, highest_price = ?, lowest_price = ?,
                            return_pct = ?, status = ?, outcome = ?, post_mortem_reason = ?,
                            lesson_learned = ?, closed_date = ?
                        , last_tracked_date = ? WHERE id = ?
                    """, (new_days, curr_p, new_high, new_low, ret_pct, status, outcome, reason, lesson, today, today, rec_id))
                    continue

                # 4. Tiếp tục theo dõi
                cursor.execute("""
                    UPDATE tracked_recommendations SET
                        days_tracked = ?, current_price = ?, highest_price = ?, lowest_price = ?,
                        return_pct = ?, last_tracked_date = ?
                    WHERE id = ?
                """, (new_days, curr_p, new_high, new_low, ret_pct, today, rec_id))

            conn.commit()

    def get_active_recommendations(self) -> pd.DataFrame:
        """Lấy danh sách các mã đang trong chu kỳ theo dõi 14 ngày."""
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query("""
                SELECT id, symbol, recommendation_date, entry_price, current_price,
                       return_pct, days_tracked, stop_loss, take_profit_1, take_profit_2,
                       rule_score, status, outcome, positive_factors
                FROM tracked_recommendations
                WHERE status = 'DANG_THEO_DOI'
                ORDER BY recommendation_date DESC, return_pct DESC
            """, conn)

    def get_completed_recommendations(self) -> pd.DataFrame:
        """Lấy lịch sử các khuyến nghị đã hoàn thành để đúc rút kinh nghiệm & tự học."""
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query("""
                SELECT id, symbol, recommendation_date, closed_date, entry_price,
                       current_price, return_pct, days_tracked, rule_score, outcome,
                       post_mortem_reason, lesson_learned, catalysts
                FROM tracked_recommendations
                WHERE status != 'DANG_THEO_DOI'
                ORDER BY closed_date DESC, id DESC
            """, conn)

    def seed_initial_knowledge(self):
        """Không nạp các mẫu lịch sử cũ tháng 9/10 để đảm bảo bot bắt đầu đánh giá hoàn toàn từ hôm nay."""
        return

    def remove_active_recommendation(self, symbol: str):
        """Xóa một mã đang theo dõi khỏi danh sách 14 ngày."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tracked_recommendations WHERE symbol = ? AND status = 'DANG_THEO_DOI'", (symbol.upper(),))
            conn.commit()

    def clear_all_active_recommendations(self):
        """Xóa toàn bộ các mã đang theo dõi 14 ngày."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tracked_recommendations WHERE status = 'DANG_THEO_DOI'")
            conn.commit()
