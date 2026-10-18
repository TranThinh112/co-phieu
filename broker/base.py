from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class BaseBrokerAdapter(ABC):
    """Abstract Interface for Broker Integration (Paper Trading and Live APIs)."""

    @abstractmethod
    def get_account_balance(self) -> Dict[str, float]:
        pass

    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_open_orders(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def place_order(self, symbol: str, side: str, quantity: int, price: float, order_type: str = "LO") -> Dict[str, Any]:
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        pass

    @property
    @abstractmethod
    def is_paper_trading(self) -> bool:
        pass
