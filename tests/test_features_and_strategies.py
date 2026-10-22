import pytest
import pandas as pd
from data.providers.synthetic_provider import SyntheticDataProvider
from features.technical import TechnicalFeatures
from features.momentum import MomentumFeatures
from features.volatility import VolatilityFeatures
from features.liquidity import LiquidityFeatures
from strategies.trend_following import TrendFollowingStrategy
from strategies.breakout import BreakoutStrategy
from strategies.relative_strength import RelativeStrengthStrategy

def test_feature_engineering():
    provider = SyntheticDataProvider()
    df = provider.get_historical_prices("FPT")

    df = TechnicalFeatures.add_technical_indicators(df)
    df = MomentumFeatures.add_momentum_indicators(df)
    df = VolatilityFeatures.add_volatility_indicators(df)
    df = LiquidityFeatures.add_liquidity_indicators(df)

    assert "sma_20" in df.columns
    assert "rsi_14" in df.columns
    assert "macd_line" in df.columns
    assert "bb_upper" in df.columns
    assert "volume_ratio" in df.columns
    assert not df['sma_20'].isna().all()

def test_strategies():
    provider = SyntheticDataProvider()
    df = provider.get_historical_prices("TCB")
    idx_df = provider.get_market_index_data()

    df = TechnicalFeatures.add_technical_indicators(df)
    df = MomentumFeatures.add_momentum_indicators(df)
    df = LiquidityFeatures.add_liquidity_indicators(df)

    t_info = TrendFollowingStrategy.evaluate_trend(df)
    assert "trend" in t_info
    assert "trend_score" in t_info

    b_info = BreakoutStrategy.evaluate_breakout(df)
    assert "breakout_status" in b_info
    assert "breakout_score" in b_info

    rs_info = RelativeStrengthStrategy.calculate_relative_strength(df, idx_df)
    assert "rs_rating" in rs_info

def test_candlestick_patterns():
    from features.candlestick import CandlestickAnalyzer

    # Test Marubozu
    df_maru = pd.DataFrame({
        "open": [10.0, 10.2, 10.0],
        "high": [10.3, 10.5, 11.0],
        "low": [9.9, 10.0, 9.98],
        "close": [10.2, 10.4, 10.98]
    })
    res_maru = CandlestickAnalyzer.analyze_patterns(df_maru)
    assert res_maru["sentiment"] == "BULLISH"
    assert "Marubozu" in res_maru["pattern_name"]
    assert res_maru["score_adjustment"] > 0

    # Test Shooting Star
    df_star = pd.DataFrame({
        "open": [10.0, 10.2, 10.5],
        "high": [10.3, 10.5, 11.5],
        "low": [9.9, 10.0, 10.45],
        "close": [10.2, 10.5, 10.52]
    })
    res_star = CandlestickAnalyzer.analyze_patterns(df_star)
    assert res_star["sentiment"] == "BEARISH"
    assert "Bắn Sao" in res_star["pattern_name"] or "Shooting Star" in res_star["pattern_name"]
    assert res_star["score_adjustment"] < 0
