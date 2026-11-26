"""
run_worker.py - Tien trinh nen chay song song giup bot luon quet va tu hoc dung gio
ke ca khi khong co ai mo trinh duyet Streamlit web.
"""
import time
import os
import sys
from dotenv import load_dotenv

load_dotenv()
from automation.scheduler import MarketAutopilotScheduler

def main():
    # This process is the only production owner of the scheduler.
    os.environ.setdefault("RUN_SCHEDULER", "true")
    print("[Worker] Khoi dong tien trinh quet tu dong nen (Autopilot Worker)...")
    scheduler = MarketAutopilotScheduler.get_instance()
    scheduler.start()

    try:
        while True:
            # Keep the parent process alive; the scheduler thread may be daemonized.
            time.sleep(30)
            if not scheduler.is_running:
                print("[Worker] Scheduler stopped; restarting it.")
                scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        scheduler.is_running = False
        print("[Worker] Dung tien trinh worker.")

if __name__ == "__main__":
    main()


