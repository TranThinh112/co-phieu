import time
from typing import Dict, List, Optional, Tuple
import pandas as pd

from data.providers.base import BaseDataProvider
from data.providers.vnstock_provider import VnstockProvider
from data.providers.yfinance_provider import YFinanceProvider
from data.providers.csv_provider import CsvDataProvider
from data.providers.synthetic_provider import SyntheticDataProvider
from data.cache import DataCache
from data.validator import DataValidator
from universe.stock_universe import StockUniverse

class DataDownloader:
    """Downloader component for fetching, validating and caching stock price history."""

    def __init__(self, provider: Optional[BaseDataProvider] = None, use_cache: bool = True):
        self.universe = StockUniverse()
        self.provider = provider or VnstockProvider(self.universe)
        self.use_cache = use_cache
        self.cache = DataCache() if use_cache else None

    def fetch_symbol_data(self, symbol: str, start_date: str = "", end_date: str = "", force_reload: bool = False) -> Tuple[pd.DataFrame, List[str]]:
        symbol = symbol.upper()
        if self.use_cache and not force_reload and self.cache and not self.provider.is_synthetic:
            cached_df = self.cache.get(symbol)
            if cached_df is not None and not cached_df.empty:
                is_valid, warnings = DataValidator.validate_price_data(cached_df, symbol)
                return cached_df, warnings

        raw_df = self.provider.get_historical_prices(symbol, start_date, end_date)
        clean_df = DataValidator.clean_price_data(raw_df)
        is_valid, warnings = DataValidator.validate_price_data(clean_df, symbol)

        if self.use_cache and self.cache and is_valid and not clean_df.empty and not self.provider.is_synthetic:
            self.cache.set(symbol, clean_df)

        return clean_df, warnings

    def fetch_universe_data(self, symbols: Optional[List[str]] = None, start_date: str = "", end_date: str = "", max_workers: int = 8) -> Dict[str, pd.DataFrame]:
        target_symbols = symbols or self.universe.get_all_symbols()
        data_dict = {}

        if getattr(self.provider, "is_synthetic", False) or len(target_symbols) <= 5:
            for sym in target_symbols:
                df, _ = self.fetch_symbol_data(sym, start_date, end_date)
                if not df.empty:
                    data_dict[sym] = df
            return data_dict

        from concurrent.futures import ThreadPoolExecutor

        def _worker(s: str):
            try:
                df, _ = self.fetch_symbol_data(s, start_date, end_date)
                return s, df
            except Exception:
                return s, pd.DataFrame()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for sym, df in executor.map(_worker, target_symbols):
                if not df.empty:
                    data_dict[sym] = df

        return data_dict

    def fetch_market_index(self, index_symbol: str = "VNINDEX", start_date: str = "", end_date: str = "") -> pd.DataFrame:
        df = self.provider.get_market_index_data(index_symbol, start_date, end_date)
        return DataValidator.clean_price_data(df)

