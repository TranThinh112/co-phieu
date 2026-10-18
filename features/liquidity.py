import pandas as pd
from typing import Tuple

class LiquidityFeatures:
    """Calculates liquidity indicators and checks filter thresholds."""

    @staticmethod
    def add_liquidity_indicators(df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty or len(df) < 5:
            return df

        df = df.copy()
        vol = df['volume']
        val = df['trading_value'] if 'trading_value' in df.columns else df['close'] * df['volume']

        df['avg_volume_20d'] = vol.rolling(window=20, min_periods=5).mean()
        df['avg_value_20d'] = val.rolling(window=20, min_periods=5).mean()
        df['volume_ratio'] = vol / df['avg_volume_20d'].replace(0, 1.0)

        return df

    @staticmethod
    def check_liquidity_filter(df: pd.DataFrame, min_avg_volume: float = 50000, min_avg_value: float = 1000000000) -> Tuple[bool, str]:
        if df is None or df.empty or len(df) < 5:
            return False, "Thiếu dữ liệu giao dịch"

        last_row = df.iloc[-1]
        avg_vol = last_row.get('avg_volume_20d', 0.0)
        avg_val = last_row.get('avg_value_20d', 0.0)

        if avg_vol < min_avg_volume:
            return False, f"Khối lượng TB 20 phiên ({avg_vol:,.0f}) thấp hơn ngưỡng ({min_avg_volume:,.0f})"
        if avg_val < min_avg_value:
            return False, f"Giá trị TB 20 phiên ({avg_val:,.0f} VND) thấp hơn ngưỡng ({min_avg_value:,.0f} VND)"

        return True, "Thỏa mãn tiêu chuẩn thanh khoản"
