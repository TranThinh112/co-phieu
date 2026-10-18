import pytest
from features.news_sentiment import NewsAnalyzer
from scanner.trade_plan import TradePlanEngine

def test_news_analyzer_bidding_and_contracts():
    title = "Tổng công ty xây dựng trúng thầu gói thầu hạ tầng cao tốc Bắc Nam giá trị 3500 tỷ"
    summary = "Lễ ký kết hợp đồng và khởi công dự án đã được thực hiện."
    res = NewsAnalyzer.analyze_article(title, summary)
    assert res["sentiment"] == "BULLISH"
    assert "Trúng Thầu / Dự Án Mới" in res["positive_catalysts"]
    assert res["score"] >= 8.0

def test_news_analyzer_dividend_and_branch():
    title = "Ngân hàng thương mại mở thêm chi nhánh mới tại Đà Nẵng, đồng thời chi trả cổ tức tiền mặt 15%"
    res = NewsAnalyzer.analyze_article(title, "")
    assert "Chia Cổ Tức Khủng / Thưởng" in res["positive_catalysts"]
    assert "Mở Rộng Quy Mô / Chi Nhánh" in res["positive_catalysts"]
    assert res["score"] >= 10.0

def test_news_analyzer_fatal_negative_warning():
    title = "Cựu lãnh đạo doanh nghiệp bị khởi tố và tạm hoãn xuất cảnh vì vi phạm pháp luật"
    res = NewsAnalyzer.analyze_article(title, "")
    assert res["sentiment"] == "BEARISH"
    assert res["is_severe_negative"] is True
    assert "Rủi Ro Pháp Lý / Bị Xử Phạt / Điều Tra" in res["negative_catalysts"]

def test_trade_plan_vetoes_fatal_news():
    config = {
        "risk": {"risk_per_trade_pct": 0.005, "max_position_pct": 0.15, "minimum_order_value_vnd": 1_000_000, "board_lot_size": 100, "max_open_positions": 5},
        "trade_plan": {"holding_period_sessions": 10, "min_rule_score": 70, "min_market_regime": "Sideways", "atr_stop_multiple": 2.0, "structural_stop_buffer_pct": 0.02, "target_one_r_multiple": 2.0, "target_two_r_multiple": 3.0, "scale_out_at_target_one_pct": 0.5, "trailing_stop_atr_multiple": 2.0, "reject_rsi_above": 75, "reject_high_risk": True},
    }
    engine = TradePlanEngine(config)
    result = {
        "symbol": "ABC", "close_price": 50_000, "rule_score": 85, "rsi": 55, "risk_level": "Low",
        "has_fatal_news": True, "negative_warnings": ["Rủi Ro Pháp Lý / Bị Xử Phạt / Điều Tra"]
    }
    row = {"atr_14": 1_000, "sma_20": 48_000, "low": 49_000}
    plan = engine.build_plan(result, row, "Sideways", 100_000_000, 90_000_000, 0)
    assert plan["decision"] == "DO_NOT_BUY"
    assert "PHÁP LÝ" in plan["reason"]

def test_trade_plan_rejects_buy_the_rumor_sell_the_news():
    config = {
        "risk": {"risk_per_trade_pct": 0.005, "max_position_pct": 0.15, "minimum_order_value_vnd": 1_000_000, "board_lot_size": 100, "max_open_positions": 5},
        "trade_plan": {"holding_period_sessions": 10, "min_rule_score": 70, "min_market_regime": "Sideways", "atr_stop_multiple": 2.0, "structural_stop_buffer_pct": 0.02, "target_one_r_multiple": 2.0, "target_two_r_multiple": 3.0, "scale_out_at_target_one_pct": 0.5, "trailing_stop_atr_multiple": 2.0, "reject_rsi_above": 75, "reject_high_risk": True},
    }
    engine = TradePlanEngine(config)
    # Good news (trúng thầu) but RSI is already 73 (overheated)
    result = {
        "symbol": "XYZ", "close_price": 50_000, "rule_score": 85, "rsi": 73, "risk_level": "Medium",
        "has_fatal_news": False, "detected_catalysts": ["Trúng Thầu / Dự Án Mới"]
    }
    row = {"atr_14": 1_000, "sma_20": 48_000, "low": 49_000}
    plan = engine.build_plan(result, row, "Sideways", 100_000_000, 90_000_000, 0)
    assert plan["decision"] == "DO_NOT_BUY"
    assert "Tin ra là bán" in plan["reason"]
