import pandas as pd
from typing import Dict, Any

class TrendFollowingStrategy:
    """Evaluates trend direction and strength for a stock."""

    @staticmethod
    def evaluate_trend(df: pd.DataFrame) -> Dict[str, Any]:
        result = {
            "trend": "Đi ngang",
            "trend_score": 50.0,
            "is_bullish": False,
            "above_sma20": False,
            "above_sma50": False,
            "above_sma200": False,
            "sma_alignment": False
        }

        if df is None or df.empty or len(df) < 20:
            return result

        last = df.iloc[-1]
        c = last['close']
        s20 = last.get('sma_20', c)
        s50 = last.get('sma_50', s20)
        s200 = last.get('sma_200', s50)

        above_20 = c > s20
        above_50 = c > s50
        above_200 = c > s200
        aligned = (s20 >= s50) and (s50 >= s200)

        score = 0.0
        if above_20: score += 25.0
        if above_50: score += 25.0
        if above_200: score += 25.0
        if aligned: score += 25.0

        if score >= 75.0:
            trend_str = "Tăng mạnh (Strong Uptrend)"
            is_bullish = True
        elif score >= 50.0:
            trend_str = "Tăng nhẹ (Uptrend)"
            is_bullish = True
        elif score <= 25.0:
            trend_str = "Giảm (Downtrend)"
            is_bullish = False
        else:
            trend_str = "Đi ngang (Sideways)"
            is_bullish = False

        result.update({
            "trend": trend_str,
            "trend_score": score,
            "is_bullish": is_bullish,
            "above_sma20": above_20,
            "above_sma50": above_50,
            "above_sma200": above_200,
            "sma_alignment": aligned
        })
        return result
