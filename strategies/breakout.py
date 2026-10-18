import pandas as pd
from typing import Dict, Any

class BreakoutStrategy:
    """Detects resistance breakouts without lookahead bias."""

    @staticmethod
    def evaluate_breakout(df: pd.DataFrame) -> Dict[str, Any]:
        result = {
            "breakout_status": "Chưa có Breakout",
            "is_breakout": False,
            "breakout_score": 0.0,
            "resistance_20d": 0.0,
            "distance_to_resistance_pct": 0.0
        }

        if df is None or df.empty or len(df) < 25:
            return result

        df = df.copy()
        # Shift(1) to exclude today's price from resistance calculation!
        df['res_20d'] = df['high'].shift(1).rolling(20, min_periods=10).max()
        df['res_55d'] = df['high'].shift(1).rolling(55, min_periods=20).max()

        last = df.iloc[-1]
        c = last['close']
        r20 = last['res_20d']
        r55 = last['res_55d'] if pd.notna(last['res_55d']) else r20
        vol_ratio = last.get('volume_ratio', 1.0)

        dist_pct = ((c - r20) / r20) * 100.0 if r20 > 0 else 0.0
        result["resistance_20d"] = float(r20)
        result["distance_to_resistance_pct"] = round(dist_pct, 2)

        if c > r55 and vol_ratio >= 1.5:
            result.update({
                "breakout_status": "Breakout Đỉnh 55 Phiên (+Vol đột biến)",
                "is_breakout": True,
                "breakout_score": 100.0
            })
        elif c > r20 and vol_ratio >= 1.3:
            result.update({
                "breakout_status": "Breakout Kháng cự 20 Phiên",
                "is_breakout": True,
                "breakout_score": 80.0
            })
        elif c > r20:
            result.update({
                "breakout_status": "Vượt Đỉnh 20 Phiên (Thanh khoản thấp)",
                "is_breakout": False,
                "breakout_score": 50.0
            })
        elif dist_pct >= -2.0 and dist_pct <= 0.0:
            result.update({
                "breakout_status": "Sát Vùng Kháng Cự (Chờ Breakout)",
                "is_breakout": False,
                "breakout_score": 40.0
            })

        return result
