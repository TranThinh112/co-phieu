import pandas as pd
from typing import Dict, Any

class PullbackStrategy:
    """Detects healthy pullbacks to key support moving averages in an uptrend."""

    @staticmethod
    def evaluate_pullback(df: pd.DataFrame) -> Dict[str, Any]:
        result = {
            "is_pullback": False,
            "pullback_type": "Không có",
            "support_level": 0.0,
            "pullback_score": 0.0
        }

        if df is None or df.empty or len(df) < 20:
            return result

        last = df.iloc[-1]
        c = last['close']
        l = last['low']
        s20 = last.get('sma_20', c)
        s50 = last.get('sma_50', s20)
        vol_ratio = last.get('volume_ratio', 1.0)

        # In an uptrend, low price touches or comes close to SMA20/50 while close stays near or above
        dist_s20_pct = (l - s20) / s20 * 100.0 if s20 > 0 else 999.0
        dist_s50_pct = (l - s50) / s50 * 100.0 if s50 > 0 else 999.0

        if abs(dist_s20_pct) <= 2.0 and c >= s20 * 0.99 and vol_ratio <= 1.2:
            result.update({
                "is_pullback": True,
                "pullback_type": "Pullback về SMA20 (Thanh khoản cạn)",
                "support_level": float(s20),
                "pullback_score": 85.0
            })
        elif abs(dist_s50_pct) <= 2.5 and c >= s50 * 0.98 and vol_ratio <= 1.2:
            result.update({
                "is_pullback": True,
                "pullback_type": "Pullback về SMA50 (Hỗ trợ trung hạn)",
                "support_level": float(s50),
                "pullback_score": 75.0
            })

        return result
