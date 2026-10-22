"""
Japanese Candlestick Pattern Recognition & Price Action Analyzer.
Detects high-probability candlestick patterns for Vietnam stock market:
1. Bullish Marubozu (Thân nến xanh đặc, xung lực áp đảo)
2. Hammer / Bullish Pinbar (Nến búa rút chân tại hỗ trợ)
3. Bullish Engulfing (Nến nhấn chìm tăng trưởng)
4. Morning Star (Cụm nến Sao Mai đảo chiều tăng đáy)
5. Shooting Star / Inverted Pinbar (Nến bắn sao cụt đầu tại đỉnh)
6. Bearish Engulfing (Nến nhấn chìm giảm, cảnh báo phân phối)
7. Doji (Nến Doji giằng co cung cầu)
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np


class CandlestickAnalyzer:
    """Analyzes recent OHLC candles to identify Price Action patterns."""

    @staticmethod
    def analyze_patterns(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Nhận diện mẫu hình nến của phiên gần nhất và cụm 2-3 phiên trước đó.
        Trả về:
            - pattern_name: Tên mẫu hình tiếng Việt
            - sentiment: BULLISH / BEARISH / NEUTRAL
            - score_adjustment: Điểm cộng/trừ (-15 đến +15)
            - detail_reason: Diễn giải chi tiết lý do và hành động gợi ý
            - is_reversal: Có phải tín hiệu đảo chiều không
        """
        default_res = {
            "pattern_name": "Nến Tiêu Chuẩn",
            "sentiment": "NEUTRAL",
            "score_adjustment": 0.0,
            "detail_reason": "Vận động nến dao động bình thường trong biên độ",
            "is_reversal": False,
            "body_ratio": 0.5,
            "upper_shadow_pct": 0.25,
            "lower_shadow_pct": 0.25
        }

        if df is None or df.empty or len(df) < 3:
            return default_res

        # Lấy 3 nến gần nhất
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        prev2 = df.iloc[-3] if len(df) >= 3 else prev

        o = float(curr["open"])
        h = float(curr["high"])
        l = float(curr["low"])
        c = float(curr["close"])

        o_p = float(prev["open"])
        h_p = float(prev["high"])
        l_p = float(prev["low"])
        c_p = float(prev["close"])

        o_p2 = float(prev2["open"])
        c_p2 = float(prev2["close"])

        total_range = h - l
        if total_range <= 0:
            return default_res

        body = abs(c - o)
        upper_shadow = h - max(o, c)
        lower_shadow = min(o, c) - l

        body_ratio = body / total_range
        upper_ratio = upper_shadow / total_range
        lower_ratio = lower_shadow / total_range

        is_green = c >= o
        is_red = c < o
        prev_is_red = c_p < o_p
        prev_is_green = c_p > o_p

        rsi_val = float(curr.get("rsi", curr.get("rsi_14", 50.0)))
        vol_ratio = float(curr.get("volume_ratio", 1.0))

        # -----------------------------------------------------------------
        # 1. CỤM 3 NẾN: MORNING STAR (SAO MAI ĐẢO CHIỀU TĂNG TỪ ĐÁY)
        # -----------------------------------------------------------------
        if len(df) >= 3:
            body_p2 = abs(c_p2 - o_p2)
            body_p = abs(c_p - o_p)
            # Nến 1 giảm mạnh, Nến 2 thân nhỏ/doji, Nến 3 tăng mạnh vượt 50% thân nến 1
            if prev2["close"] < prev2["open"] and body_p < (body_p2 * 0.5):
                if is_green and c > (o_p2 + c_p2) / 2.0:
                    return {
                        "pattern_name": "⭐ Cụm Sao Mai Đảo Chiều (Morning Star)",
                        "sentiment": "BULLISH",
                        "score_adjustment": 14.0,
                        "detail_reason": "Cụm nến Sao Mai xác nhận phe mua áp đảo tại vùng hỗ trợ, tỷ lệ đảo chiều tăng giá rất cao",
                        "is_reversal": True,
                        "body_ratio": round(body_ratio, 2),
                        "upper_shadow_pct": round(upper_ratio, 2),
                        "lower_shadow_pct": round(lower_ratio, 2)
                    }

        # -----------------------------------------------------------------
        # 2. CỤM 2 NẾN: BULLISH ENGULFING (NHẤN CHÌM TĂNG TRƯỞNG)
        # -----------------------------------------------------------------
        if prev_is_red and is_green:
            if c >= o_p and o <= c_p and body > abs(c_p - o_p):
                return {
                    "pattern_name": "🟢 Nhấn Chìm Tăng (Bullish Engulfing)",
                    "sentiment": "BULLISH",
                    "score_adjustment": 12.0,
                    "detail_reason": "Thân nến tăng nuốt trọn nến giảm hôm trước, lực cầu hấp thụ sạch lượng cung bán tháo",
                    "is_reversal": True,
                    "body_ratio": round(body_ratio, 2),
                    "upper_shadow_pct": round(upper_ratio, 2),
                    "lower_shadow_pct": round(lower_ratio, 2)
                }

        # -----------------------------------------------------------------
        # 3. NẾN RÚT CHÂN / BÚA (HAMMER / BULLISH PINBAR)
        # -----------------------------------------------------------------
        # Râu nến dưới dài gấp ít nhất 2 lần thân nến, râu nến trên rất ngắn
        if lower_shadow >= 2.0 * body and upper_ratio <= 0.15:
            # Giá đóng cửa nằm ở 35% trên cùng của cây nến
            if (c - l) / total_range >= 0.65:
                return {
                    "pattern_name": "🔨 Nến Búa Rút Chân (Hammer Pinbar)",
                    "sentiment": "BULLISH",
                    "score_adjustment": 12.0,
                    "detail_reason": "Lực cầu bắt đáy mạnh mẽ rút chân quyết liệt từ vùng giá thấp, tạo hỗ trợ ngắn hạn cứng",
                    "is_reversal": True,
                    "body_ratio": round(body_ratio, 2),
                    "upper_shadow_pct": round(upper_ratio, 2),
                    "lower_shadow_pct": round(lower_ratio, 2)
                }

        # -----------------------------------------------------------------
        # 4. NẾN MARUBOZU TĂNG (THÂN NẾN XANH ĐẶC DÀI)
        # -----------------------------------------------------------------
        if is_green and body_ratio >= 0.80 and upper_ratio <= 0.08 and lower_ratio <= 0.08:
            return {
                "pattern_name": "🚀 Nến Marubozu Tăng Cường Lực",
                "sentiment": "BULLISH",
                "score_adjustment": 15.0,
                "detail_reason": "Thân nến xanh đặc không râu, phe mua áp đảo từ đầu phiên tới ATC, quán tính tăng rất mạnh",
                "is_reversal": False,
                "body_ratio": round(body_ratio, 2),
                "upper_shadow_pct": round(upper_ratio, 2),
                "lower_shadow_pct": round(lower_ratio, 2)
            }

        # -----------------------------------------------------------------
        # 5. CẢNH BÁO BẪY ĐỈNH: SHOOTING STAR (BẮN SAO / CỤT ĐẦU)
        # -----------------------------------------------------------------
        if upper_shadow >= 2.0 * body and lower_ratio <= 0.15:
            if (h - max(o, c)) / total_range >= 0.60:
                is_danger = (rsi_val >= 68.0) or (vol_ratio >= 1.5)
                adj = -15.0 if is_danger else -10.0
                return {
                    "pattern_name": "⚠️ Nến Bắn Sao Cụt Đầu (Shooting Star)",
                    "sentiment": "BEARISH",
                    "score_adjustment": adj,
                    "detail_reason": "Áp lực chốt lời xả hàng mạnh khiến giá rụt cổ tạo râu trên dài, cảnh báo bẫy tăng giá Bull Trap",
                    "is_reversal": True,
                    "body_ratio": round(body_ratio, 2),
                    "upper_shadow_pct": round(upper_ratio, 2),
                    "lower_shadow_pct": round(lower_ratio, 2)
                }

        # -----------------------------------------------------------------
        # 6. CẢNH BÁO: BEARISH ENGULFING (NHẤN CHÌM GIẢM)
        # -----------------------------------------------------------------
        if prev_is_green and is_red:
            if o >= c_p and c <= o_p and body > abs(c_p - o_p):
                return {
                    "pattern_name": "🔴 Nến Nhấn Chìm Giảm (Bearish Engulfing)",
                    "sentiment": "BEARISH",
                    "score_adjustment": -12.0,
                    "detail_reason": "Phe bán chiếm trọn quyền kiểm soát, phủ nhận đà tăng của phiên hôm trước",
                    "is_reversal": True,
                    "body_ratio": round(body_ratio, 2),
                    "upper_shadow_pct": round(upper_ratio, 2),
                    "lower_shadow_pct": round(lower_ratio, 2)
                }

        # -----------------------------------------------------------------
        # 7. NẾN DOJI (LƯỠNG LỰ CUNG CẦU)
        # -----------------------------------------------------------------
        if body_ratio <= 0.10:
            if lower_ratio >= 0.40 and upper_ratio <= 0.15:
                p_name = "🦗 Nến Doji Chuồn Chuồn (Dragonfly Doji)"
                adj = 6.0
                sent = "BULLISH"
                reason = "Doji chuồn chuồn xuất hiện lực đỡ giá cuối phiên, tín hiệu giữ nền tốt"
            elif upper_ratio >= 0.40 and lower_ratio <= 0.15:
                p_name = "🪦 Nến Doji Bia Mộ (Gravestone Doji)"
                adj = -8.0
                sent = "BEARISH"
                reason = "Doji bia mộ bị đè bán từ đỉnh phiên, thể hiện lực cung treo lơ lửng"
            else:
                p_name = "⚖️ Nến Doji Lưỡng Lự"
                adj = 0.0
                sent = "NEUTRAL"
                reason = "Thị trường cân bằng giằng co giữa phe mua và phe bán, chờ xác nhận phiên tới"

            return {
                "pattern_name": p_name,
                "sentiment": sent,
                "score_adjustment": adj,
                "detail_reason": reason,
                "is_reversal": False,
                "body_ratio": round(body_ratio, 2),
                "upper_shadow_pct": round(upper_ratio, 2),
                "lower_shadow_pct": round(lower_ratio, 2)
            }

        # Nến tiêu chuẩn (Tăng hoặc giảm nhẹ)
        if is_green:
            return {
                "pattern_name": "🟢 Nến Tăng Tiêu Chuẩn",
                "sentiment": "BULLISH",
                "score_adjustment": 4.0,
                "detail_reason": "Giá đóng cửa cao hơn giá mở cửa, duy trì đà tăng ổn định",
                "is_reversal": False,
                "body_ratio": round(body_ratio, 2),
                "upper_shadow_pct": round(upper_ratio, 2),
                "lower_shadow_pct": round(lower_ratio, 2)
            }
        else:
            return {
                "pattern_name": "🔴 Nến Giảm Tiêu Chuẩn",
                "sentiment": "BEARISH",
                "score_adjustment": -4.0,
                "detail_reason": "Giá đóng cửa thấp hơn giá mở cửa, chịu áp lực điều chỉnh thông thường",
                "is_reversal": False,
                "body_ratio": round(body_ratio, 2),
                "upper_shadow_pct": round(upper_ratio, 2),
                "lower_shadow_pct": round(lower_ratio, 2)
            }
