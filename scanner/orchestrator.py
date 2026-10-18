import uuid
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple

from config.trading import load_trading_config
from data.providers.base import BaseDataProvider
from data.providers.vnstock_provider import VnstockProvider
from data.providers.yfinance_provider import YFinanceProvider
from data.downloader import DataDownloader
from data.storage import StorageEngine
from data.news import NewsProvider
from universe.stock_universe import StockUniverse
from features.technical import TechnicalFeatures
from features.momentum import MomentumFeatures
from features.volatility import VolatilityFeatures
from features.liquidity import LiquidityFeatures
from features.market_regime import MarketRegime
from features.news_sentiment import NewsAnalyzer
from strategies.trend_following import TrendFollowingStrategy
from strategies.breakout import BreakoutStrategy
from strategies.relative_strength import RelativeStrengthStrategy
from scanner.scoring import ScoringEngine
from scanner.ranking import StockRanker
from scanner.explanations import SignalExplanations
from scanner.trade_plan import TradePlanEngine
from learning.tracker import RecommendationTracker
from models.predict import ModelPredictor


class MarketScanner:
    """Scans public market data and creates paper-only trade plans with risk limits and news catalysts."""

    def __init__(self, provider: Optional[BaseDataProvider] = None, use_cache: bool = True):
        self.universe = StockUniverse()
        self.provider = provider or VnstockProvider(self.universe)
        self.downloader = DataDownloader(provider=self.provider, use_cache=use_cache)
        self.storage = StorageEngine()
        self.scoring_engine = ScoringEngine()
        self.news_provider = NewsProvider(storage=self.storage)
        self.predictor = ModelPredictor()
        self.trading_config = load_trading_config()
        self.trade_planner = TradePlanEngine(self.trading_config)
        self.tracker = RecommendationTracker(db_path=self.storage.db_path)
        self.tracker.seed_initial_knowledge()

    def _validated_ai_probabilities(self, df: pd.DataFrame) -> Dict[str, Optional[float]]:
        governance = self.trading_config["model_governance"]
        if governance["require_real_data"]:
            return {"ai_prob_5d": None, "ai_prob_10d": None, "ai_prob_20d": None}
        return self.predictor.predict_stock_probabilities(df)

    def run_market_scan(
        self,
        symbols: Optional[List[str]] = None,
        min_avg_volume: float = 50000,
        min_avg_value: float = 1000000000,
        sort_by: str = "rule_score",
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        target_symbols = symbols or self.universe.get_all_symbols()
        print(f"[MarketScanner] Starting market scan for {len(target_symbols)} symbols...")
        stock_dfs = self.downloader.fetch_universe_data(target_symbols)
        index_df = self.downloader.fetch_market_index()
        data_timestamp = self.provider.get_data_timestamp()
        regime_info = MarketRegime.analyze_market_regime(index_df, stock_dfs)
        results_list: List[Dict[str, Any]] = []
        latest_rows: Dict[str, Dict[str, Any]] = {}
        run_id = f"SCAN_{uuid.uuid4().hex[:8].upper()}"

        for sym in target_symbols:
            stock_info = self.universe.get_stock_info(sym) or {}
            df = stock_dfs.get(sym)
            if df is None or df.empty or len(df) < 20:
                continue

            df = TechnicalFeatures.add_technical_indicators(df)
            df = MomentumFeatures.add_momentum_indicators(df)
            df = VolatilityFeatures.add_volatility_indicators(df)
            df = LiquidityFeatures.add_liquidity_indicators(df)
            last_row = df.iloc[-1]
            latest_rows[sym] = last_row.to_dict()
            prev_row = df.iloc[-2] if len(df) > 1 else last_row
            close = float(last_row["close"])
            previous_close = float(prev_row["close"])
            price_change = round((close - previous_close) / previous_close * 100.0, 2) if previous_close > 0 else 0.0

            passed_liq, liquidity_reason = LiquidityFeatures.check_liquidity_filter(df, min_avg_volume, min_avg_value)
            trend_info = TrendFollowingStrategy.evaluate_trend(df)
            breakout_info = BreakoutStrategy.evaluate_breakout(df)
            rs_info = RelativeStrengthStrategy.calculate_relative_strength(df, index_df)
            scores = self.scoring_engine.compute_scores(df, rs_info, trend_info, breakout_info)
            base_rule_score = scores["total_score"]

            # --- EVENT-DRIVEN NEWS ANALYSIS ---
            try:
                news_items = self.news_provider.get_symbol_news(sym, limit=5)
                news_report = NewsAnalyzer.analyze_symbol_news(news_items)
            except Exception as e:
                news_report = NewsAnalyzer.analyze_symbol_news([])

            # Apply news adjustment to rule score (bounded between 0 and 100)
            adjusted_score = round(max(0.0, min(100.0, base_rule_score + news_report["news_score_adjustment"])), 1)

            positives, risks, risk_level = SignalExplanations.generate_explanations(
                df, trend_info, breakout_info, rs_info, scores, passed_liq, liquidity_reason
            )

            # Enrich factors with corporate news catalysts
            for cat in news_report["detected_catalysts"]:
                positives.append(f"Sự kiện doanh nghiệp hỗ trợ: {cat}")
            for warn in news_report["negative_warnings"]:
                risks.append(f"RỦI RO THÔNG TIN: {warn}")

            if news_report["has_fatal_news"]:
                risk_level = "High"

            results_list.append({
                "symbol": sym,
                "exchange": stock_info.get("exchange", "HOSE"),
                "sector": stock_info.get("sector", "Other"),
                "close_price": close,
                "price_change": price_change,
                "avg_volume_20d": round(float(last_row.get("avg_volume_20d", 0)), 0),
                "avg_value_20d": round(float(last_row.get("avg_value_20d", 0)), 0),
                "trend": trend_info.get("trend", "Sideways"),
                "rs_index": rs_info.get("rs_rating", 50.0),
                "rsi": round(float(last_row.get("rsi_14", 50.0)), 1),
                "volume_ratio": round(float(last_row.get("volume_ratio", 1.0)), 2),
                "breakout_status": breakout_info.get("breakout_status", "No Breakout"),
                "rule_score": adjusted_score,
                "base_rule_score": base_rule_score,
                "category": StockRanker.categorize_stock(adjusted_score, passed_liq),
                **self._validated_ai_probabilities(df),
                "risk_level": risk_level,
                "positive_factors": positives,
                "risk_factors": risks,
                "news_sentiment": news_report["news_sentiment"],
                "detected_catalysts": news_report["detected_catalysts"],
                "negative_warnings": news_report["negative_warnings"],
                "news_score_adj": news_report["news_score_adjustment"],
                "has_fatal_news": news_report["has_fatal_news"],
                "news_summary": news_report["summary_reason"],
                "data_timestamp": data_timestamp,
            })

        ranked_results = StockRanker.rank_stocks(results_list, sort_by=sort_by)
        results_df = pd.DataFrame(ranked_results)
        if not results_df.empty:
            self.storage.save_scan_run(run_id, results_df, self.provider.__class__.__name__, self.provider.is_synthetic)
            self._create_trade_plans(run_id, ranked_results, latest_rows, regime_info)
            self._update_14d_tracking(ranked_results)

        print(f"[MarketScanner] Scan completed. Analyzed {len(results_df)} stocks.")
        return results_df, regime_info

    def _create_trade_plans(self, run_id: str, results: List[Dict[str, Any]], latest_rows: Dict[str, Dict[str, Any]], regime_info: Dict[str, Any]):
        account = self.trading_config["account"]
        risk = self.trading_config["risk"]
        equity = float(account["paper_capital_vnd"])
        available_cash = equity * (1 - float(account["cash_reserve_pct"]))
        plans = []
        buy_slots_used = 0
        for result in results:
            plan = self.trade_planner.build_plan(
                result=result,
                last_row=latest_rows[result["symbol"]],
                regime=regime_info["regime"],
                equity=equity,
                available_cash=available_cash,
                open_positions=buy_slots_used,
            )
            plan["plan_id"] = f"PLAN_{uuid.uuid4().hex[:12].upper()}"
            if plan["decision"] == "BUY_CANDIDATE":
                buy_slots_used += 1
                available_cash -= plan["position_value"]
            plans.append(plan)
        self.storage.save_trade_plans(run_id, plans)

    def _update_14d_tracking(self, results: List[Dict[str, Any]]):
        if getattr(self.provider, "is_synthetic", False):
            return
        try:
            price_map = {r["symbol"]: float(r["close_price"]) for r in results}
            self.tracker.update_daily_tracking(price_map)
            for r in results[:8]:
                if float(r.get("rule_score", 0)) >= 65:
                    self.tracker.enroll_candidate(
                        symbol=r["symbol"],
                        entry_price=float(r["close_price"]),
                        rule_score=float(r["rule_score"]),
                        positive_factors=r.get("positive_factors", []),
                        risk_factors=r.get("risk_factors", []),
                        catalysts=r.get("detected_catalysts", []),
                    )
        except Exception as e:
            print(f"[MarketScanner] Warning during 14d tracking update: {e}")
