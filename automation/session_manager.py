import datetime
from typing import Dict, Any, Tuple, Optional


class MarketSessionManager:
    """Quan ly khung gio giao dich chuan cua Thi Truong Chung Khoan Viet Nam (HOSE, HNX, UPCoM).
    
    Quy dinh lich giao dich:
    - Thu 2 den Thu 6 (nghi Thu 7 va Chu Nhat).
    - Khung gio sang: 09:00 - 11:30 (Khop lenh lien tuc & ATO/Khop lenh dinh ky).
    - Khung gio chieu: 13:00 - 15:00 (Khop lenh lien tuc & ATC).
    - Sau gio dong cua: 15:00 - 16:30 (Danh gia tong ket phien, tong hop tin tuc, tinh toan de xuat moi).
    - Ngoai gio (Dem & Cuoi tuan): Khong goi API gia/nen lien tuc, chi dung du lieu cache de tiet kiem tai nguyen.
    """

    TIMEZONE_OFFSET_HOURS = 7  # Gio Viet Nam GMT+7

    @classmethod
    def get_vietnam_now(cls) -> datetime.datetime:
        """Lay thoi gian hien tai theo gio Viet Nam (GMT+7)."""
        utc_now = datetime.datetime.now(datetime.timezone.utc)
        vn_tz = datetime.timezone(datetime.timedelta(hours=cls.TIMEZONE_OFFSET_HOURS))
        return utc_now.astimezone(vn_tz)

    @classmethod
    def get_session_info(cls, dt: Optional[datetime.datetime] = None) -> Dict[str, Any]:
        """Xac dinh trang thai phien giao dich hien tai."""
        if dt is None:
            dt = cls.get_vietnam_now()

        weekday = dt.weekday()  # 0: Mon, ..., 4: Fri, 5: Sat, 6: Sun
        is_weekday = weekday < 5
        curr_time = dt.time()

        t_0900 = datetime.time(9, 0)
        t_1130 = datetime.time(11, 30)
        t_1300 = datetime.time(13, 0)
        t_1500 = datetime.time(15, 0)
        t_1630 = datetime.time(16, 30)

        # 1. Cuoi tuan
        if not is_weekday:
            return {
                "is_trading_hour": False,
                "is_post_market": False,
                "should_poll_api": False,
                "session_name": "Nghỉ Cuối Tuần (Thị trường đóng cửa)",
                "session_code": "WEEKEND",
                "recommended_action": "Sử dụng dữ liệu chốt phiên gần nhất; không gọi API liên tục.",
                "badge_color": "#94a3b8",
                "badge_label": "⚪ THỊ TRƯỜNG ĐÓNG CỬA (CUỐI TUẦN)"
            }

        # 2. Phien sang: 09:00 - 11:30
        if t_0900 <= curr_time <= t_1130:
            return {
                "is_trading_hour": True,
                "is_post_market": False,
                "should_poll_api": True,
                "session_name": "Phiên Giao Dịch Sáng (09:00 - 11:30)",
                "session_code": "MORNING_SESSION",
                "recommended_action": "Đang trong giờ giao dịch trực tiếp. Cập nhật giá & xung lực cung cầu.",
                "badge_color": "#10b981",
                "badge_label": "🟢 ĐANG TRONG PHIÊN SÁNG (ACTIVE)"
            }

        # 3. Nghi trua: 11:30 - 13:00
        if t_1130 < curr_time < t_1300:
            return {
                "is_trading_hour": False,
                "is_post_market": False,
                "should_poll_api": False,
                "session_name": "Nghỉ Trưa (11:30 - 13:00)",
                "session_code": "LUNCH_BREAK",
                "recommended_action": "Tạm dừng gọi API giá nến; bảo toàn hạn mức gọi API.",
                "badge_color": "#f59e0b",
                "badge_label": "🟡 NGHỈ TRƯA (TẠM DỪNG GỌI API)"
            }

        # 4. Phien chieu: 13:00 - 15:00
        if t_1300 <= curr_time <= t_1500:
            return {
                "is_trading_hour": True,
                "is_post_market": False,
                "should_poll_api": True,
                "session_name": "Phiên Giao Dịch Chiều & ATC (13:00 - 15:00)",
                "session_code": "AFTERNOON_SESSION",
                "recommended_action": "Đang trong giờ giao dịch trực tiếp. Cập nhật biến động ATC.",
                "badge_color": "#10b981",
                "badge_label": "🟢 ĐANG TRONG PHIÊN CHIỀU (ACTIVE)"
            }

        # 5. Khung gio tong ket & danh gia sau phien: 15:00 - 16:30
        if t_1500 < curr_time <= t_1630:
            return {
                "is_trading_hour": False,
                "is_post_market": True,
                "should_poll_api": False,
                "session_name": "Tổng Kết & Đánh Giá Sau Phiên (15:00 - 16:30)",
                "session_code": "POST_MARKET_REVIEW",
                "recommended_action": "Đã kết thúc phiên. Đang chạy tổng hợp tin tức và cập nhật đề xuất cho phiên kế tiếp.",
                "badge_color": "#3b82f6",
                "badge_label": "🔵 TỔNG KẾT & ĐÁNH GIÁ PHIÊN HÔM NAY"
            }

        # 6. Ngoai gio (Truoc 09:00 hoac Sau 16:30)
        return {
            "is_trading_hour": False,
            "is_post_market": False,
            "should_poll_api": False,
            "session_name": "Ngoài Giờ Giao Dịch (Nghỉ qua đêm)",
            "session_code": "OFF_HOURS",
            "recommended_action": "Thị trường nghỉ. Sử dụng dữ liệu phân tích đã lưu; ngừng quét API định kỳ.",
            "badge_color": "#64748b",
            "badge_label": "🌙 NGOÀI GIỜ GIAO DỊCH (BẢO TOÀN API)"
        }

    @classmethod
    def should_allow_live_scan(cls, force: bool = False) -> Tuple[bool, str]:
        """Kiem tra xem co nen kich hoat quet du lieu truc tiep hay khong de han che goi API vo ich."""
        if force:
            return True, "Chế độ quét cưỡng bức theo yêu cầu trực tiếp từ người dùng."

        info = cls.get_session_info()
        if info["is_trading_hour"]:
            return True, f"Trong giờ giao dịch ({info['session_name']}). Cho phép cập nhật giá."

        if info["is_post_market"]:
            return True, f"Khung giờ đánh giá sau phiên ({info['session_name']}). Cập nhật báo cáo chốt ngày."

        return False, f"Thị trường đang đóng cửa ({info['session_name']}). Tạm dừng gọi API để hạn chế quá tải."


def is_market_open_now() -> bool:
    return MarketSessionManager.get_session_info()["is_trading_hour"]


def get_market_session_status() -> Dict[str, Any]:
    return MarketSessionManager.get_session_info()
