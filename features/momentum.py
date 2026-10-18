import numpy as np
import pandas as pd

class MomentumFeatures:
    """Calculates RSI, MACD, and Rate of Change (ROC)."""

    @staticmethod
    def add_momentum_indicators(df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty or len(df) < 5:
            return df

        df = df.copy()
        close = df['close']

        # RSI 14
        df['rsi_14'] = MomentumFeatures.calculate_rsi(close, period=14)

        # MACD (12, 26, 9)
        ema_fast = close.ewm(span=12, adjust=False).mean()
        ema_slow = close.ewm(span=26, adjust=False).mean()
        df['macd_line'] = ema_fast - ema_slow
        df['macd_signal'] = df['macd_line'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd_line'] - df['macd_signal']

        # ROC 12
        df['roc_12'] = (close - close.shift(12)) / close.shift(12) * 100.0

        return df

    @staticmethod
    def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period, min_periods=1).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period, min_periods=1).mean()

        rs = gain / loss.replace(0, 1e-9)
        rsi = 100.0 - (100.0 / (1.0 + rs))
        return rsi.fillna(50.0)
