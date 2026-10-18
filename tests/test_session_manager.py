import datetime
from automation.session_manager import MarketSessionManager, is_market_open_now, get_market_session_status


def test_market_session_weekend_self_learning():
    sat = datetime.datetime(2026, 10, 24, 10, 0)
    info = MarketSessionManager.get_session_info(sat)
    assert info["is_trading_hour"] is False
    assert info["should_poll_api"] is False
    assert info["session_code"] == "WEEKEND_SELF_LEARNING"
    assert info["is_learning_active"] is True
    assert "🧠 CUỐI TUẦN" in info["badge_label"]
    assert info["learning_details"] is not None
    assert info["learning_details"]["active"] is True


def test_market_session_morning():
    mon_morning = datetime.datetime(2026, 10, 19, 10, 15)
    info = MarketSessionManager.get_session_info(mon_morning)
    assert info["is_trading_hour"] is True
    assert info["should_poll_api"] is True
    assert info["session_code"] == "MORNING_SESSION"


def test_market_session_lunch():
    mon_lunch = datetime.datetime(2026, 10, 19, 12, 15)
    info = MarketSessionManager.get_session_info(mon_lunch)
    assert info["is_trading_hour"] is False
    assert info["should_poll_api"] is False
    assert info["session_code"] == "LUNCH_BREAK"


def test_market_session_afternoon():
    mon_afternoon = datetime.datetime(2026, 10, 19, 14, 0)
    info = MarketSessionManager.get_session_info(mon_afternoon)
    assert info["is_trading_hour"] is True
    assert info["should_poll_api"] is True
    assert info["session_code"] == "AFTERNOON_SESSION"


def test_market_session_post_market():
    mon_post = datetime.datetime(2026, 10, 19, 15, 30)
    info = MarketSessionManager.get_session_info(mon_post)
    assert info["is_trading_hour"] is False
    assert info["is_post_market"] is True
    assert info["should_poll_api"] is False
    assert info["session_code"] == "POST_MARKET_REVIEW"


def test_market_session_off_hours():
    mon_night = datetime.datetime(2026, 10, 19, 21, 0)
    info = MarketSessionManager.get_session_info(mon_night)
    assert info["is_trading_hour"] is False
    assert info["should_poll_api"] is False
    assert info["session_code"] == "OFF_HOURS"
