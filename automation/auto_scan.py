"""Scheduled job: scan public data and persist paper-only trade plans."""
import sys
from pathlib import Path

# Add project root to sys.path so modules like data, scanner can be found
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure UTF-8 output on Windows console/logs
sys.stdout.reconfigure(encoding="utf-8")

from data.providers.vnstock_provider import VnstockProvider
from scanner.orchestrator import MarketScanner


def main() -> int:
    print(f"[AutoScan] Starting scheduled scan at project root: {PROJECT_ROOT}")
    scanner = MarketScanner(provider=VnstockProvider())
    results, regime = scanner.run_market_scan()
    plans = scanner.storage.get_latest_trade_plans()
    candidates = plans[plans["decision"] == "BUY_CANDIDATE"] if not plans.empty else plans
    print(f"[AutoScan] Market regime: {regime.get('regime')}")
    print(f"[AutoScan] Scanned symbols: {len(results)}")
    print(f"[AutoScan] Total trade plans generated: {len(plans)}")
    print(f"[AutoScan] Paper buy candidates: {len(candidates)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

