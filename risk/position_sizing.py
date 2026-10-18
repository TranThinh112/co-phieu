import math
from dataclasses import dataclass


@dataclass(frozen=True)
class PositionSizingResult:
    quantity: int
    risk_amount: float
    risk_per_share: float
    position_value: float
    position_pct: float
    reason: str


class PositionSizer:
    """Position sizing with fixed-risk and maximum-allocation constraints."""

    def __init__(
        self,
        risk_per_trade_pct: float = 0.005,
        max_position_pct: float = 0.15,
        minimum_order_value_vnd: float = 1_000_000,
        board_lot_size: int = 100,
    ):
        self.risk_per_trade_pct = risk_per_trade_pct
        self.max_position_pct = max_position_pct
        self.minimum_order_value_vnd = minimum_order_value_vnd
        self.board_lot_size = board_lot_size

    def calculate(self, equity: float, available_cash: float, entry_price: float, stop_price: float) -> PositionSizingResult:
        if equity <= 0 or available_cash <= 0 or entry_price <= 0 or stop_price <= 0 or stop_price >= entry_price:
            return PositionSizingResult(0, 0.0, 0.0, 0.0, 0.0, "Invalid account or stop-loss inputs")

        risk_amount = equity * self.risk_per_trade_pct
        risk_per_share = entry_price - stop_price
        quantity_by_risk = math.floor(risk_amount / risk_per_share)
        quantity_by_allocation = math.floor((equity * self.max_position_pct) / entry_price)
        quantity_by_cash = math.floor(available_cash / entry_price)
        quantity = min(quantity_by_risk, quantity_by_allocation, quantity_by_cash)
        quantity = (quantity // self.board_lot_size) * self.board_lot_size
        position_value = quantity * entry_price

        if quantity <= 0 or position_value < self.minimum_order_value_vnd:
            return PositionSizingResult(0, risk_amount, risk_per_share, 0.0, 0.0, "Position below minimum board lot or order value")

        return PositionSizingResult(
            quantity=quantity,
            risk_amount=risk_amount,
            risk_per_share=risk_per_share,
            position_value=position_value,
            position_pct=position_value / equity,
            reason="Risk and allocation limits satisfied",
        )
