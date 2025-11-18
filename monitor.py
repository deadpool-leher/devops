import os
import time
import requests
import logging
import socket
import traceback
import threading
from datetime import datetime
import sys

LOG_FILE = "monitorTeman.log"
FONNTE_TOKEN = "qgYnAhKSR8NtymzySksJ"
ADMIN_NUMBER = "628998273221"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

def send_fonnte(text):
    try:
        r = requests.post(
            "https://api.fonnte.com/send",
            headers={"Authorization": FONNTE_TOKEN},
            data={"target": ADMIN_NUMBER, "message": text},
            timeout=10
        )
        logging.info(f"[FONNTE] status={r.status_code}")
    except Exception as e:
        logging.error(f"[FONNTE ERROR] {e}")

def main():
    logging.info("Monitor dimulai...")
    send_fonnte(f"Monitor aktif di {socket.gethostname()}")

    # Program dummy biar tidak crash
    while True:
        logging.info("Monitor berjalan normal...")
        time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.error("ERROR FATAL TERJADI!")
        traceback.print_exc()
        sys.exit(0)  # jangan exit 1
