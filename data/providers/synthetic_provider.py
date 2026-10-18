import datetime
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional
from data.providers.base import BaseDataProvider
from universe.stock_universe import StockUniverse

class SyntheticDataProvider(BaseDataProvider):
    """Synthetic Data Provider ONLY for unit tests and simulation.
    Clearly marked as synthetic."""

    def __init__(self, universe: Optional[StockUniverse] = None, seed: int = 42):
        self.universe = universe or StockUniverse()
        self.seed = seed
        self.last_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @property
    def is_synthetic(self) -> bool:
        return True

    def get_stock_universe(self) -> List[Dict[str, Any]]:
        return self.universe.stocks

    def get_historical_prices(self, symbol: str, start_date: str = "", end_date: str = "") -> pd.DataFrame:
        clean_symbol = symbol.strip().upper()
        np.random.seed(hash(clean_symbol) % 2**32)

        n_days = 250
        end_dt = datetime.date.today()
        dates = [ (end_dt - datetime.timedelta(days=n_days - i)).strftime("%Y-%m-%d") for i in range(n_days) ]

        # Filter weekends
        valid_dates = [d for d in dates if pd.to_datetime(d).weekday() < 5]
        n = len(valid_dates)

        # Baseline stock price based on symbol hash
        base_price = 20.0 + (hash(clean_symbol) % 80)
        daily_returns = np.random.normal(loc=0.0008, scale=0.018, size=n)

        prices = [base_price]
        for r in daily_returns[1:]:
            prices.append(max(1.0, prices[-1] * (1.0 + r)))

        prices = np.array(prices)
        highs = prices * (1.0 + np.abs(np.random.normal(0.005, 0.005, size=n)))
        lows = prices * (1.0 - np.abs(np.random.normal(0.005, 0.005, size=n)))
        opens = lows + (highs - lows) * np.random.uniform(0.1, 0.9, size=n)
        closes = prices

        volumes = np.random.randint(100000, 2000000, size=n)
        trading_values = closes * volumes

        df = pd.DataFrame({
            'date': valid_dates,
            'open': opens.round(2),
            'high': highs.round(2),
            'low': lows.round(2),
            'close': closes.round(2),
            'volume': volumes,
            'trading_value': trading_values.round(2)
        })

        if start_date:
            df = df[df['date'] >= start_date]
        if end_date:
            df = df[df['date'] <= end_date]

        return df.reset_index(drop=True)

    def get_market_index_data(self, index_symbol: str = "VNINDEX", start_date: str = "", end_date: str = "") -> pd.DataFrame:
        return self.get_historical_prices("VNINDEX", start_date, end_date)

    def get_sector_information(self) -> Dict[str, List[str]]:
        sectors = {}
        for item in self.universe.stocks:
            sec = item.get("sector", "Other")
            sectors.setdefault(sec, []).append(item["symbol"])
        return sectors

    def get_corporate_actions(self, symbol: str) -> pd.DataFrame:
        return pd.DataFrame(columns=['date', 'action_type', 'value'])

    def get_data_timestamp(self) -> str:
        return f"{self.last_timestamp} [SYNTHETIC DATA - TEST ONLY]"
