import pandas as pd
from typing import List, Dict, Any

class StockRanker:
    """Classifies and ranks screened stocks by quantitative score and filters."""

    @staticmethod
    def categorize_stock(score: float, passed_liquidity: bool) -> str:
        if not passed_liquidity:
            return "Excluded (Thanh khoản kém)"
        if score >= 75.0:
            return "Strong Candidate"
        elif score >= 60.0:
            return "Potential Candidate"
        elif score >= 45.0:
            return "Watchlist"
        else:
            return "Excluded"

    @staticmethod
    def rank_stocks(results_list: List[Dict[str, Any]], sort_by: str = "rule_score") -> List[Dict[str, Any]]:
        if not results_list:
            return []

        def get_sort_key(item):
            val = item.get(sort_by)
            if val is None or pd.isna(val):
                return -999.0
            return float(val)

        sorted_list = sorted(results_list, key=get_sort_key, reverse=True)
        for rank, item in enumerate(sorted_list, 1):
            item["rank"] = rank

        return sorted_list
