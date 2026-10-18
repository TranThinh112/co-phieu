import numpy as np
import pandas as pd
from typing import Dict, Any, List

class PerformanceMetrics:
    """Computes quantitative performance & risk metrics for backtest strategies."""

    @staticmethod
    def calculate_metrics(equity_curve: pd.Series, trades: List[Dict[str, Any]], risk_free_rate: float = 0.04) -> Dict[str, Any]:
        if equity_curve is None or len(equity_curve) < 2:
            return {
                "total_return_pct": 0.0,
                "cagr_pct": 0.0,
                "max_drawdown_pct": 0.0,
                "sharpe_ratio": 0.0,
                "sortino_ratio": 0.0,
                "win_rate_pct": 0.0,
                "profit_factor": 0.0,
                "total_trades": 0,
                "turnover_annual": 0.0
            }

        initial_val = equity_curve.iloc[0]
        final_val = equity_curve.iloc[-1]
        total_ret = ((final_val - initial_val) / initial_val) * 100.0

        n_days = len(equity_curve)
        cagr = (((final_val / initial_val) ** (252.0 / max(1, n_days))) - 1.0) * 100.0 if final_val > 0 else -100.0

        # Maximum Drawdown (MDD)
        cummax = equity_curve.cummax()
        drawdown = (equity_curve - cummax) / cummax * 100.0
        max_dd = float(drawdown.min())

        # Daily returns & Sharpe / Sortino
        daily_ret = equity_curve.pct_change().dropna()
        daily_rf = (1.0 + risk_free_rate) ** (1.0 / 252.0) - 1.0
        excess_ret = daily_ret - daily_rf

        std_daily = daily_ret.std()
        sharpe = (excess_ret.mean() / std_daily * np.sqrt(252)) if std_daily > 0 else 0.0

        downside_std = daily_ret[daily_ret < 0].std()
        sortino = (excess_ret.mean() / downside_std * np.sqrt(252)) if downside_std > 0 else 0.0

        # Trade metrics
        total_trades = len(trades)
        if total_trades > 0:
            profits = [t['pnl_pct'] for t in trades if t.get('pnl_pct') is not None]
            wins = [p for p in profits if p > 0]
            losses = [p for p in profits if p < 0]

            win_rate = (len(wins) / len(profits) * 100.0) if profits else 0.0
            gross_profit = sum(wins)
            gross_loss = abs(sum(losses))
            profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)
        else:
            win_rate = 0.0
            profit_factor = 0.0

        return {
            "total_return_pct": round(total_ret, 2),
            "cagr_pct": round(cagr, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "sharpe_ratio": round(sharpe, 2),
            "sortino_ratio": round(sortino, 2),
            "win_rate_pct": round(win_rate, 2),
            "profit_factor": round(profit_factor, 2),
            "total_trades": total_trades,
            "turnover_annual": round((total_trades * 2.0) / (n_days / 252.0), 1) if n_days > 0 else 0.0
        }
