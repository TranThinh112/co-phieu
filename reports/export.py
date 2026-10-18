import os
import json
import datetime
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List

class ReportExporter:
    """Exports scan results, watchlists, and backtest reports to CSV or JSON."""

    def __init__(self, export_dir: str = "reports"):
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)

    def export_scan_results_csv(self, df: pd.DataFrame, filename: str = "") -> str:
        if df is None or df.empty:
            return ""

        if not filename:
            now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"scan_results_{now_str}.csv"

        filepath = self.export_dir / filename
        
        # Flatten factors lists if present
        export_df = df.copy()
        if 'positive_factors' in export_df.columns:
            export_df['positive_factors'] = export_df['positive_factors'].apply(lambda x: "; ".join(x) if isinstance(x, list) else str(x))
        if 'risk_factors' in export_df.columns:
            export_df['risk_factors'] = export_df['risk_factors'].apply(lambda x: "; ".join(x) if isinstance(x, list) else str(x))

        export_df.to_csv(filepath, index=False, encoding='utf-8-sig')
        return str(filepath)

    def export_backtest_summary(self, metrics: Dict[str, Any], trades: List[Dict[str, Any]], filename: str = "") -> str:
        if not filename:
            now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"backtest_report_{now_str}.json"

        filepath = self.export_dir / filename
        data = {
            "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "metrics": metrics,
            "trades_count": len(trades),
            "trades": trades
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return str(filepath)
