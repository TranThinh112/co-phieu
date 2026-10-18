import tempfile
import pytest
import gc
from pathlib import Path
from learning.tracker import RecommendationTracker
from learning.feedback_loop import SelfLearningEngine
from strategies.exit_strategy import ExitAdvisor
from features.limit_price import LimitPricePredictor


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    gc.collect()
    try:
        Path(db_path).unlink(missing_ok=True)
    except Exception:
        pass


def test_tracker_enroll_and_tp_win(temp_db):
    tracker = RecommendationTracker(db_path=temp_db)
    
    enrolled = tracker.enroll_candidate(
        symbol="VPB",
        entry_price=50000.0,
        rule_score=85.0,
        positive_factors=["Sự kiện trúng thầu dự án", "Mạnh hơn VN-Index"],
        catalysts=["TRUNG_THAU"]
    )
    assert enrolled is True

    active = tracker.get_active_recommendations()
    assert len(active) == 1
    assert active.iloc[0]["symbol"] == "VPB"

    tracker.update_daily_tracking({"VPB": 55000.0})

    active_after = tracker.get_active_recommendations()
    assert len(active_after) == 0

    completed = tracker.get_completed_recommendations()
    assert len(completed) == 1
    rec = completed.iloc[0]
    assert rec["symbol"] == "VPB"
    assert rec["outcome"] == "THANG_DAT_TP1"
    assert rec["return_pct"] >= 8.0
    assert "THẮNG" in rec["post_mortem_reason"]


def test_tracker_sl_loss(temp_db):
    tracker = RecommendationTracker(db_path=temp_db)
    
    tracker.enroll_candidate(
        symbol="MSN",
        entry_price=100000.0,
        rule_score=68.0,
        positive_factors=["Hồi phục kỹ thuật"]
    )
    tracker.update_daily_tracking({"MSN": 94000.0})

    completed = tracker.get_completed_recommendations()
    assert len(completed) == 1
    rec = completed.iloc[0]
    assert rec["symbol"] == "MSN"
    assert rec["outcome"] == "THUA_DUNG_SL"
    assert "DỪNG LỖ" in rec["post_mortem_reason"]


def test_self_learning_metrics(temp_db):
    tracker = RecommendationTracker(db_path=temp_db)
    tracker.seed_initial_knowledge()

    engine = SelfLearningEngine(db_path=temp_db)
    metrics = engine.compute_performance_metrics()
    assert metrics["total_closed_trades"] >= 4
    assert metrics["win_rate_pct"] > 0
    assert metrics["profit_factor"] > 0

    factors = engine.analyze_factors_effectiveness()
    assert len(factors) > 0
    insights = engine.get_actionable_insights()
    assert len(insights) >= 3


def test_exit_advisor_scenarios():
    sl = ExitAdvisor.evaluate_exit("MSN", 100000.0, 94000.0)
    assert sl["action"] == "STOP_LOSS"
    assert "CẮT LỖ" in sl["action_label"]

    tp1 = ExitAdvisor.evaluate_exit("VPB", 20000.0, 21800.0)
    assert tp1["action"] == "TAKE_PROFIT_HALF"
    assert "50%" in tp1["action_label"]

    tp2 = ExitAdvisor.evaluate_exit("GMD", 50000.0, 58000.0)
    assert tp2["action"] == "TAKE_PROFIT_ALL"
    assert "100%" in tp2["action_label"]

    rsi_res = ExitAdvisor.evaluate_exit("FRT", 100000.0, 107000.0, rsi=78.0)
    assert rsi_res["action"] == "TECHNICAL_PROFIT"

    tr = ExitAdvisor.evaluate_exit("TCB", 30000.0, 31500.0)
    assert tr["action"] == "TRAILING_STOP"

    hd = ExitAdvisor.evaluate_exit("HPG", 25000.0, 25300.0)
    assert hd["action"] == "HOLD"


def test_limit_price_calculations_and_prediction():
    # 1. HOSE calculation
    ref, ceil, floor = LimitPricePredictor.calculate_limits(24500.0, "HOSE")
    assert ceil == 26200.0
    assert floor == 22800.0

    # 2. UPCoM calculation
    ref, ceil, floor = LimitPricePredictor.calculate_limits(41400.0, "UPCoM")
    assert ceil == 47600.0
    assert floor == 35200.0

    # 3. High ceiling momentum prediction
    pred_up = LimitPricePredictor.evaluate_momentum({
        "symbol": "ACV", "exchange": "UPCoM", "close_price": 41400.0,
        "price_change": 0.98, "volume_ratio": 3.5, "rsi": 62.0, "rule_score": 78.0,
        "detected_catalysts": ["Trúng thầu dự án"]
    })
    assert pred_up["ceiling_price"] == 47600.0
    assert pred_up["floor_price"] == 35200.0
    assert "tăng" in pred_up["next_session_prediction"].lower()

    # 4. Floor risk prediction
    pred_down = LimitPricePredictor.evaluate_momentum({
        "symbol": "XYZ", "exchange": "HOSE", "close_price": 15000.0,
        "price_change": -6.5, "volume_ratio": 2.0, "rsi": 25.0, "rule_score": 30.0,
        "has_fatal_news": True, "negative_warnings": ["Khởi tố lãnh đạo"]
    })
    assert "sàn" in pred_down["next_session_prediction"].lower()
