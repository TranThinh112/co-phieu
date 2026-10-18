import pandas as pd
from typing import Dict, Any, Optional, List


class ExitAdvisor:
    """Hệ thống cố vấn & phát tín hiệu Chốt Lời / Cắt Lỗ tự động.
    Phân tích tỷ lệ lợi nhuận, ngưỡng hỗ trợ/kháng cự, chỉ báo RSI và hành động giá
    để hướng dẫn nhà đầu tư thời điểm chốt lời tối ưu hoặc cắt lỗ bảo toàn vốn."""

    @staticmethod
    def evaluate_exit(
        symbol: str,
        buy_price: float,
        current_price: float,
        highest_price: Optional[float] = None,
        lowest_price: Optional[float] = None,
        rsi: Optional[float] = None,
        sma_20: Optional[float] = None,
        days_held: int = 0
    ) -> Dict[str, Any]:
        """Đánh giá chi tiết trạng thái vị thế và đưa ra khuyến nghị Chốt Lời / Cắt Lỗ."""
        if buy_price <= 0:
            return {"action": "HOLD", "action_label": "⚪ TIẾP TỤC NẮM GIỮ", "reason": "Chưa có giá mua hợp lệ."}

        pnl_pct = round(((current_price - buy_price) / buy_price) * 100.0, 2)
        high_p = highest_price or max(buy_price, current_price)
        max_gain_pct = round(((high_p - buy_price) / buy_price) * 100.0, 2)

        # Ngưỡng kỹ thuật chuẩn
        sl_pct = -5.0           # Cắt lỗ cứng 5%
        tp1_pct = 8.0           # Chốt lời 1: +8% (Tỷ lệ R:R = 1:1.6)
        tp2_pct = 15.0          # Chốt lời 2: +15% (Tỷ lệ R:R = 1:3.0)
        trailing_trigger = 4.5  # Bật chặn lãi khi lãi vượt 4.5%

        sl_price = round(buy_price * 0.95, 0)
        tp1_price = round(buy_price * 1.08, 0)
        tp2_price = round(buy_price * 1.15, 0)
        trailing_stop_price = round(buy_price * 1.01, 0) if max_gain_pct >= trailing_trigger else sl_price

        # -------------------------------------------------------------
        # 1. TRƯỜNG HỢP CẮT LỖ KHẨN CẤP (STOP-LOSS)
        # -------------------------------------------------------------
        if pnl_pct <= sl_pct or current_price <= sl_price:
            return {
                "symbol": symbol,
                "action": "STOP_LOSS",
                "action_label": "🔴 BÁN CẮT LỖ KHẨN CẤP (100% VỊ THẾ)",
                "pnl_pct": pnl_pct,
                "buy_price": buy_price,
                "current_price": current_price,
                "sl_price": sl_price,
                "tp1_price": tp1_price,
                "tp2_price": tp2_price,
                "trailing_stop_price": sl_price,
                "urgency": "KHẨN CẤP (Ưu tiên số 1)",
                "reason_title": f"Chạm ngưỡng cắt lỗ kỷ luật {sl_pct}%",
                "reason_detail": (
                    f"Giá giảm {pnl_pct:+.2f}% vi phạm mốc cắt lỗ kỷ luật ({sl_price:,.0f} đ). "
                    f"Lý do cần bán ngay: Cổ phiếu đã gãy cấu trúc tăng giá ngắn hạn, áp lực bán gia tăng. "
                    f"Bán dứt khoát 100% khối lượng để bảo toàn 95% vốn gốc, tuyệt đối không gồng lỗ hay trung bình giá xuống."
                )
            }

        # Kiểm tra thủng đường hỗ trợ SMA20 khi đang lỗ nhẹ (-2% đến -4.9%)
        if sma_20 and current_price < sma_20 and pnl_pct < -2.0:
            return {
                "symbol": symbol,
                "action": "EARLY_STOP",
                "action_label": "🔴 HẠ TỶ TRỌNG PHÒNG THỦ (BÁN 50-70%)",
                "pnl_pct": pnl_pct,
                "buy_price": buy_price,
                "current_price": current_price,
                "sl_price": sl_price,
                "tp1_price": tp1_price,
                "tp2_price": tp2_price,
                "trailing_stop_price": sl_price,
                "urgency": "CAO",
                "reason_title": "Đóng cửa thủng đường hỗ trợ SMA20",
                "reason_detail": (
                    f"Giá hiện tại ({current_price:,.0f} đ) đã đóng cửa dưới đường SMA20 ({sma_20:,.0f} đ) "
                    f"kèm mức lỗ {pnl_pct:+.2f}%. Lý do: Mất mốc hỗ trợ động quan trọng cho thấy phe mua đã suy yếu. "
                    f"Khuyến nghị chủ động hạ 50-70% vị thế để thu hẹp rủi ro trước khi chạm ngưỡng cắt lỗ cứng."
                )
            }

        # -------------------------------------------------------------
        # 2. TRƯỜNG HỢP CHỐT LỜI MỤC TIÊU 2 (TP2 - LÃI LỚN)
        # -------------------------------------------------------------
        if pnl_pct >= tp2_pct or current_price >= tp2_price:
            return {
                "symbol": symbol,
                "action": "TAKE_PROFIT_ALL",
                "action_label": "🟢 CHỐT LỜI TOÀN BỘ (BÁN 100% HIỆN THỰC HÓA LÃI)",
                "pnl_pct": pnl_pct,
                "buy_price": buy_price,
                "current_price": current_price,
                "sl_price": sl_price,
                "tp1_price": tp1_price,
                "tp2_price": tp2_price,
                "trailing_stop_price": tp1_price,
                "urgency": "CAO",
                "reason_title": f"Đạt mục tiêu chốt lời tối đa TP2 (+{tp2_pct}%)",
                "reason_detail": (
                    f"Cổ phiếu đã tăng trưởng xuất sắc {pnl_pct:+.2f}%, chạm mốc mục tiêu TP2 ({tp2_price:,.0f} đ). "
                    f"Lý do nên chốt: Vị thế đã đạt trọn vẹn sóng Swing (R:R > 1:3). Dư địa tăng tiếp theo hẹp hơn nguy cơ "
                    f"gặp áp lực phân phối chốt lời của các quỹ lớn. Hãy bán chốt lời 100% để bảo vệ thành quả trọn vẹn."
                )
            }

        # -------------------------------------------------------------
        # 3. TRƯỜNG HỢP CHỐT LỜI KỸ THUẬT (RSI QUÁ MUA CỰC ĐẠI > 75)
        # -------------------------------------------------------------
        if rsi and rsi >= 75.0 and pnl_pct >= 6.0:
            return {
                "symbol": symbol,
                "action": "TECHNICAL_PROFIT",
                "action_label": "🟢 CHỐT LỜI CHỦ ĐỘNG 50-70% (RSI QUÁ MUA)",
                "pnl_pct": pnl_pct,
                "buy_price": buy_price,
                "current_price": current_price,
                "sl_price": sl_price,
                "tp1_price": tp1_price,
                "tp2_price": tp2_price,
                "trailing_stop_price": buy_price,
                "urgency": "TRUNG BÌNH - CAO",
                "reason_title": f"Chỉ số RSI({rsi:.1f}) đi vào vùng quá mua cực đại",
                "reason_detail": (
                    f"Lợi nhuận đang đạt {pnl_pct:+.2f}% nhưng RSI đã lên mức {rsi:.1f} (>75). "
                    f"Lý do: Lực mua FOMO đang đẩy giá vào vùng quá nhiệt, xác suất cao sắp có rung lắc điều chỉnh mạnh. "
                    f"Chủ động bán chốt lời 50-70% ngay khi giá đang hưng phấn để tối đa hóa mức giá khớp tốt nhất."
                )
            }

        # -------------------------------------------------------------
        # 4. TRƯỜNG HỢP CHỐT LỜI MỤC TIÊU 1 (TP1 - BÁN 50%)
        # -------------------------------------------------------------
        if pnl_pct >= tp1_pct or current_price >= tp1_price:
            return {
                "symbol": symbol,
                "action": "TAKE_PROFIT_HALF",
                "action_label": "🟢 BÁN CHỐT LỜI 50% & NÂNG CHẶN LÃI (TP1 ĐẠT CHUẨN)",
                "pnl_pct": pnl_pct,
                "buy_price": buy_price,
                "current_price": current_price,
                "sl_price": sl_price,
                "tp1_price": tp1_price,
                "tp2_price": tp2_price,
                "trailing_stop_price": round(buy_price * 1.02, 0),
                "urgency": "TRUNG BÌNH",
                "reason_title": f"Đạt mục tiêu chốt lời 1 TP1 (+{tp1_pct}%)",
                "reason_detail": (
                    f"Cổ phiếu đã tăng {pnl_pct:+.2f}%, chạm chuẩn mục tiêu chốt lời TP1 ({tp1_price:,.0f} đ). "
                    f"Chiến lược hành động: Bán 50% khối lượng để bỏ túi tiền thật; nâng điểm chặn lãi cho 50% còn lại "
                    f"lên mức hòa vốn ({round(buy_price * 1.02, 0):,.0f} đ). Sau bước này vị thế trở thành LỆNH KHÔNG THỂ THUA."
                )
            }

        # -------------------------------------------------------------
        # 5. TRƯỜNG HỢP NÂNG CHẶN LÃI (TRAILING STOP)
        # -------------------------------------------------------------
        if pnl_pct >= trailing_trigger:
            return {
                "symbol": symbol,
                "action": "TRAILING_STOP",
                "action_label": "🟡 NÂNG CHẶN LÃI LÊN HÒA VỐN (BẢO VỆ VỐN)",
                "pnl_pct": pnl_pct,
                "buy_price": buy_price,
                "current_price": current_price,
                "sl_price": sl_price,
                "tp1_price": tp1_price,
                "tp2_price": tp2_price,
                "trailing_stop_price": round(buy_price * 1.01, 0),
                "urgency": "THEO DÕI",
                "reason_title": f"Lợi nhuận đạt {pnl_pct:+.2f}%, kích hoạt chặn lãi an toàn",
                "reason_detail": (
                    f"Vị thế đang có lãi {pnl_pct:+.2f}%. Nguyên tắc quản trị: Nâng điểm dừng lỗ từ mốc {sl_price:,.0f} đ "
                    f"lên mức giá vốn ({round(buy_price * 1.01, 0):,.0f} đ). Tuyệt đối không để một khoản đầu tư đã sinh lời "
                    f"biến thành một khoản lỗ nếu thị trường bất ngờ quay đầu."
                )
            }

        # -------------------------------------------------------------
        # 6. TRƯỜNG HỢP TIẾP TỤC NẮM GIỮ (HOLD)
        # -------------------------------------------------------------
        return {
            "symbol": symbol,
            "action": "HOLD",
            "action_label": "⚪ TIẾP TỤC NẮM GIỮ (CHƯA VI PHẠM)",
            "pnl_pct": pnl_pct,
            "buy_price": buy_price,
            "current_price": current_price,
            "sl_price": sl_price,
            "tp1_price": tp1_price,
            "tp2_price": tp2_price,
            "trailing_stop_price": sl_price,
            "urgency": "BÌNH THƯỜNG",
            "reason_title": "Cổ phiếu vận động trong biên độ an toàn",
            "reason_detail": (
                f"Tỷ suất hiện tại {pnl_pct:+.2f}%. Giá đang vận động bình thường trong vùng tích lũy, "
                f"chưa chạm ngưỡng cắt lỗ ({sl_price:,.0f} đ) và chưa đạt mục tiêu chốt lời TP1 ({tp1_price:,.0f} đ). "
                f"Khuyến nghị kiên nhẫn nắm giữ theo chu kỳ sóng Swing."
            )
        }
