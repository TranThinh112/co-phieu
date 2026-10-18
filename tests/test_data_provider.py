import pytest
import pandas as pd
from data.providers.synthetic_provider import SyntheticDataProvider
from data.downloader import DataDownloader
from data.validator import DataValidator

def test_synthetic_provider():
    provider = SyntheticDataProvider()
    assert provider.is_synthetic is True
    df = provider.get_historical_prices("FPT")
    assert not df.empty
    assert "close" in df.columns
    assert "trading_value" in df.columns
    assert len(df) > 50

def test_data_validator():
    provider = SyntheticDataProvider()
    df = provider.get_historical_prices("HPG")
    is_valid, errors = DataValidator.validate_price_data(df, "HPG")
    assert is_valid is True

    clean_df = DataValidator.clean_price_data(df)
    assert not clean_df.empty
    assert clean_df['high'].max() >= clean_df['close'].max()

def test_downloader():
    dl = DataDownloader(provider=SyntheticDataProvider(), use_cache=False)
    df, warnings = dl.fetch_symbol_data("VNM")
    assert not df.empty
    assert len(df) > 50
