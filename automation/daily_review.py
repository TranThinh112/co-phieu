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



def run_autopilot_paper_trading(df_results, active_tracked, tracker, learning_engine) -> dict:
    """
    Cơ chế Tự Động Giao Dịch Bằng Số Tiền Ảo & Đúc Rút Kinh Nghiệm Tự Học:
    1. Quản trị các lệnh ảo đang mở: Tự động BÁN CHỐT LỜI khi chạm TP1 (+8%) hoặc BÁN CẮT LỖ khi chạm SL (-5%).
    2. Đánh giá lại Top 3 mã bứt phá hôm nay, tự động chọn ra 1 mã tối ưu nhất.
    3. Tự phân bổ số vốn ảo an toàn (10-15% NAV, khoảng 10-15 triệu) theo đúng lô 100 CP chuẩn sàn.
    4. Tiến hành MUA ẢO tự động để kiểm nghiệm thực tế.
    5. Đưa kết quả thắng/thua vào vòng lặp Self-Learning Feedback Loop để bot tự học và thông minh hơn.
    """
    from broker.paper import PaperBroker
    import sqlite3

    print("[AutopilotPaper] Kích hoạt cơ chế tự động đánh giá & giao dịch tiền ảo...")
    broker = PaperBroker()
    bal = broker.get_account_balance()
    cash = bal.get("cash", 0.0)
    total_nav = bal.get("total_equity", 100000000.0)

    # 1. KIỂM TRA CHỐT LỜI / CẮT LỖ CÁC VỊ THẾ ẢO ĐANG MỞ
    open_positions = broker.get_positions()
    if open_positions and not df_results.empty:
        close_map = dict(zip(df_results["symbol"], df_results["close_price"]))
        for pos in open_positions:
            pos_sym = pos["symbol"]
            pos_qty = int(pos["quantity"])
            pos_avg = float(pos["avg_buy_price"])
            if pos_qty <= 0 or pos_sym not in close_map:
                continue
            curr_p = float(close_map[pos_sym])
            pnl_pct = ((curr_p - pos_avg) / pos_avg) * 100.0 if pos_avg > 0 else 0.0

            # TP1 (+8%) hoặc SL (-5%)
            if pnl_pct >= 8.0:
                print(f"[AutopilotPaper] {pos_sym} ĐẠT MỤC TIÊU CHỐT LỜI (+{pnl_pct:.2f}%). Bot tự động BÁN CHỐT LỜI ẢO...")
                broker.place_order(pos_sym, "SELL", pos_qty, curr_p)
                learning_engine.run_offline_learning_cycle()
            elif pnl_pct <= -5.0:
                print(f"[AutopilotPaper] {pos_sym} CHẠM NGƯỠNG CẮT LỖ ({pnl_pct:.2f}%). Bot tự động BÁN CẮT LỖ ẢO...")
                broker.place_order(pos_sym, "SELL", pos_qty, curr_p)
                learning_engine.run_offline_learning_cycle()
            else:
                with sqlite3.connect(broker.db_path) as conn:
                    conn.cursor().execute("UPDATE paper_positions SET current_price = ? WHERE symbol = ?", (curr_p, pos_sym))
                    conn.commit()

    # 2. LỰA CHỌN 1 MÃ XUẤT SẮC NHẤT TRONG TOP 3 ĐỂ MUA ẢO
    if cash < 5000000:
        print(f"[AutopilotPaper] Tiền mặt còn lại ({cash:,.0f} đ) không đủ để mở vị thế mới.")
        return {"action": "HOLD", "reason": "Tiền mặt không đủ"}

    held_symbols = [p["symbol"] for p in broker.get_positions() if p["quantity"] > 0]
    candidates = []

    if not active_tracked.empty and not df_results.empty:
        close_map = dict(zip(df_results["symbol"], df_results["close_price"]))
        score_map = dict(zip(df_results["symbol"], df_results["rule_score"]))
        val_map = dict(zip(df_results["symbol"], df_results["avg_value_20d"]))

        for _, tr in active_tracked.iterrows():
            sym = tr["symbol"]
            if sym in held_symbols:
                continue # Đã mua thì không mua lặp lại

            c_price = float(close_map.get(sym, tr.get("current_price", 0.0)))
            c_score = float(score_map.get(sym, tr.get("rule_score", 0.0)))
            c_val = float(val_map.get(sym, 0.0))

            if c_price <= 0:
                continue

            candidates.append({
                "symbol": sym,
                "price": c_price,
                "score": c_score,
                "val": c_val
            })

    if not candidates:
        print("[AutopilotPaper] Chưa có ứng viên mới chưa sở hữu để mở vị thế ảo.")
        return {"action": "NONE"}

    # Sắp xếp ưu tiên: Điểm AI cao nhất, nếu bằng điểm thì ưu tiên thanh khoản giá trị giao dịch lớn nhất
    candidates.sort(key=lambda x: (x["score"], x["val"]), reverse=True)
    best_candidate = candidates[0]
    chosen_sym = best_candidate["symbol"]
    chosen_p = best_candidate["price"]

    # 3. PHÂN BỔ SỐ VỐN ẢO & TÍNH SỐ LƯỢNG LÔ 100 CHUẨN SÀN
    target_alloc = min(cash * 0.8, total_nav * 0.15) # Tối đa 15% NAV
    raw_qty = int(target_alloc // chosen_p)
    lot_qty = (raw_qty // 100) * 100
    if lot_qty < 100:
        lot_qty = 100 # Tối thiểu 1 lô 100 CP

    order_val = lot_qty * chosen_p
    if order_val <= cash:
        print(f"[AutopilotPaper] BOT TỰ ĐỘNG CHỌN MUA ẢO: {chosen_sym} | Khối lượng: {lot_qty:,} CP | Giá: {chosen_p:,.0f} đ | Tổng vốn: {order_val:,.0f} đ")
        order_res = broker.place_order(chosen_sym, "BUY", lot_qty, chosen_p)
        return {
            "action": "BOUGHT",
            "symbol": chosen_sym,
            "quantity": lot_qty,
            "price": chosen_p,
            "order_val": order_val,
            "order_id": order_res.get("order_id")
        }
    else:
        return {"action": "FAILED", "reason": "Tiền mặt không đủ cho lô 100"}


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
        tracker.update_daily_tracking(close_price_map)

    # 4. BOT TU DONG DANH GIA & GIAO DICH TIEN AO (AUTOPILOT PAPER TRADING)
    paper_res = run_autopilot_paper_trading(df_results, tracker.get_active_recommendations(), tracker, learning_engine)

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
