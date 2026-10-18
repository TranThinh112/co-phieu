from typing import Dict, Any, Tuple, Optional


class LimitPricePredictor:
    """Tính toán giá Trần / Sàn và đánh giá xung lực phiên tiếp theo
    (Khả năng tiếp tục tăng trần hay giảm sàn) theo quy chuẩn biên độ HOSE, HNX, UPCoM."""

    @staticmethod
    def calculate_limits(close_price: float, exchange: str = "HOSE") -> Tuple[float, float, float]:
        """Tính Giá Tham Chiếu, Giá Trần và Giá Sàn chính xác theo bước giá từng sàn."""
        ref = float(close_price)
        ex = str(exchange or "HOSE").upper()

        if "HOSE" in ex:
            # Biên độ HOSE: +-7%
            pct = 0.07
            if ref < 10000:
                step = 10
            elif ref < 50000:
                step = 50
            else:
                step = 100
        elif "HNX" in ex:
            # Biên độ HNX: +-10%
            pct = 0.10
            step = 100
        else:
            # Biên độ UPCoM: +-15%
            pct = 0.15
            step = 100

        raw_ceil = ref * (1.0 + pct)
        raw_floor = ref * (1.0 - pct)

        # Làm tròn theo bước giá quy định
        ceiling = int(raw_ceil // step) * step
        if raw_floor % step != 0:
            floor = int((raw_floor + step - 1) // step) * step
        else:
            floor = int(raw_floor)

        return ref, float(ceiling), float(floor)

    @classmethod
    def evaluate_momentum(cls, row: Dict[str, Any]) -> Dict[str, Any]:
        """Đánh giá xác suất phiên tới có tiếp tục tăng trần hay giảm sàn không."""
        sym = str(row.get("symbol", ""))
        ex = str(row.get("exchange", "HOSE"))
        close_p = float(row.get("close_price", 0.0))
        chg_p = float(row.get("price_change", 0.0))
        vol_r = float(row.get("volume_ratio", 1.0))
        rsi_val = float(row.get("rsi", 50.0))
        rule_sc = float(row.get("rule_score", 50.0))
        trend_str = str(row.get("trend", ""))
        catalysts = row.get("detected_catalysts", []) or []
        warnings = row.get("negative_warnings", []) or []
        has_fatal = bool(row.get("has_fatal_news", False))

        ref_p, ceil_p, floor_p = cls.calculate_limits(close_p, ex)

        # -----------------------------------------------------------------
        # 1. ĐO LƯỜNG XUNG LỰC TĂNG TRẦN (CEILING MOMENTUM SCORE: 0 - 100)
        # -----------------------------------------------------------------
        c_score = 30.0

        # Nếu phiên hôm nay đã tăng mạnh sát trần
        hose_limit = 6.0
        if "HNX" in ex.upper():
            hose_limit = 8.5
        elif "UPCOM" in ex.upper():
            hose_limit = 12.0

        if chg_p >= hose_limit:
            c_score += 25.0  # Quán tính dư mua trần rất cao
        elif chg_p >= 3.0:
            c_score += 15.0

        # Khối lượng bùng nổ (Dòng tiền tổ chức hấp thụ cung)
        if vol_r >= 3.0:
            c_score += 20.0
        elif vol_r >= 1.8:
            c_score += 12.0
        elif vol_r < 0.8:
            c_score -= 10.0  # Cạn tiền khó đẩy trần

        # Tin tức sự kiện hỗ trợ
        if catalysts:
            c_score += 15.0

        # Điểm định lượng AI cao
        if rule_sc >= 75:
            c_score += 10.0

        # Phạt nếu RSI quá mua cực đại (dễ rung lắc đảo chiều, khó trần tiếp)
        if rsi_val >= 78.0:
            c_score -= 25.0
        elif rsi_val >= 72.0:
            c_score -= 12.0

        if has_fatal or warnings:
            c_score -= 40.0

        c_score = max(0.0, min(100.0, c_score))

        # -----------------------------------------------------------------
        # 2. ĐO LƯỜNG NGUY CƠ GIẢM SÀN (FLOOR RISK SCORE: 0 - 100)
        # -----------------------------------------------------------------
        f_score = 5.0

        if has_fatal:
            f_score += 55.0  # Tin xấu nghiêm trọng dễ trắng bên mua
        elif warnings:
            f_score += 25.0

        if chg_p <= -hose_limit:
            f_score += 30.0  # Đang bị xả sàn phiên trước
        elif chg_p <= -3.0:
            f_score += 15.0

        if "Giảm" in trend_str or "Downtrend" in trend_str:
            f_score += 10.0

        # Giảm thiểu nguy cơ sàn nếu cổ phiếu khỏe và có dòng tiền lớn
        if rule_sc >= 65:
            f_score -= 15.0
        if catalysts:
            f_score -= 15.0
        if vol_r >= 1.5 and chg_p > 0:
            f_score -= 15.0

        f_score = max(0.0, min(100.0, f_score))

        # -----------------------------------------------------------------
        # 3. KẾT LUẬN ĐÁNH GIÁ PHIÊN TIẾP THEO
        # -----------------------------------------------------------------
        if f_score >= 50.0:
            pred_badge = "🔵 CẢNH BÁO NGUY CƠ GIẢM SÀN (Xác suất >50%)"
            pred_reason = f"Có tin xấu nghiêm trọng hoặc áp lực bán tháo tháo chạy, nguy cơ cao bị ép về giá sàn {floor_p:,.0f} đ."
            floor_risk_desc = "🔴 Rủi ro sàn: RẤT CAO"
        elif c_score >= 70.0:
            pred_badge = "🟣 KHẢ NĂNG CAO TIẾP TỤC TĂNG TRẦN (Xác suất 70-80%)"
            pred_reason = f"Dòng tiền bùng nổ (Vol {vol_r:.1f}x), quán tính mua áp đảo và có tin tức hỗ trợ mạnh, giá có dư địa hướng thẳng tới giá trần {ceil_p:,.0f} đ."
            floor_risk_desc = "🟢 Rủi ro sàn: Cực thấp (<5%)"
        elif c_score >= 50.0:
            pred_badge = "🟢 TIẾP TỤC TĂNG TỐT (+3% ĐẾN +5%)"
            pred_reason = f"Xung lực tăng duy trì rất khỏe nhưng khó trần cứng phiên thứ 2 liên tiếp do tiệm cận vùng cản kỹ thuật gần trần {ceil_p:,.0f} đ."
            floor_risk_desc = "🟢 Rủi ro sàn: Cực thấp (<5%)"
        else:
            pred_badge = "🟡 RUNG LẮC HẠ NHIỆT (KHÓ TRẦN TIẾP)"
            pred_reason = f"Chỉ số RSI ({rsi_val:.0f}) ở vùng cao hoặc cần tích lũy hấp thụ áp lực chốt lời, biên độ dao động trong khoảng {floor_p*1.02:,.0f} đ - {ceil_p*0.97:,.0f} đ."
            floor_risk_desc = "🟢 Rủi ro sàn: Rất thấp (<5%)"

        return {
            "symbol": sym,
            "exchange": ex,
            "ref_price": ref_p,
            "ceiling_price": ceil_p,
            "floor_price": floor_p,
            "ceiling_score": c_score,
            "floor_score": f_score,
            "next_session_prediction": pred_badge,
            "floor_risk_desc": floor_risk_desc,
            "detailed_reason": pred_reason
        }
