class TransactionCosts:
    """Calculates brokerage commissions, tax and slippage costs."""

    def __init__(self, commission_buy: float = 0.001, commission_sell: float = 0.002, slippage: float = 0.001):
        self.commission_buy = commission_buy   # 0.1% buy commission
        self.commission_sell = commission_sell # 0.1% sell commission + 0.1% tax = 0.2%
        self.slippage = slippage               # 0.1% slippage penalty

    def calculate_buy_cost(self, amount: float) -> float:
        # Effective buy price is slightly higher due to slippage
        cost = amount * (self.commission_buy + self.slippage)
        return cost

    def calculate_sell_cost(self, amount: float) -> float:
        # Effective sell price is slightly lower due to slippage
        cost = amount * (self.commission_sell + self.slippage)
        return cost
