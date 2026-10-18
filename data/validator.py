import datetime
import pandas as pd
from typing import Dict, Any, List, Tuple

class DataValidator:
    """Validates raw stock price data and reports data quality issues."""

    REQUIRED_COLUMNS = ['date', 'open', 'high', 'low', 'close', 'volume']

    @classmethod
    def validate_price_data(cls, df: pd.DataFrame, symbol: str = "") -> Tuple[bool, List[str]]:
        errors = []

        if df is None or df.empty:
            return False, [f"Symbol {symbol}: Dataframe is empty or None."]

        missing_cols = [c for c in cls.REQUIRED_COLUMNS if c not in df.columns]
        if missing_cols:
            return False, [f"Symbol {symbol}: Missing required columns: {missing_cols}"]

        # Check duplicate dates
        dup_count = df['date'].duplicated().sum()
        if dup_count > 0:
            errors.append(f"Symbol {symbol}: Found {dup_count} duplicate dates.")

        # Check NaNs
        nan_cols = df[cls.REQUIRED_COLUMNS].isna().sum()
        if nan_cols.sum() > 0:
            bad = nan_cols[nan_cols > 0].to_dict()
            errors.append(f"Symbol {symbol}: Found missing values in columns: {bad}")

        # Check positive prices
        non_positive = (df[['open', 'high', 'low', 'close']] <= 0).sum().sum()
        if non_positive > 0:
            errors.append(f"Symbol {symbol}: Found {non_positive} zero or negative prices.")

        # Check high/low integrity
        bad_high = (df['high'] < df[['open', 'close']].max(axis=1)).sum()
        bad_low = (df['low'] > df[['open', 'close']].min(axis=1)).sum()
        if bad_high > 0 or bad_low > 0:
            errors.append(f"Symbol {symbol}: Found price anomalies (high < max(O,C) or low > min(O,C)).")

        # Check data freshness
        try:
            last_date_str = str(df['date'].iloc[-1])
            last_dt = pd.to_datetime(last_date_str).date()
            today = datetime.date.today()
            days_diff = (today - last_dt).days
            if days_diff > 5:
                errors.append(f"Symbol {symbol}: Data is stale (last update: {last_date_str}, {days_diff} days ago).")
        except Exception as e:
            errors.append(f"Symbol {symbol}: Could not parse last date for staleness check: {e}")

        is_valid = (len(errors) == 0 or (len(errors) == 1 and "stale" in errors[0]))
        return is_valid, errors

    @classmethod
    def clean_price_data(cls, df: pd.DataFrame) -> pd.DataFrame:
        """Cleans and fixes minor price data issues."""
        if df is None or df.empty:
            return pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume', 'trading_value'])

        df = df.copy()
        df.drop_duplicates(subset=['date'], keep='last', inplace=True)
        df.sort_values('date', inplace=True)

        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        df.dropna(subset=['close'], inplace=True)
        df['open'] = df['open'].fillna(df['close'])
        df['high'] = df['high'].fillna(df[['open', 'close']].max(axis=1))
        df['low'] = df['low'].fillna(df[['open', 'close']].min(axis=1))
        df['volume'] = df['volume'].fillna(0)

        # Fix high/low bounds
        df['high'] = df[['high', 'open', 'close']].max(axis=1)
        df['low'] = df[['low', 'open', 'close']].min(axis=1)

        if 'trading_value' not in df.columns:
            df['trading_value'] = df['close'] * df['volume']
        else:
            df['trading_value'] = df['trading_value'].fillna(df['close'] * df['volume'])

        return df.reset_index(drop=True)
