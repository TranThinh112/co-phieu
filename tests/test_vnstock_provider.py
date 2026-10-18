import pytest
import pandas as pd
from data.providers.vnstock_provider import VnstockProvider

def test_vnstock_provider_stocks():
    p = VnstockProvider()
    assert p.is_synthetic is False
    df = p.get_historical_prices("FPT")
    assert not df.empty
    assert "close" in df.columns
    assert "volume" in df.columns
    assert len(df) >= 100
    # Price must be in full VND (> 1000)
    assert df["close"].iloc[-1] > 1000

def test_vnstock_provider_hnx_upcom():
    p = VnstockProvider()
    for sym in ["PVS", "ACV"]:
        df = p.get_historical_prices(sym)
        assert not df.empty, f"Failed for {sym}"
        assert len(df) >= 50

def test_vnstock_provider_official_index():
    p = VnstockProvider()
    df = p.get_market_index_data("VNINDEX")
    assert not df.empty
    assert len(df) >= 100
    # VN-Index in 2024-2026 is around 1000-2000 points
    assert 800 < df["close"].iloc[-1] < 3000
