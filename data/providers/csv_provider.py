import os
import datetime
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional
from data.providers.base import BaseDataProvider
from universe.stock_universe import StockUniverse

class CsvDataProvider(BaseDataProvider):
    """Data provider reading historical price data from CSV files."""

    def __init__(self, csv_dir: str = "data/csv_storage", universe: Optional[StockUniverse] = None):
        self.csv_dir = Path(csv_dir)
        self.csv_dir.mkdir(parents=True, exist_ok=True)
        self.universe = universe or StockUniverse()
        self.last_timestamp = ""

    def get_stock_universe(self) -> List[Dict[str, Any]]:
        return self.universe.stocks

    def get_historical_prices(self, symbol: str, start_date: str = "", end_date: str = "") -> pd.DataFrame:
        clean_symbol = symbol.strip().upper()
        filepath = self.csv_dir / f"{clean_symbol}.csv"

        if not filepath.exists():
            return pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume', 'trading_value'])

        try:
            df = pd.read_csv(filepath)
            df.columns = [c.strip().lower() for c in df.columns]

            col_map = {'time': 'date', 'ticker': 'symbol'}
            df = df.rename(columns=col_map)

            required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
            for col in required_cols:
                if col not in df.columns:
                    return pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume', 'trading_value'])

            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            df.dropna(subset=['close'], inplace=True)
            if 'trading_value' not in df.columns:
                df['trading_value'] = df['close'] * df['volume']
            else:
                df['trading_value'] = pd.to_numeric(df['trading_value'], errors='coerce').fillna(df['close'] * df['volume'])

            df = df.sort_values('date').reset_index(drop=True)

            if start_date:
                df = df[df['date'] >= start_date]
            if end_date:
                df = df[df['date'] <= end_date]

            self.last_timestamp = datetime.datetime.fromtimestamp(filepath.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            return df.reset_index(drop=True)
        except Exception as e:
            print(f"[CsvDataProvider] Error reading {filepath}: {e}")
            return pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume', 'trading_value'])

    def get_market_index_data(self, index_symbol: str = "VNINDEX", start_date: str = "", end_date: str = "") -> pd.DataFrame:
        idx_df = self.get_historical_prices(index_symbol, start_date, end_date)
        if not idx_df.empty:
            return idx_df

        # Fallback to computing average of available stocks
        all_syms = self.universe.get_all_symbols()[:10]
        dfs = []
        for sym in all_syms:
            df = self.get_historical_prices(sym, start_date, end_date)
            if not df.empty:
                df = df.set_index('date')[['close']].rename(columns={'close': sym})
                dfs.append(df)

        if not dfs:
            return pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume', 'trading_value'])

        combined = pd.concat(dfs, axis=1).dropna()
        if combined.empty:
            return pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume', 'trading_value'])

        returns = combined.pct_change().mean(axis=1).fillna(0)
        index_vals = [1000.0]
        for r in returns.iloc[1:]:
            index_vals.append(index_vals[-1] * (1.0 + r))

        res_df = pd.DataFrame({
            'date': combined.index,
            'open': index_vals,
            'high': index_vals,
            'low': index_vals,
            'close': index_vals,
            'volume': 100000000,
            'trading_value': 10000000000
        })
        return res_df

    def get_sector_information(self) -> Dict[str, List[str]]:
        sectors = {}
        for item in self.universe.stocks:
            sec = item.get("sector", "Other")
            sectors.setdefault(sec, []).append(item["symbol"])
        return sectors

    def get_corporate_actions(self, symbol: str) -> pd.DataFrame:
        return pd.DataFrame(columns=['date', 'action_type', 'value'])

    def get_data_timestamp(self) -> str:
        return self.last_timestamp or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
