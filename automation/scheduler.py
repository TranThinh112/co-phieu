import time
import threading
import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from automation.session_manager import MarketSessionManager

class MarketAutopilotScheduler:
    """Background Daemon Scheduler dieu phoi bot tu dong quet khi mo phien,
    danh gia sau phien va tu hoc cuoi tuan."""

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self.last_action: str = 'Khởi tạo scheduler'
        self.last_run_time: Optional[str] = None
        self.last_morning_date: Optional[str] = None
        self.last_afternoon_date: Optional[str] = None
        self.last_post_market_date: Optional[str] = None
        self.last_weekend_date: Optional[str] = None
        self.logs: list = []

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = MarketAutopilotScheduler()
            return cls._instance

    def log(self, message: str):
        now_str = MarketSessionManager.get_vietnam_now().strftime('%H:%M:%S %d/%m')
        entry = f'[{now_str}] {message}'
        print(f'[Autopilot] {entry}')
        self.logs.append(entry)
        if len(self.logs) > 20:
            self.logs = self.logs[-20:]

    def get_status(self) -> Dict[str, Any]:
        now_vn = MarketSessionManager.get_vietnam_now()
        weekday = now_vn.weekday()
        curr_time = now_vn.time()
        
        # Tinh moc tu dong tiep theo
        if weekday < 5:  # Thu 2 - Thu 6
            if curr_time < datetime.time(9, 5):
                next_action = 'Quét mở phiên sáng (09:05)'
                next_time_str = '09:05 hôm nay'
            elif curr_time < datetime.time(13, 5):
                next_action = 'Quét mở phiên chiều (13:05)'
                next_time_str = '13:05 hôm nay'
            elif curr_time < datetime.time(15, 5):
                next_action = 'Tổng kết phiên & Tin tức (15:05)'
                next_time_str = '15:05 hôm nay'
            else:
                next_action = 'Quét mở phiên sáng (09:05 ngày mai)'
                next_time_str = '09:05 ngày mai'
        else:  # Cuoi tuan
            next_action = 'Tự học & Tinh chỉnh mô hình AI'
            next_time_str = 'Đang chạy chế độ cuối tuần'

        return {
            'is_running': self.is_running,
            'last_action': self.last_action,
            'last_run_time': self.last_run_time or 'Chờ phiên giao dịch',
            'next_action': next_action,
            'next_time_str': next_time_str,
            'logs': self.logs[-5:]
        }

    def start(self):
        with self._lock:
            if self.is_running and self._thread and self._thread.is_alive():
                return
            self.is_running = True
            self._thread = threading.Thread(target=self._run_loop, daemon=True, name='AutopilotDaemon')
            self._thread.start()
            self.log('Đã khởi động Autopilot Daemon chạy ngầm.')

    def trigger_scan_now(self, scan_type: str = 'MANUAL') -> dict:
        """Kich hoat quet ngay lap tuc theo yeu cau."""
        self.log(f'Kích hoạt quét thị trường ({scan_type})...')
        try:
            from scanner.orchestrator import MarketScanner
            from data.providers.vnstock_provider import VnstockProvider
            from universe.stock_universe import StockUniverse
            
            universe = StockUniverse()
            scanner = MarketScanner(provider=VnstockProvider(universe=universe))
            df_res, regime = scanner.run_market_scan()
            now_vn = MarketSessionManager.get_vietnam_now()
            
            self.last_action = f'Quét thành công {len(df_res)} mã ({scan_type})'
            self.last_run_time = now_vn.strftime('%H:%M:%S %d/%m/%Y')
            self.log(self.last_action)
            return {'status': 'SUCCESS', 'symbols': len(df_res), 'regime': regime.get('regime')}
        except Exception as e:
            self.last_action = f'Lỗi quét: {str(e)}'
            self.log(self.last_action)
            return {'status': 'ERROR', 'error': str(e)}

    def trigger_post_market_now(self) -> dict:
        """Kich hoat tong ket phien ngay lap tuc."""
        self.log('Kích hoạt tổng kết phiên và đọc tin tức...')
        try:
            from automation.daily_review import run_daily_post_market_evaluation
            res = run_daily_post_market_evaluation(force=True)
            now_vn = MarketSessionManager.get_vietnam_now()
            scanned = res.get('symbols_scanned', 0) if isinstance(res, dict) else 0
            self.last_action = f'Tổng kết phiên thành công ({scanned} mã)'
            self.last_run_time = now_vn.strftime('%H:%M:%S %d/%m/%Y')
            self.log(self.last_action)
            return res
        except Exception as e:
            self.last_action = f'Lỗi tổng kết phiên: {str(e)}'
            self.log(self.last_action)
            return {'status': 'ERROR', 'error': str(e)}

    def _run_loop(self):
        """Vong lap ngam kiem tra thoi gian de tu dong quet."""
        while self.is_running:
            try:
                now_vn = MarketSessionManager.get_vietnam_now()
                today_str = now_vn.strftime('%Y-%m-%d')
                weekday = now_vn.weekday()
                curr_t = now_vn.time()

                # Chi tu dong trong cac ngay trong tuan (Thu 2 - Thu 6)
                if weekday < 5:
                    # 1. Quet mo phien sang (09:05 - 11:30)
                    if datetime.time(9, 5) <= curr_t <= datetime.time(11, 30):
                        if self.last_morning_date != today_str:
                            self.log(f'Phát hiện mở phiên sáng {today_str}. Bắt đầu tự động quét...')
                            self.trigger_scan_now('AUTO_MORNING')
                            self.last_morning_date = today_str

                    # 2. Quet mo phien chieu (13:05 - 15:00)
                    elif datetime.time(13, 5) <= curr_t <= datetime.time(15, 0):
                        if self.last_afternoon_date != today_str:
                            self.log(f'Phát hiện mở phiên chiều {today_str}. Bắt đầu tự động quét...')
                            self.trigger_scan_now('AUTO_AFTERNOON')
                            self.last_afternoon_date = today_str

                    # 3. Tong ket sau phien ATC & Tin tuc (15:05 - 16:30)
                    elif datetime.time(15, 5) <= curr_t <= datetime.time(16, 30):
                        if self.last_post_market_date != today_str:
                            self.log(f'Phát hiện kết thúc phiên {today_str}. Bắt đầu tổng kết & đọc tin tức...')
                            self.trigger_post_market_now()
                            self.last_post_market_date = today_str

                else:
                    # Cuoi tuan: Kich hoat tu hoc moi cuoi tuan 1 lan
                    weekend_key = f'{today_str}_weekend'
                    if self.last_weekend_date != weekend_key:
                        self.log(f'Phát hiện cuối tuần {today_str}. Kích hoạt chế độ Bot Tự Học...')
                        try:
                            from learning.feedback_loop import SelfLearningEngine
                            from data.storage import StorageEngine
                            engine = SelfLearningEngine(db_path=StorageEngine().db_path)
                            engine.run_offline_learning_cycle()
                            self.last_action = 'Tự học cuối tuần hoàn tất'
                            self.last_run_time = now_vn.strftime('%H:%M:%S %d/%m/%Y')
                            self.last_weekend_date = weekend_key
                            self.log('Đã hoàn tất tinh chỉnh mô hình AI cuối tuần.')
                        except Exception as e:
                            self.log(f'Lỗi tự học cuối tuần: {e}')

            except Exception as e:
                self.log(f'Lỗi trong vòng lặp autopilot: {e}')

            # Kiem tra lai sau moi 30 giay
            time.sleep(30)


def start_background_scheduler():
    """Ham tien ich de khoi dong scheduler."""
    scheduler = MarketAutopilotScheduler.get_instance()
    scheduler.start()
    return scheduler