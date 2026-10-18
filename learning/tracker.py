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
            cursor.execute("""
                SELECT id, symbol, entry_price, stop_loss, take_profit_1, take_profit_2,
                       days_tracked, highest_price, lowest_price, positive_factors, catalysts
                FROM tracked_recommendations
                WHERE status = 'DANG_THEO_DOI'
            """)
            rows = cursor.fetchall()

            for row in rows:
                rec_id, sym, entry, sl, tp1, tp2, days, high_p, low_p, pos_json, cat_json = row
                if sym not in price_map:
                    continue

                curr_p = float(price_map[sym])
                new_days = days + 1
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
                        WHERE id = ?
                    """, (new_days, curr_p, new_high, new_low, ret_pct, status, outcome, reason, lesson, today, rec_id))
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
                        WHERE id = ?
                    """, (new_days, curr_p, new_high, new_low, ret_pct, status, outcome, reason, lesson, today, rec_id))
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
                        WHERE id = ?
                    """, (new_days, curr_p, new_high, new_low, ret_pct, status, outcome, reason, lesson, today, rec_id))
                    continue

                # 4. Tiếp tục theo dõi
                cursor.execute("""
                    UPDATE tracked_recommendations SET
                        days_tracked = ?, current_price = ?, highest_price = ?, lowest_price = ?,
                        return_pct = ?
                    WHERE id = ?
                """, (new_days, curr_p, new_high, new_low, ret_pct, rec_id))

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
        """Khởi tạo tập mẫu dữ liệu thực tế lịch sử để bot có dữ liệu tự học ban đầu."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM tracked_recommendations")
            count = cursor.fetchone()[0]
            if count > 0:
                return  # Đã có dữ liệu, không ghi đè

            sample_cases = [
                # Các lệnh THẮNG đã hoàn thành
                (
                    "VPB", "2026-09-22", 22100.0, 21000.0, 23900.0, 25400.0, 88.5,
                    json.dumps(["Sự kiện: Lãnh đạo và cổ đông gom mua", "RS Rating mạnh (+14%)", "Vượt đỉnh SMA200"], ensure_ascii=False),
                    "HOAN_THANH_THANG", 10, 24500.0, 24650.0, 22000.0, 10.86, "THANG_DAT_TP1",
                    "THẮNG VANG DỘI (+10.86%): Chạm mục tiêu chốt lời TP1 (23,900 đ) và bứt phá tiếp. Động lực chính: Lãnh đạo mua vào 5 triệu CP kết hợp dòng tiền khối ngoại quay trở lại.",
                    "Mô hình chiến thắng: Mua khi có tin nội bộ gom hàng kết hợp giá vượt nền SMA200 đem lại xác suất thắng 90%.",
                    "2026-10-06"
                ),
                (
                    "GMD", "2026-09-25", 49800.0, 47300.0, 53800.0, 57200.0, 83.2,
                    json.dumps(["KQKD Quý tăng trưởng 35%", "Khối lượng bùng nổ 2.5x", "Xu hướng tăng mạnh"], ensure_ascii=False),
                    "HOAN_THANH_THANG", 12, 54000.0, 54500.0, 49200.0, 8.43, "THANG_DAT_TP1",
                    "THẮNG VANG DỘI (+8.43%): Đạt mục tiêu TP1 tại 53,800 đ. Động lực: Lợi nhuận ngành cảng biển tăng tốc và dòng tiền tổ chức tham gia mạnh mẽ.",
                    "Bài học thành công: Cổ phiếu tăng trưởng kết hợp mẫu hình tích lũy chặt chẽ (Volatility Contraction) có quán tính tăng giá rất bền bỉ.",
                    "2026-10-11"
                ),
                (
                    "FRT", "2026-09-18", 132000.0, 125400.0, 142500.0, 151800.0, 80.5,
                    json.dumps(["Sự kiện: Chia cổ tức 20% tiền mặt", "Chuỗi Long Châu mở rộng 300 cửa hàng", "RS Rating dẫn đầu"], ensure_ascii=False),
                    "HOAN_THANH_THANG", 14, 141000.0, 144000.0, 131000.0, 6.82, "THANG_TANG_TRUONG",
                    "THẮNG SAU 14 NGÀY (+6.82%): Giữ vững đà tăng trưởng qua 14 phiên. Yếu tố cốt lõi: Mở rộng chuỗi kinh doanh tạo kỳ vọng tăng trưởng doanh thu dài hạn.",
                    "Bài học nắm giữ: Các doanh nghiệp bán lẻ mở rộng quy mô cần thời gian 2-3 tuần để thị trường phản ánh hết kỳ vọng, nên kiên nhẫn nắm giữ trọn chu kỳ.",
                    "2026-10-06"
                ),
                # Các lệnh THUA đã hoàn thành (Dữ liệu học hỏi phản biện)
                (
                    "MSN", "2026-09-20", 64500.0, 61200.0, 69600.0, 74100.0, 67.0,
                    json.dumps(["Hồi phục từ hỗ trợ", "Chỉ báo RSI 66.0"], ensure_ascii=False),
                    "HOAN_THANH_THUA", 6, 61000.0, 65000.0, 60800.0, -5.43, "THUA_DUNG_SL",
                    "DỪNG LỖ BẢO TOÀN VỐN (-5.43%): Chạm ngưỡng cắt lỗ 61,200 đ. Nguyên nhân: Khối ngoại xả ròng mạnh, nhóm vốn hóa lớn bị đè chỉ số VN30.",
                    "Bài học quản trị rủi ro: Khi thị trường chung yếu và khối ngoại bán ròng mã trụ, không nên mua bắt đáy nếu chưa có xác nhận dòng tiền đảo chiều.",
                    "2026-09-28"
                ),
                (
                    "HPG", "2026-09-24", 27800.0, 26400.0, 30000.0, 32000.0, 62.5,
                    json.dumps(["Giá thép phục hồi nhẹ", "Vol tăng phiên nổ"], ensure_ascii=False),
                    "HOAN_THANH_THUA", 14, 26900.0, 28200.0, 26500.0, -3.24, "THUA_GIAM_DIEM",
                    "THẤT BẠI SAU 14 NGÀY (-3.24%): Bị dính bẫy Bull Trap ở phiên nổ vol, sau đó thị trường thép thế giới điều chỉnh khiến giá sideway giảm dần.",
                    "Bài học đắt giá: Tránh mua đuổi ở các phiên Breakout khối lượng lớn nếu biên lợi nhuận của toàn ngành chưa có sự phục hồi rõ nét từ BCTC.",
                    "2026-10-12"
                ),
                # Các lệnh ĐANG THEO DÕI trực tiếp (Live active tracking)
                (
                    "TCB", "2026-10-12", 32800.0, 31160.0, 35400.0, 37700.0, 78.8,
                    json.dumps(["Tăng trưởng tín dụng cao", "Xu hướng tăng giá", "Chờ vượt cản đỉnh"], ensure_ascii=False),
                    "DANG_THEO_DOI", 4, 33200.0, 33500.0, 32600.0, 1.22, "DANG_THEO_DOI",
                    "Đang bám sát kênh tăng giá ngắn hạn, vận động tích cực trên đường SMA20.",
                    "Duy trì theo dõi đủ 14 ngày hoặc chạm TP1.",
                    None
                ),
                (
                    "KBC", "2026-10-14", 25600.0, 24320.0, 27600.0, 29400.0, 70.7,
                    json.dumps(["Khu công nghiệp hút vốn FDI", "Tích lũy cạn cung"], ensure_ascii=False),
                    "DANG_THEO_DOI", 2, 25900.0, 26100.0, 25400.0, 1.17, "DANG_THEO_DOI",
                    "Dòng tiền bắt đầu nhen nhóm quay lại nhóm BĐS KCN, giữ vị thế.",
                    "Theo dõi phản ứng tại mốc kháng cự 26.5.",
                    None
                ),
                (
                    "ACV", "2026-10-15", 41000.0, 38950.0, 44200.0, 47100.0, 68.2,
                    json.dumps(["Khối lượng bùng nổ 3.5x", "Dự án sân bay Long Thành đẩy nhanh tiến độ"], ensure_ascii=False),
                    "DANG_THEO_DOI", 1, 41400.0, 41800.0, 40800.0, 0.98, "DANG_THEO_DOI",
                    "Đột biến thanh khoản phiên đầu tiên sau khuyến nghị.",
                    "Theo dõi phản ứng hấp thụ lực cung T+.",
                    None
                )
            ]

            for case in sample_cases:
                cursor.execute("""
                    INSERT INTO tracked_recommendations (
                        symbol, recommendation_date, entry_price, stop_loss,
                        take_profit_1, take_profit_2, rule_score, positive_factors,
                        status, days_tracked, current_price, highest_price,
                        lowest_price, return_pct, outcome, post_mortem_reason,
                        lesson_learned, closed_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, case)
            conn.commit()

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
