from scanner.trade_plan import TradePlanEngine


def test_trade_plan_respects_position_sizing():
    config = {
        "risk": {"risk_per_trade_pct": 0.005, "max_position_pct": 0.15, "minimum_order_value_vnd": 1_000_000, "board_lot_size": 100, "max_open_positions": 5},
        "trade_plan": {"holding_period_sessions": 10, "min_rule_score": 70, "min_market_regime": "Sideways", "atr_stop_multiple": 2.0, "structural_stop_buffer_pct": 0.02, "target_one_r_multiple": 2.0, "target_two_r_multiple": 3.0, "scale_out_at_target_one_pct": 0.5, "trailing_stop_atr_multiple": 2.0, "reject_rsi_above": 75, "reject_high_risk": True},
    }
    engine = TradePlanEngine(config)
    result = {"symbol": "FPT", "close_price": 100_000, "rule_score": 80, "rsi": 60, "risk_level": "Low"}
    row = {"atr_14": 2_000, "sma_20": 98_500, "low": 99_000}
    plan = engine.build_plan(result, row, "Sideways", 100_000_000, 90_000_000, 0)
    assert plan["decision"] == "BUY_CANDIDATE"
    assert plan["quantity"] % 100 == 0
    assert plan["position_value"] <= 15_000_000
    assert plan["take_profit_2"] > plan["take_profit_1"] > plan["entry_price"] > plan["stop_loss"]


def test_trade_plan_rejects_bearish_market():
    config = {
        "risk": {"risk_per_trade_pct": 0.005, "max_position_pct": 0.15, "minimum_order_value_vnd": 1_000_000, "board_lot_size": 100, "max_open_positions": 5},
        "trade_plan": {"holding_period_sessions": 10, "min_rule_score": 70, "min_market_regime": "Sideways", "atr_stop_multiple": 2.0, "structural_stop_buffer_pct": 0.02, "target_one_r_multiple": 2.0, "target_two_r_multiple": 3.0, "scale_out_at_target_one_pct": 0.5, "trailing_stop_atr_multiple": 2.0, "reject_rsi_above": 75, "reject_high_risk": True},
    }
    plan = TradePlanEngine(config).build_plan({"symbol": "FPT", "close_price": 100_000, "rule_score": 80, "rsi": 60, "risk_level": "Low"}, {"atr_14": 2_000, "sma_20": 98_500, "low": 99_000}, "Bearish (Xu huong Giam gia)", 100_000_000, 90_000_000, 0)
    assert plan["decision"] == "DO_NOT_BUY"
