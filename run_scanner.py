import sys
import argparse
import pandas as pd
from pathlib import Path

# Ensure UTF-8 output on Windows console
sys.stdout.reconfigure(encoding='utf-8')

from data.providers.vnstock_provider import VnstockProvider
from data.providers.yfinance_provider import YFinanceProvider
from data.providers.synthetic_provider import SyntheticDataProvider
from data.providers.csv_provider import CsvDataProvider
from scanner.orchestrator import MarketScanner
from reports.export import ReportExporter
from models.train import ModelTrainer
from backtest.engine import BacktestEngine

def main():
    parser = argparse.ArgumentParser(description="AI Stock Scanner - Vietnam Stock Market")
    parser.add_argument("--mode", choices=["scan", "train", "backtest", "all"], default="scan", help="Execution mode")
    parser.add_argument("--provider", choices=["vnstock", "public", "csv", "synthetic"], default="vnstock", help="Data provider type")
    parser.add_argument("--export", action="store_true", help="Export scan results to CSV")
    args = parser.parse_args()

    # Select provider
    if args.provider == "synthetic":
        provider = SyntheticDataProvider()
        print("[INFO] Using Synthetic Data Provider (For unit tests and offline testing).")
    elif args.provider == "csv":
        provider = CsvDataProvider()
        print("[INFO] Using CSV Data Provider.")
    else:
        provider = YFinanceProvider()
        print("[INFO] Using Public API (Yahoo Finance .VN) Data Provider.")

    scanner = MarketScanner(provider=provider)

    if args.mode in ["scan", "all"]:
        print("=== RUNNING MARKET SCAN ===")
        df_results, regime_info = scanner.run_market_scan()

        print("\n--- KẾT QUẢ QUÉT THỊ TRƯỜNG ---")
        print(f"Trạng thái thị trường: {regime_info.get('regime')}")
        print(f"Tỷ lệ CP > SMA20: {regime_info.get('pct_above_sma20')}% | CP > SMA50: {regime_info.get('pct_above_sma50')}%")
        print("-" * 80)

        if not df_results.empty:
            display_cols = ['rank', 'symbol', 'exchange', 'close_price', 'price_change', 'trend', 'rule_score', 'ai_prob_5d', 'category', 'risk_level']
            cols_present = [c for c in display_cols if c in df_results.columns]
            print(df_results[cols_present].head(15).to_string(index=False))

            if args.export:
                exporter = ReportExporter()
                fpath = exporter.export_scan_results_csv(df_results)
                print(f"\n[OK] Đã xuất kết quả quét ra file CSV: {fpath}")

    if args.mode in ["train", "all"]:
        print("\n=== HUẤN LUYỆN MÔ HÌNH AI ===")
        stock_dfs = scanner.downloader.fetch_universe_data()
        trainer = ModelTrainer()
        results = trainer.train_all_horizons(stock_dfs, horizons=[5, 10, 20])
        print("[OK] Hoàn thành huấn luyện mô hình AI.")

    if args.mode in ["backtest", "all"]:
        print("\n=== CHẠY BACKTEST CHIẾN LƯỢC ===")
        stock_dfs = scanner.downloader.fetch_universe_data()
        idx_df = scanner.downloader.fetch_market_index()
        engine = BacktestEngine(initial_capital=100000000.0)
        bt_res = engine.run_backtest(stock_dfs, idx_df, holding_period=10, score_threshold=55.0)

        metrics = bt_res['metrics']
        print("--- KẾT QUẢ BACKTEST ---")
        print(f"Tổng lợi nhuận (Total Return): {metrics['total_return_pct']}%")
        print(f"CAGR: {metrics['cagr_pct']}%")
        print(f"Max Drawdown: {metrics['max_drawdown_pct']}%")
        print(f"Sharpe Ratio: {metrics['sharpe_ratio']}")
        print(f"Tỷ lệ thắng (Win Rate): {metrics['win_rate_pct']}%")
        print(f"Profit Factor: {metrics['profit_factor']}")
        print(f"Tổng số giao dịch: {metrics['total_trades']}")

if __name__ == "__main__":
    main()

