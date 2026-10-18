import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional

from backtest.costs import TransactionCosts
from backtest.metrics import PerformanceMetrics
from features.technical import TechnicalFeatures
from features.momentum import MomentumFeatures
from features.volatility import VolatilityFeatures
from features.liquidity import LiquidityFeatures
from strategies.trend_following import TrendFollowingStrategy
from strategies.breakout import BreakoutStrategy
from strategies.relative_strength import RelativeStrengthStrategy
from scanner.scoring import ScoringEngine

class BacktestEngine:
    """Historical event-driven backtest simulation engine."""

    def __init__(self, initial_capital: float = 100000000.0, max_positions: int = 5, cost_model: Optional[TransactionCosts] = None):
        self.initial_capital = initial_capital
        self.max_positions = max_positions
        self.cost_model = cost_model or TransactionCosts()
        self.scoring_engine = ScoringEngine()

    def run_backtest(
        self,
        stock_dfs: Dict[str, pd.DataFrame],
        index_df: pd.DataFrame,
        holding_period: int = 10,
        score_threshold: float = 60.0,
        stop_loss_pct: float = -0.07,
        take_profit_pct: float = 0.15
    ) -> Dict[str, Any]:

        if not stock_dfs or index_df is None or index_df.empty:
            return {"metrics": PerformanceMetrics.calculate_metrics(None, []), "equity_df": pd.DataFrame(), "trades": []}

        # 1. Precalculate indicators for all stocks
        processed_dfs = {}
        for sym, df in stock_dfs.items():
            if df is not None and len(df) >= 30:
                p_df = TechnicalFeatures.add_technical_indicators(df)
                p_df = MomentumFeatures.add_momentum_indicators(p_df)
                p_df = VolatilityFeatures.add_volatility_indicators(p_df)
                p_df = LiquidityFeatures.add_liquidity_indicators(p_df)
                processed_dfs[sym] = p_df

        # Get common dates timeline
        all_dates = sorted(list(index_df['date'].unique()))
        if len(all_dates) < 30:
            return {"metrics": PerformanceMetrics.calculate_metrics(None, []), "equity_df": pd.DataFrame(), "trades": []}

        cash = self.initial_capital
        positions = {} # sym -> {entry_price, qty, entry_date, days_held}
        trades = []
        equity_records = []

        position_weight = 1.0 / self.max_positions

        # Loop chronologically through trading dates
        for idx in range(30, len(all_dates)):
            curr_date = all_dates[idx]

            # Calculate total portfolio equity on curr_date
            curr_portfolio_val = cash
            for sym, pos in list(positions.items()):
                df_s = processed_dfs.get(sym)
                if df_s is not None:
                    row_s = df_s[df_s['date'] == curr_date]
                    if not row_s.empty:
                        c_price = row_s.iloc[0]['close']
                        curr_portfolio_val += pos['qty'] * c_price
                    else:
                        curr_portfolio_val += pos['qty'] * pos['entry_price']

            equity_records.append({'date': curr_date, 'portfolio_value': curr_portfolio_val})

            # Check open positions for exit rules (holding period limit or stop loss / take profit)
            for sym in list(positions.keys()):
                pos = positions[sym]
                df_s = processed_dfs.get(sym)
                if df_s is None:
                    continue

                row_s = df_s[df_s['date'] == curr_date]
                if row_s.empty:
                    continue

                curr_price = row_s.iloc[0]['close']
                pnl_pct = (curr_price - pos['entry_price']) / pos['entry_price']
                pos['days_held'] += 1

                should_exit = False
                exit_reason = ""

                if pnl_pct <= stop_loss_pct:
                    should_exit = True
                    exit_reason = "Stop Loss"
                elif pnl_pct >= take_profit_pct:
                    should_exit = True
                    exit_reason = "Take Profit"
                elif pos['days_held'] >= holding_period:
                    should_exit = True
                    exit_reason = "Holding Time Limit"

                if should_exit:
                    gross_proceeds = pos['qty'] * curr_price
                    cost = self.cost_model.calculate_sell_cost(gross_proceeds)
                    net_proceeds = gross_proceeds - cost
                    cash += net_proceeds

                    final_pnl_pct = ((net_proceeds - (pos['qty'] * pos['entry_price'])) / (pos['qty'] * pos['entry_price'])) * 100.0
                    trades.append({
                        'symbol': sym,
                        'entry_date': pos['entry_date'],
                        'exit_date': curr_date,
                        'entry_price': pos['entry_price'],
                        'exit_price': curr_price,
                        'pnl_pct': final_pnl_pct,
                        'days_held': pos['days_held'],
                        'reason': exit_reason
                    })
                    del positions[sym]

            # Rebalance & check for new entries every 5 sessions if slot available
            if len(positions) < self.max_positions and (idx % 5 == 0):
                sub_index = index_df[index_df['date'] <= curr_date]
                candidate_scores = []

                for sym, df_s in processed_dfs.items():
                    if sym in positions:
                        continue
                    sub_s = df_s[df_s['date'] <= curr_date]
                    if len(sub_s) < 20:
                        continue

                    t_info = TrendFollowingStrategy.evaluate_trend(sub_s)
                    b_info = BreakoutStrategy.evaluate_breakout(sub_s)
                    rs_info = RelativeStrengthStrategy.calculate_relative_strength(sub_s, sub_index)
                    scores = self.scoring_engine.compute_scores(sub_s, rs_info, t_info, b_info)

                    if scores['total_score'] >= score_threshold:
                        candidate_scores.append((sym, scores['total_score'], sub_s.iloc[-1]['close']))

                # Sort top candidates
                candidate_scores.sort(key=lambda x: x[1], reverse=True)
                available_slots = self.max_positions - len(positions)

                for sym, sc, entry_price in candidate_scores[:available_slots]:
                    alloc_cash = min(cash, curr_portfolio_val * position_weight)
                    if alloc_cash > 1000000 and entry_price > 0: # At least 1M VND allocation
                        qty = int(alloc_cash / entry_price)
                        if qty > 0:
                            actual_cost = qty * entry_price
                            buy_fee = self.cost_model.calculate_buy_cost(actual_cost)
                            total_spent = actual_cost + buy_fee

                            if cash >= total_spent:
                                cash -= total_spent
                                positions[sym] = {
                                    'entry_price': entry_price,
                                    'qty': qty,
                                    'entry_date': curr_date,
                                    'days_held': 0
                                }

        equity_df = pd.DataFrame(equity_records)
        metrics = PerformanceMetrics.calculate_metrics(equity_df['portfolio_value'] if not equity_df.empty else None, trades)

        return {
            "metrics": metrics,
            "equity_df": equity_df,
            "trades": trades
        }
