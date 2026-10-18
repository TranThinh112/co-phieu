from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict

from risk.position_sizing import PositionSizer


class TradePlanEngine:
    """
    Produces rule-based paper-trade plans combining Technical Quant Rules + News Catalysts.
    It enforces the 'Buy the rumor, sell the news' safeguard:
    - Positive news cannot trigger a buy if RSI is overbought (bull trap prevention).
    - Fatal negative news instantly invalidates buy signals.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        risk = config["risk"]
        self.sizer = PositionSizer(
            risk_per_trade_pct=risk["risk_per_trade_pct"],
            max_position_pct=risk["max_position_pct"],
            minimum_order_value_vnd=risk["minimum_order_value_vnd"],
            board_lot_size=risk["board_lot_size"],
        )

    def build_plan(
        self,
        result: Dict[str, Any],
        last_row: Dict[str, Any],
        regime: str,
        equity: float,
        available_cash: float,
        open_positions: int,
    ) -> Dict[str, Any]:
        trade = self.config["trade_plan"]
        risk = self.config["risk"]
        close = float(result["close_price"])
        atr = float(last_row.get("atr_14") or 0.0)
        sma_20 = float(last_row.get("sma_20") or close)
        recent_low = float(last_row.get("low") or close)
        structural_stop = min(sma_20, recent_low) * (1 - trade["structural_stop_buffer_pct"])
        atr_stop = close - (atr * trade["atr_stop_multiple"])
        stop = max(0.01, min(structural_stop, atr_stop))
        risk_per_share = close - stop

        base = {
            "symbol": result["symbol"],
            "decision": "DO_NOT_BUY",
            "entry_price": round(close, 2),
            "stop_loss": round(stop, 2),
            "take_profit_1": None,
            "take_profit_2": None,
            "quantity": 0,
            "position_value": 0.0,
            "risk_amount": 0.0,
            "risk_reward_1": 0.0,
            "risk_reward_2": 0.0,
            "holding_period_sessions": trade["holding_period_sessions"],
            "execution_mode": "PAPER_ONLY",
            "reason": "",
            "invalidates_if": "Close below stop-loss, negative news breaks, or risk limits are exceeded",
        }

        exclusions = []

        # 1. Fatal News Check (Legal risk, bankruptcy, investigation, fraud)
        if result.get("has_fatal_news"):
            exclusions.append(f"CẢNH BÁO PHÁP LÝ/TIN XẤU: {'; '.join(result.get('negative_warnings', []))}")

        # 2. 'Buy the rumor, sell the news' Bull Trap Safeguard:
        # If there are strong positive catalysts (trúng thầu, cổ tức...) but RSI > 72 or already extended, reject!
        if result.get("detected_catalysts") and result.get("rsi", 0) >= 72:
            exclusions.append("Nguy cơ bẫy 'Tin ra là bán': Tin tích cực nhưng RSI quá mua (> 72), giá đã phản ánh")

        # 3. Rule Score check (adjusted by news impact)
        if result.get("rule_score", 0) < trade["min_rule_score"]:
            exclusions.append("Điểm định lượng (kèm tin tức) chưa đạt ngưỡng chuẩn (tối thiểu 70)")

        # 4. Market regime check
        if "Bearish" in regime:
            exclusions.append("Thị trường chung đang trong xu hướng Giảm (Bearish)")

        # 5. Overbought RSI check
        if result.get("rsi", 0) >= trade["reject_rsi_above"]:
            exclusions.append("RSI nằm ở vùng quá mua rủi ro")

        # 6. Technical Risk check
        if trade["reject_high_risk"] and result.get("risk_level") == "High":
            exclusions.append("Mức độ rủi ro biến động kỹ thuật cao")

        # 7. Open positions quota
        if open_positions >= risk["max_open_positions"]:
            exclusions.append("Đã đạt giới hạn tối đa số vị thế nắm giữ đồng thời")

        # 8. Stop loss integrity
        if stop >= close or risk_per_share <= 0:
            exclusions.append("Không thể xác định ngưỡng cắt lỗ hợp lệ")

        if exclusions:
            base["reason"] = "; ".join(exclusions)
            return base

        # Calculate position size
        sizing = self.sizer.calculate(equity, available_cash, close, stop)
        if sizing.quantity == 0:
            base["reason"] = sizing.reason
            return base

        target_1 = close + risk_per_share * trade["target_one_r_multiple"]
        target_2 = close + risk_per_share * trade["target_two_r_multiple"]

        reasons = ["Thỏa mãn toàn bộ tiêu chí kỹ thuật, dòng tiền và kiểm soát rủi ro"]
        if result.get("detected_catalysts"):
            reasons.append(f"Cộng hưởng tin tốt: {', '.join(result['detected_catalysts'])}")

        base.update({
            "decision": "BUY_CANDIDATE",
            "take_profit_1": round(target_1, 2),
            "take_profit_2": round(target_2, 2),
            "quantity": sizing.quantity,
            "position_value": round(sizing.position_value, 2),
            "risk_amount": round(sizing.risk_amount, 2),
            "risk_reward_1": trade["target_one_r_multiple"],
            "risk_reward_2": trade["target_two_r_multiple"],
            "reason": "; ".join(reasons),
        })
        return base
