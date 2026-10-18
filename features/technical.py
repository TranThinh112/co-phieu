import numpy as np
import pandas as pd

class TechnicalFeatures:
    """Calculates technical indicators, moving averages, slopes, ADX and returns."""

    @staticmethod
    def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty or len(df) < 5:
            return df

        df = df.copy()
        close = df['close']
        high = df['high']
        low = df['low']

        # Moving Averages
        df['sma_20'] = close.rolling(window=20, min_periods=5).mean()
        df['sma_50'] = close.rolling(window=50, min_periods=10).mean()
        df['sma_200'] = close.rolling(window=200, min_periods=20).mean()

        df['ema_20'] = close.ewm(span=20, adjust=False).mean()
        df['ema_50'] = close.ewm(span=50, adjust=False).mean()

        # Slopes (% change over 5 sessions)
        df['sma_20_slope'] = (df['sma_20'] - df['sma_20'].shift(5)) / df['sma_20'].shift(5) * 100.0
        df['sma_50_slope'] = (df['sma_50'] - df['sma_50'].shift(5)) / df['sma_50'].shift(5) * 100.0

        # Price Performance (Returns)
        df['ret_5d'] = close.pct_change(5) * 100.0
        df['ret_10d'] = close.pct_change(10) * 100.0
        df['ret_20d'] = close.pct_change(20) * 100.0
        df['ret_60d'] = close.pct_change(60) * 100.0

        # Simple ADX (Average Directional Index) approximation
        df['adx_14'] = TechnicalFeatures.calculate_adx(high, low, close, period=14)

        return df

    @staticmethod
    def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
        tr1 = high - low
        tr2 = (high - close.shift(1)).abs()
        tr3 = (low - close.shift(1)).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period, min_periods=1).mean()

        up_move = high - high.shift(1)
        down_move = low.shift(1) - low

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

        plus_di = 100.0 * (pd.Series(plus_dm, index=high.index).rolling(period, min_periods=1).mean() / atr)
        minus_di = 100.0 * (pd.Series(minus_dm, index=high.index).rolling(period, min_periods=1).mean() / atr)

        dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, 1.0)
        adx = dx.rolling(period, min_periods=1).mean()
        return adx
