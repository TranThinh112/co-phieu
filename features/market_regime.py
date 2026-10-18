import pandas as pd
from typing import Dict, Any, List

class MarketRegime:
    """Analyzes market index trends and market breadth across universe."""

    @staticmethod
    def analyze_market_regime(index_df: pd.DataFrame, stock_dfs: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        regime_info = {
            "regime": "Sideways (Đi ngang)",
            "index_close": 0.0,
            "index_change_1d": 0.0,
            "pct_above_sma20": 0.0,
            "pct_above_sma50": 0.0,
            "total_stocks_analyzed": len(stock_dfs),
            "timestamp": ""
        }

        if index_df is not None and not index_df.empty:
            idx = index_df.copy()
            idx['sma_20'] = idx['close'].rolling(20, min_periods=5).mean()
            idx['sma_50'] = idx['close'].rolling(50, min_periods=10).mean()

            last = idx.iloc[-1]
            prev = idx.iloc[-2] if len(idx) > 1 else last
            regime_info["index_close"] = float(last['close'])
            regime_info["index_change_1d"] = float((last['close'] - prev['close']) / prev['close'] * 100.0) if prev['close'] > 0 else 0.0
            regime_info["timestamp"] = str(last.get('date', ''))

        # Calculate breadth across stock_dfs
        above_20 = 0
        above_50 = 0
        valid_count = 0

        for sym, df in stock_dfs.items():
            if df is not None and len(df) >= 20:
                c = df['close'].iloc[-1]
                s20 = df['close'].rolling(20, min_periods=5).mean().iloc[-1]
                s50 = df['close'].rolling(50, min_periods=10).mean().iloc[-1] if len(df) >= 50 else s20

                if pd.notna(c) and pd.notna(s20):
                    valid_count += 1
                    if c > s20:
                        above_20 += 1
                    if pd.notna(s50) and c > s50:
                        above_50 += 1

        if valid_count > 0:
            regime_info["pct_above_sma20"] = round((above_20 / valid_count) * 100.0, 1)
            regime_info["pct_above_sma50"] = round((above_50 / valid_count) * 100.0, 1)

        pct20 = regime_info["pct_above_sma20"]
        if pct20 >= 60.0:
            regime_info["regime"] = "Bullish (Xu hướng Tăng mạnh)"
        elif pct20 <= 40.0:
            regime_info["regime"] = "Bearish (Xu hướng Giảm giá)"
        else:
            regime_info["regime"] = "Sideways (Thị trường Tích lũy / Đi ngang)"

        return regime_info
