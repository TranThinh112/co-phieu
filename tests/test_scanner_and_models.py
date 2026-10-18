import pytest
import pandas as pd
from data.providers.synthetic_provider import SyntheticDataProvider
from data.downloader import DataDownloader
from scanner.orchestrator import MarketScanner
from models.train import ModelTrainer
from models.predict import ModelPredictor

def test_market_scanner():
    scanner = MarketScanner(provider=SyntheticDataProvider(), use_cache=False)
    results_df, regime_info = scanner.run_market_scan(symbols=["FPT", "HPG", "VNM"])
    assert not results_df.empty
    assert "rule_score" in results_df.columns
    assert "category" in results_df.columns
    assert "regime" in regime_info

def test_ai_model_training_and_prediction():
    dl = DataDownloader(provider=SyntheticDataProvider(), use_cache=False)
    stock_dfs = dl.fetch_universe_data(symbols=["FPT", "HPG", "VNM", "TCB", "SSI"])

    trainer = ModelTrainer()
    train_res = trainer.train_horizon_model(stock_dfs, horizon=5)
    assert train_res["status"] == "success"

    predictor = ModelPredictor()
    probs = predictor.predict_stock_probabilities(stock_dfs["FPT"])
    assert probs["ai_prob_5d"] is not None
    assert 0.0 <= probs["ai_prob_5d"] <= 1.0
