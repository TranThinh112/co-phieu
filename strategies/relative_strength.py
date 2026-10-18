import pandas as pd
from typing import Dict, Any, Optional

class RelativeStrengthStrategy:
    """Calculates Relative Strength (RS) versus Market Index (VN-Index) and Sector."""

    @staticmethod
    def calculate_relative_strength(stock_df: pd.DataFrame, index_df: pd.DataFrame) -> Dict[str, Any]:
        result = {
            "rs_rating": 50.0,
            "rs_status": "Ngang thị trường",
            "outperforming_index_20d": False,
            "stock_ret_20d": 0.0,
            "index_ret_20d": 0.0,
            "excess_return_20d": 0.0
        }

        if stock_df is None or stock_df.empty or index_df is None or index_df.empty:
            return result

        merged = pd.merge(
            stock_df[['date', 'close']].rename(columns={'close': 'stock_close'}),
            index_df[['date', 'close']].rename(columns={'close': 'index_close'}),
            on='date', how='inner'
        ).sort_values('date')

        if len(merged) < 20:
            return result

        stock_ret_20 = (merged['stock_close'].iloc[-1] - merged['stock_close'].iloc[-20]) / merged['stock_close'].iloc[-20] * 100.0
        index_ret_20 = (merged['index_close'].iloc[-1] - merged['index_close'].iloc[-20]) / merged['index_close'].iloc[-20] * 100.0
        excess = stock_ret_20 - index_ret_20

        # Mansfield RS approximation over 20-50 sessions
        merged['ratio'] = merged['stock_close'] / merged['index_close']
        ratio_ma = merged['ratio'].rolling(window=min(50, len(merged)), min_periods=5).mean()
        mansfield_rs = ((merged['ratio'] / ratio_ma) - 1.0) * 100.0

        latest_rs = mansfield_rs.iloc[-1] if not mansfield_rs.empty and pd.notna(mansfield_rs.iloc[-1]) else 0.0
        rs_rating = min(100.0, max(0.0, 50.0 + (excess * 2.5)))

        if excess > 5.0:
            rs_status = "Mạnh hơn VN-Index rất nhiều"
        elif excess > 0.0:
            rs_status = "Mạnh hơn VN-Index"
        elif excess > -5.0:
            rs_status = "Yếu hơn VN-Index"
        else:
            rs_status = "Rất yếu so với VN-Index"

        result.update({
            "rs_rating": round(rs_rating, 1),
            "rs_status": rs_status,
            "outperforming_index_20d": excess > 0,
            "stock_ret_20d": round(stock_ret_20, 2),
            "index_ret_20d": round(index_ret_20, 2),
            "excess_return_20d": round(excess, 2)
        })

        return result
