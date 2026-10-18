import datetime
import pandas as pd
import yfinance as yf
from typing import List, Dict, Any, Optional
from data.providers.base import BaseDataProvider
from universe.stock_universe import StockUniverse

class YFinanceProvider(BaseDataProvider):
    """Data provider using Yahoo Finance for Vietnamese stocks (.VN)."""

    def __init__(self, universe: Optional[StockUniverse] = None):
        self.universe = universe or StockUniverse()
        self.last_timestamp = ""

    def get_stock_universe(self) -> List[Dict[str, Any]]:
        return self.universe.stocks

    def get_historical_prices(self, symbol: str, start_date: str = "", end_date: str = "") -> pd.DataFrame:
        clean_symbol = symbol.strip().upper()
        ticker = clean_symbol if "." in clean_symbol else f"{clean_symbol}.VN"

        if not start_date:
            start_date = (datetime.date.today() - datetime.timedelta(days=730)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.date.today().strftime("%Y-%m-%d")

        try:
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)
            if df.empty:
                return pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume', 'trading_value'])

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df = df.reset_index()

            col_map = {}
            for col in df.columns:
                c_lower = str(col).lower()
                if 'date' in c_lower:
                    col_map[col] = 'date'
                elif 'open' in c_lower:
                    col_map[col] = 'open'
                elif 'high' in c_lower:
                    col_map[col] = 'high'
                elif 'low' in c_lower:
                    col_map[col] = 'low'
                elif 'close' in c_lower:
                    col_map[col] = 'close'
                elif 'volume' in c_lower:
                    col_map[col] = 'volume'

            df = df.rename(columns=col_map)
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            df = df[['date', 'open', 'high', 'low', 'close', 'volume']].copy()

            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            df.dropna(subset=['close'], inplace=True)
            df['trading_value'] = df['close'] * df['volume']

            self.last_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return df.sort_values('date').reset_index(drop=True)
        except Exception as e:
            print(f"[YFinanceProvider] Error fetching {symbol}: {e}")
            return pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume', 'trading_value'])

    def get_market_index_data(self, index_symbol: str = "VNINDEX", start_date: str = "", end_date: str = "") -> pd.DataFrame:
        top_symbols = ["FPT", "HPG", "VNM", "VHM", "TCB", "SSI", "MBB", "MSN"]
        dfs = []
        for sym in top_symbols:
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

        idx_df = pd.DataFrame({
            'date': combined.index,
            'open': index_vals,
            'high': index_vals,
            'low': index_vals,
            'close': index_vals,
            'volume': 100000000,
            'trading_value': 10000000000
        })
        return idx_df

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
