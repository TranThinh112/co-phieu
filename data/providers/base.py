from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import pandas as pd

class BaseDataProvider(ABC):
    """Abstract Base Class for Stock Data Providers."""

    @abstractmethod
    def get_stock_universe(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_historical_prices(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        pass

    @abstractmethod
    def get_market_index_data(self, index_symbol: str = "VNINDEX", start_date: str = "", end_date: str = "") -> pd.DataFrame:
        pass

    @abstractmethod
    def get_sector_information(self) -> Dict[str, List[str]]:
        pass

    @abstractmethod
    def get_corporate_actions(self, symbol: str) -> pd.DataFrame:
        pass

    @abstractmethod
    def get_data_timestamp(self) -> str:
        pass

    @property
    def is_synthetic(self) -> bool:
        return False
