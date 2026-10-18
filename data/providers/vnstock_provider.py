import datetime
import time
import requests
import pandas as pd
from typing import List, Dict, Any, Optional
from data.providers.base import BaseDataProvider
from universe.stock_universe import StockUniverse


class VnstockProvider(BaseDataProvider):
    """
    Data provider connecting directly to public Vietnam Stock Market chart endpoints:
    - Primary: VNDirect DChart API (HOSE, HNX, UPCoM + VNINDEX, VN30, HNX, UPCOM)
    - Fallback: DNSE Entrade Chart API v2
    Provides official OHLCV daily bars with 100% Vietnamese market coverage.
    """

    VNDIRECT_URL = "https://dchart-api.vndirect.com.vn/dchart/history"
    DNSE_URL = "https://services.entrade.com.vn/chart-api/v2/ohlcs/stock"

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
    }

    def __init__(self, universe: Optional[StockUniverse] = None):
        self.universe = universe or StockUniverse()
        self.last_timestamp = ""

    def get_stock_universe(self) -> List[Dict[str, Any]]:
        return self.universe.stocks

    def _date_to_timestamp(self, date_str: str, default_ts: int) -> int:
        if not date_str:
            return default_ts
        try:
            dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            return int(dt.timestamp())
        except Exception:
            return default_ts

    def _fetch_vndirect(self, symbol: str, from_ts: int, to_ts: int) -> pd.DataFrame:
        url = f"{self.VNDIRECT_URL}?resolution=D&symbol={symbol}&from={from_ts}&to={to_ts}"
        resp = requests.get(url, headers=self.HEADERS, timeout=10)
        if resp.status_code != 200:
            return pd.DataFrame()
        data = resp.json()
        timestamps = data.get("t", [])
        if not timestamps:
            return pd.DataFrame()

        df = pd.DataFrame({
            "timestamp": timestamps,
            "open": data.get("o", []),
            "high": data.get("h", []),
            "low": data.get("l", []),
            "close": data.get("c", []),
            "volume": data.get("v", [])
        })

        # VNDirect prices for stocks are in 1,000 VND (e.g. 104.11 = 104,110 VND)
        # For indices (VNINDEX, VN30, HNX, UPCOM) close is index point (e.g. 1280.5)
        # Standardize stock prices to full VND if <= 1000 and symbol is not an index
        is_index = symbol.upper() in ["VNINDEX", "VN30", "HNX", "UPCOM", "HNXINDEX", "UPINDEX"]
        if not is_index:
            mean_close = df["close"].mean()
            if mean_close < 1000:
                for col in ["open", "high", "low", "close"]:
                    df[col] = df[col] * 1000.0

        df["date"] = pd.to_datetime(df["timestamp"], unit="s").dt.strftime("%Y-%m-%d")
        df["trading_value"] = df["close"] * df["volume"]
        return df[["date", "open", "high", "low", "close", "volume", "trading_value"]]

    def _fetch_dnse(self, symbol: str, from_ts: int, to_ts: int) -> pd.DataFrame:
        url = f"{self.DNSE_URL}?from={from_ts}&to={to_ts}&symbol={symbol}&resolution=1D"
        resp = requests.get(url, headers=self.HEADERS, timeout=10)
        if resp.status_code != 200:
            return pd.DataFrame()
        data = resp.json()
        timestamps = data.get("t", [])
        if not timestamps:
            return pd.DataFrame()

        df = pd.DataFrame({
            "timestamp": timestamps,
            "open": data.get("o", []),
            "high": data.get("h", []),
            "low": data.get("l", []),
            "close": data.get("c", []),
            "volume": data.get("v", [])
        })

        mean_close = df["close"].mean()
        if mean_close < 1000:
            for col in ["open", "high", "low", "close"]:
                df[col] = df[col] * 1000.0

        df["date"] = pd.to_datetime(df["timestamp"], unit="s").dt.strftime("%Y-%m-%d")
        df["trading_value"] = df["close"] * df["volume"]
        return df[["date", "open", "high", "low", "close", "volume", "trading_value"]]

    def get_historical_prices(self, symbol: str, start_date: str = "", end_date: str = "") -> pd.DataFrame:
        clean_symbol = symbol.strip().upper()
        now_ts = int(time.time())
        two_years_ago_ts = now_ts - (730 * 86400)

        from_ts = self._date_to_timestamp(start_date, two_years_ago_ts)
        to_ts = self._date_to_timestamp(end_date, now_ts)

        empty_df = pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume", "trading_value"])

        # Try Primary: VNDirect
        try:
            df = self._fetch_vndirect(clean_symbol, from_ts, to_ts)
            if not df.empty and len(df) >= 5:
                self.last_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                return df.sort_values("date").reset_index(drop=True)
        except Exception as e:
            print(f"[VnstockProvider] VNDirect error for {clean_symbol}: {e}")

        # Try Fallback: DNSE
        try:
            df = self._fetch_dnse(clean_symbol, from_ts, to_ts)
            if not df.empty and len(df) >= 5:
                self.last_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                return df.sort_values("date").reset_index(drop=True)
        except Exception as e:
            print(f"[VnstockProvider] DNSE error for {clean_symbol}: {e}")

        return empty_df

    def get_market_index_data(self, index_symbol: str = "VNINDEX", start_date: str = "", end_date: str = "") -> pd.DataFrame:
        """
        Fetches official index history: VNINDEX, VN30, HNX, UPCOM.
        Does NOT synthesize from a few stocks.
        """
        clean_symbol = index_symbol.strip().upper()
        # Normalization mapping
        mapping = {
            "VNINDEX": "VNINDEX",
            "^VNINDEX": "VNINDEX",
            "VN-INDEX": "VNINDEX",
            "HNXINDEX": "HNX",
            "HNX": "HNX",
            "UPINDEX": "UPCOM",
            "UPCOM": "UPCOM",
            "VN30": "VN30",
        }
        symbol_mapped = mapping.get(clean_symbol, clean_symbol)

        now_ts = int(time.time())
        two_years_ago_ts = now_ts - (730 * 86400)
        from_ts = self._date_to_timestamp(start_date, two_years_ago_ts)
        to_ts = self._date_to_timestamp(end_date, now_ts)

        try:
            df = self._fetch_vndirect(symbol_mapped, from_ts, to_ts)
            if not df.empty:
                self.last_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                return df.sort_values("date").reset_index(drop=True)
        except Exception as e:
            print(f"[VnstockProvider] Error fetching market index {index_symbol}: {e}")

        return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume", "trading_value"])

    def get_sector_information(self) -> Dict[str, List[str]]:
        sectors = {}
        for item in self.universe.stocks:
            sec = item.get("sector", "Other")
            sectors.setdefault(sec, []).append(item["symbol"])
        return sectors

    def get_corporate_actions(self, symbol: str) -> pd.DataFrame:
        return pd.DataFrame(columns=["date", "action_type", "value"])

    def get_data_timestamp(self) -> str:
        return self.last_timestamp or datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
