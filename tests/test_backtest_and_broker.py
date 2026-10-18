import pytest
import pandas as pd
from data.providers.synthetic_provider import SyntheticDataProvider
from data.downloader import DataDownloader
from backtest.engine import BacktestEngine
from broker.paper import PaperBroker
from broker.vndirect import VNDirectAdapter

def test_backtest_engine():
    dl = DataDownloader(provider=SyntheticDataProvider(), use_cache=False)
    stock_dfs = dl.fetch_universe_data(symbols=["FPT", "HPG", "VNM"])
    idx_df = dl.fetch_market_index()

    engine = BacktestEngine(initial_capital=50000000.0)
    res = engine.run_backtest(stock_dfs, idx_df, holding_period=5, score_threshold=40.0)
    assert "metrics" in res
    assert "total_return_pct" in res["metrics"]
    assert "cagr_pct" in res["metrics"]

def test_paper_broker():
    broker = PaperBroker()
    bal_initial = broker.get_account_balance()
    assert bal_initial["mode"] == "PAPER"

    order_res = broker.place_order(symbol="FPT", side="BUY", quantity=100, price=100000.0)
    assert order_res["status"] == "FILLED"
    assert order_res["order_id"].startswith("PAPER_")

    positions = broker.get_positions()
    assert len(positions) > 0

def test_vndirect_placeholder():
    vnd = VNDirectAdapter()
    assert vnd.is_paper_trading is True
    bal = vnd.get_account_balance()
    assert "note" in bal
