import pandas as pd
from typing import Dict, Any, Tuple
from features.liquidity import LiquidityFeatures
from strategies.trend_following import TrendFollowingStrategy
from strategies.breakout import BreakoutStrategy

class StockFilters:
    """Applies screening criteria filters to individual stock datasets."""

    def __init__(self, min_avg_volume: float = 50000, min_avg_value: float = 1000000000):
        self.min_avg_volume = min_avg_volume
        self.min_avg_value = min_avg_value

    def apply_filters(self, df: pd.DataFrame) -> Dict[str, Any]:
        filter_res = {
            "passed_all": False,
            "passed_liquidity": False,
            "liquidity_reason": "",
            "trend_info": {},
            "breakout_info": {}
        }

        if df is None or df.empty or len(df) < 20:
            filter_res["liquidity_reason"] = "Không đủ số lượng phiên dữ liệu (tối thiểu 20 phiên)"
            return filter_res

        passed_liq, liq_msg = LiquidityFeatures.check_liquidity_filter(df, self.min_avg_volume, self.min_avg_value)
        filter_res["passed_liquidity"] = passed_liq
        filter_res["liquidity_reason"] = liq_msg

        if not passed_liq:
            return filter_res

        trend_info = TrendFollowingStrategy.evaluate_trend(df)
        breakout_info = BreakoutStrategy.evaluate_breakout(df)

        filter_res.update({
            "passed_all": True,
            "trend_info": trend_info,
            "breakout_info": breakout_info
        })
        return filter_res
