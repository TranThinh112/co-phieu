import numpy as np
import pandas as pd

class VolatilityFeatures:
    """Calculates ATR, Bollinger Bands, and Historical Volatility."""

    @staticmethod
    def add_volatility_indicators(df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty or len(df) < 5:
            return df

        df = df.copy()
        close = df['close']
        high = df['high']
        low = df['low']

        # ATR 14
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['atr_14'] = tr.rolling(window=14, min_periods=1).mean()

        # Bollinger Bands (20, 2)
        bb_mid = close.rolling(window=20, min_periods=5).mean()
        bb_std = close.rolling(window=20, min_periods=5).std()
        df['bb_upper'] = bb_mid + 2.0 * bb_std
        df['bb_middle'] = bb_mid
        df['bb_lower'] = bb_mid - 2.0 * bb_std
        df['bb_bandwidth'] = (df['bb_upper'] - df['bb_lower']) / bb_mid.replace(0, 1.0) * 100.0

        # Historical Volatility (20D)
        log_ret = np.log(close / close.shift(1))
        df['volatility_20d'] = log_ret.rolling(window=20, min_periods=5).std() * np.sqrt(252) * 100.0

        return df
