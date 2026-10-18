import pandas as pd
from typing import Dict, Any

class ScoringEngine:
    """Computes composite 0-100 quantitative rule score."""

    DEFAULT_WEIGHTS = {
        "trend": 0.25,
        "momentum": 0.25,
        "relative_strength": 0.20,
        "volume_breakout": 0.15,
        "liquidity": 0.15
    }

    def __init__(self, weights: Dict[str, float] = None):
        self.weights = weights or self.DEFAULT_WEIGHTS

    def compute_scores(self, df: pd.DataFrame, rs_info: Dict[str, Any], trend_info: Dict[str, Any], breakout_info: Dict[str, Any]) -> Dict[str, float]:
        if df is None or df.empty or len(df) < 5:
            return {"trend_score": 0, "momentum_score": 0, "rs_score": 0, "breakout_score": 0, "liquidity_score": 0, "total_score": 0}

        last = df.iloc[-1]

        # 1. Trend score (0-100)
        t_score = trend_info.get("trend_score", 50.0)

        # 2. Momentum score (RSI + MACD)
        rsi = last.get('rsi_14', 50.0)
        macd_hist = last.get('macd_hist', 0.0)
        
        m_score = 50.0
        if 50 <= rsi <= 70:
            m_score += 25.0
        elif 40 <= rsi < 50:
            m_score += 10.0
        elif rsi > 70:
            m_score += 5.0 # Caution overbought

        if macd_hist > 0:
            m_score += 25.0

        m_score = min(100.0, max(0.0, m_score))

        # 3. RS score (0-100)
        rs_score = rs_info.get("rs_rating", 50.0)

        # 4. Volume & Breakout score (0-100)
        b_score = breakout_info.get("breakout_score", 0.0)
        vol_ratio = last.get('volume_ratio', 1.0)
        if vol_ratio >= 1.5:
            b_score += 20.0
        elif vol_ratio >= 1.2:
            b_score += 10.0
        b_score = min(100.0, b_score)

        # 5. Liquidity score (0-100)
        avg_val = last.get('avg_value_20d', 0.0)
        if avg_val >= 50000000000: # 50B VND
            l_score = 100.0
        elif avg_val >= 10000000000: # 10B VND
            l_score = 80.0
        elif avg_val >= 2000000000: # 2B VND
            l_score = 60.0
        else:
            l_score = 40.0

        w = self.weights
        total_score = (
            t_score * w.get("trend", 0.25) +
            m_score * w.get("momentum", 0.25) +
            rs_score * w.get("relative_strength", 0.20) +
            b_score * w.get("volume_breakout", 0.15) +
            l_score * w.get("liquidity", 0.15)
        )

        return {
            "trend_score": round(t_score, 1),
            "momentum_score": round(m_score, 1),
            "rs_score": round(rs_score, 1),
            "breakout_score": round(b_score, 1),
            "liquidity_score": round(l_score, 1),
            "total_score": round(total_score, 1)
        }
