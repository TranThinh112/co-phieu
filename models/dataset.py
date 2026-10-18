import numpy as np
import pandas as pd
from typing import List, Tuple, Dict, Any

from features.technical import TechnicalFeatures
from features.momentum import MomentumFeatures
from features.volatility import VolatilityFeatures
from features.liquidity import LiquidityFeatures
from strategies.trend_following import TrendFollowingStrategy

class DatasetBuilder:
    """Constructs tabular ML features and temporal targets for 5D, 10D, 20D horizons."""

    FEATURE_COLS = [
        'sma_20_slope', 'sma_50_slope', 'ret_5d', 'ret_10d', 'ret_20d', 'ret_60d',
        'adx_14', 'rsi_14', 'macd_hist', 'roc_12', 'atr_14', 'bb_bandwidth',
        'volatility_20d', 'volume_ratio'
    ]

    def __init__(self, cost_rate: float = 0.003):
        self.cost_rate = cost_rate # 0.3% total roundtrip transaction costs

    def build_features_for_df(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty or len(df) < 30:
            return pd.DataFrame()

        df = TechnicalFeatures.add_technical_indicators(df)
        df = MomentumFeatures.add_momentum_indicators(df)
        df = VolatilityFeatures.add_volatility_indicators(df)
        df = LiquidityFeatures.add_liquidity_indicators(df)

        return df

    def create_dataset(self, stock_dfs: Dict[str, pd.DataFrame], horizon: int = 10, return_threshold: float = 0.01) -> Tuple[pd.DataFrame, pd.Series]:
        all_features = []
        all_targets = []

        for sym, df in stock_dfs.items():
            if df is None or len(df) < (60 + horizon):
                continue

            full_df = self.build_features_for_df(df)
            if full_df.empty:
                continue

            # Forward return definition:
            # Assume entry at open[t+1] or close[t], exit at close[t+horizon]
            # Forward return = (Close[t+H] - Close[t]) / Close[t] - transaction_cost
            close_s = full_df['close']
            fwd_ret = (close_s.shift(-horizon) - close_s) / close_s - self.cost_rate
            target = (fwd_ret > return_threshold).astype(int)

            # Drop missing values
            data = full_df.copy()
            data['target'] = target
            data['symbol'] = sym

            # Drop rows where target or features are NaN (especially the last 'horizon' rows)
            cols_needed = self.FEATURE_COLS + ['target', 'date', 'symbol']
            cols_present = [c for c in cols_needed if c in data.columns]
            valid_data = data[cols_present].dropna().reset_index(drop=True)

            if not valid_data.empty:
                all_features.append(valid_data)

        if not all_features:
            return pd.DataFrame(), pd.Series(dtype=int)

        combined = pd.concat(all_features, ignore_index=True)
        combined.sort_values('date', inplace=True)
        combined.reset_index(drop=True, inplace=True)

        X = combined[self.FEATURE_COLS]
        y = combined['target']
        return X, y

    @staticmethod
    def time_series_split(X: pd.DataFrame, y: pd.Series, test_ratio: float = 0.2, purge_window: int = 10) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series]:
        n = len(X)
        if n < 50:
            return X, y, pd.DataFrame(), pd.Series(dtype=int)

        split_idx = int(n * (1.0 - test_ratio))

        # Train set: 0 to split_idx - purge_window
        train_end = max(10, split_idx - purge_window)
        X_train, y_train = X.iloc[:train_end], y.iloc[:train_end]

        # Test set: split_idx to end
        X_test, y_test = X.iloc[split_idx:], y.iloc[split_idx:]

        return X_train, y_train, X_test, y_test
