"""Daily post-market review & news-driven recommendation generator."""
import sys
import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

sys.stdout.reconfigure(encoding="utf-8")

from universe.stock_universe import StockUniverse
from data.providers.vnstock_provider import VnstockProvider
from scanner.orchestrator import MarketScanner
from data.storage import StorageEngine
from data.news import NewsProvider
from learning.tracker import RecommendationTracker
from learning.feedback_loop import SelfLearningEngine
from automation.session_manager import MarketSessionManager


def run_daily_post_market_evaluation(force: bool = False) -> dict:
    """Chay danh gia toan bo phien giao dich hom nay va cap nhat de xuat cho phien tiep theo."""
    now_vn = MarketSessionManager.get_vietnam_now()
    session_info = MarketSessionManager.get_session_info(now_vn)
    print(f"[PostMarketReview] Bat dau quy trinh danh gia sau phien luc {now_vn.strftime('%Y-%m-%d %H:%M:%S')} (Gio VN)")
    print(f"[PostMarketReview] Trang thai phien: {session_info['session_name']}")

    universe = StockUniverse()
    storage = StorageEngine()
    provider = VnstockProvider(universe=universe)
    scanner = MarketScanner(provider=provider)
    news_provider = NewsProvider(storage=storage)
    tracker = RecommendationTracker(db_path=storage.db_path)
    learning_engine = SelfLearningEngine(db_path=storage.db_path)

    # 1. Quet thi truong chot phien
    print("[PostMarketReview] Dang quet du lieu chot phien va xac dinh xu huong thi truong...")
    df_results, regime_info = scanner.run_market_scan()
    print(f"[PostMarketReview] Da quet {len(df_results)} co phieu. Xu huong: {regime_info.get('regime')}")

    # 2. Doc tin tuc cho cac ma diem cao nhat de tinh hop hop luc dong tien + tin tuc
    if not df_results.empty:
        top_candidates = df_results[df_results["rule_score"] >= 65].head(8)["symbol"].tolist()
        print(f"[PostMarketReview] Dang cap nhat tin tuc RSS cho {len(top_candidates)} ma co phieu tiem nang: {top_candidates}")
        for sym in top_candidates:
            try:
                news_items = news_provider.get_symbol_news(sym, limit=5)
                print(f"  + {sym}: Tim thay {len(news_items)} tin tuc moi.")
            except Exception as e:
                print(f"  - {sym}: Loi tai tin tuc ({e})")

    # 3. Kiem dinh va theo doi cac khuyen nghi 14 ngay
    print("[PostMarketReview] Dang doi chieu gia dong cua de danh gia cac khuyen nghi 14 ngay...")
    active_tracked = tracker.get_active_recommendations()
    if not active_tracked.empty and not df_results.empty:
        close_price_map = dict(zip(df_results["symbol"], df_results["close_price"]))
        for _, rec in active_tracked.iterrows():
            sym = rec["symbol"]
            curr_close = close_price_map.get(sym)
            if curr_close:
                tracker.evaluate_and_update(sym, float(curr_close))

    # 4. Cap nhat thong so tu hoc (Self-learning loop)
    perf_metrics = learning_engine.compute_performance_metrics()
    insights = learning_engine.get_actionable_insights()
    print(f"[PostMarketReview] Ti le thang hien tai: {perf_metrics['win_rate_pct']}% | Insights: {len(insights)} chien thuat")

    summary = {
        "timestamp": now_vn.strftime("%Y-%m-%d %H:%M:%S"),
        "symbols_scanned": len(df_results),
        "regime": regime_info.get("regime"),
        "top_candidates_count": len(df_results[df_results["rule_score"] >= 65]) if not df_results.empty else 0,
        "win_rate_pct": perf_metrics["win_rate_pct"]
    }
    print("[PostMarketReview] Hoan tat quy trinh danh gia sau phien thanh cong!")
    return summary


if __name__ == "__main__":
    run_daily_post_market_evaluation(force=True)
