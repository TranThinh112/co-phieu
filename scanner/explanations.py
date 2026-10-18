from typing import Dict, Any, List, Tuple
import pandas as pd

class SignalExplanations:
    """Generates human-readable investment thesis, positive factors, and risk factors."""

    @staticmethod
    def generate_explanations(
        df: pd.DataFrame,
        trend_info: Dict[str, Any],
        breakout_info: Dict[str, Any],
        rs_info: Dict[str, Any],
        scores: Dict[str, float],
        passed_liquidity: bool,
        liquidity_reason: str
    ) -> Tuple[List[str], List[str], str]:

        positive_factors = []
        risk_factors = []

        if not passed_liquidity:
            risk_factors.append(f"Không đạt điều kiện thanh khoản: {liquidity_reason}")
            return positive_factors, risk_factors, "High"

        if df is None or df.empty or len(df) < 5:
            risk_factors.append("Dữ liệu lịch sử quá ít")
            return positive_factors, risk_factors, "High"

        last = df.iloc[-1]
        c = last['close']
        rsi = last.get('rsi_14', 50.0)
        vol_ratio = last.get('volume_ratio', 1.0)
        vol_20d = last.get('volatility_20d', 20.0)

        # 1. Trend factors
        if trend_info.get("above_sma200"):
            positive_factors.append("Xu hướng dài hạn tích cực (Đóng cửa trên đường SMA200)")
        if trend_info.get("above_sma20") and trend_info.get("above_sma50"):
            positive_factors.append("Xu hướng ngắn/trung hạn tăng (Nằm trên SMA20 và SMA50)")
        elif not trend_info.get("above_sma20"):
            risk_factors.append("Giá đóng cửa nằm dưới đường trung bình 20 phiên (SMA20)")

        # 2. Breakout factors
        if breakout_info.get("is_breakout"):
            positive_factors.append(f"Tín hiệu bùng nổ: {breakout_info.get('breakout_status')}")
        elif breakout_info.get("distance_to_resistance_pct", -99) >= -2.0 and breakout_info.get("distance_to_resistance_pct") <= 0:
            positive_factors.append("Đang tích lũy sát vùng kháng cự 20 phiên (Chờ breakout)")

        # 3. Volume & Momentum factors
        if vol_ratio >= 1.5:
            positive_factors.append(f"Khối lượng giao dịch bùng nổ (Gấp {vol_ratio:.1f} lần TB 20 phiên)")
        elif vol_ratio < 0.7:
            risk_factors.append(f"Thanh khoản sụt giảm so với trung bình (Chỉ đạt {vol_ratio*100:.0f}%)")

        if 50 <= rsi <= 68:
            positive_factors.append(f"Chỉ số RSI duy trì ở vùng tăng giá lành mạnh ({rsi:.1f})")
        elif rsi > 70:
            risk_factors.append(f"RSI ở vùng quá mua ({rsi:.1f}), rủi ro điều chỉnh ngắn hạn")
        elif rsi < 40:
            risk_factors.append(f"RSI ở vùng yếu ({rsi:.1f}), sức mạnh giá kém")

        # 4. Relative Strength factors
        excess = rs_info.get("excess_return_20d", 0.0)
        if excess > 3.0:
            positive_factors.append(f"Sức mạnh tương đối vượt trội so với VN-Index (+{excess:.1f}% trong 20 phiên)")
        elif excess < -3.0:
            risk_factors.append(f"Sức mạnh tương đối yếu hơn VN-Index ({excess:.1f}% trong 20 phiên)")

        # 5. Volatility / Risk Level Estimation
        risk_level = "Medium"
        if vol_20d > 40.0 or rsi > 75 or not trend_info.get("above_sma50"):
            risk_level = "High"
        elif vol_20d < 25.0 and trend_info.get("above_sma20") and trend_info.get("above_sma50") and 50 <= rsi <= 65:
            risk_level = "Low"

        return positive_factors, risk_factors, risk_level
