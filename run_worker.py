"""
run_worker.py - Tien trinh nen chay song song giup bot luon quet va tu hoc dung gio
ke ca khi khong co ai mo trinh duyet Streamlit web.
"""
import time
import os
import sys
from automation.scheduler import MarketAutopilotScheduler

def main():
    print("[Worker] Khoi dong tien trinh quet tu dong nen (Autopilot Worker)...")
    scheduler = MarketAutopilotScheduler.get_instance()
    scheduler.start()
    
    # Giu tien trinh luon song
    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        print("[Worker] Dung tien trinh worker.")

if __name__ == "__main__":
    main()
