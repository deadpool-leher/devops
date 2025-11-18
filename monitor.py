import os
import time
import requests
import logging
import socket
import subprocess
import json
import traceback
import threading
from datetime import datetime
import sys

# ==== KONFIGURASI ====
MONITOR_PID_FILE = "monitorTeman.pid"
MONITOR_LOG_FILE = "monitorTeman.log"
LOCK_FILE = "monitorTeman.lock"
CHECK_INTERVAL = 3  # detik
MAX_RETRY = 5  # batas retry pada error jaringan
LOG_PATHS = ["/var/log/auth.log", "/var/log/secure"]  # file log SSH Linux
IGNORE_USERS = ["root", "Ubuntu"]  # User yang boleh diabaikan
FONNTE_TOKEN = "qgYnAhKSR8NtymzySksJ"  # Token Fonnte
ADMIN_NUMBER = "628998273221"  # Nomor tujuan pesan

# ==== SETUP LOGGING ====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

def ensure_log_file():
    """Pastikan FileHandler aktif agar error selalu masuk ke monitor.log."""
    handler_exists = any(
        isinstance(h, logging.FileHandler) for h in logging.getLogger().handlers
    )
    if not handler_exists:
        fh = logging.FileHandler(MONITOR_LOG_FILE)
        fh.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        fh.setFormatter(formatter)
        logging.getLogger().addHandler(fh)

ensure_log_file()

def tail_file(path):
    """Generator untuk membaca baris baru dari file log."""
    try:
        with open(path, "r", errors="ignore") as f:
            f.seek(0, os.SEEK_END)
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.5)
                    continue
                yield line.strip()
    except Exception:
        logging.exception(f"ERROR membaca file log: {path}")

def send_fonnte_message(text):
    """Mengirim pesan via API Fonnte."""
    url = "https://api.fonnte.com/send"
    payload = {
        "target": ADMIN_NUMBER,
        "message": text,
    }
    headers = {
        "Authorization": FONNTE_TOKEN,
    }
    retry = 0
    while retry < MAX_RETRY:
        try:
            r = requests.post(url, data=payload, headers=headers, timeout=10)
            if r.status_code == 200:
                logging.info(f"[FONNTE] Pesan terkirim: {text}")
                return True
            else:
                logging.warning(f"[FONNTE] Gagal ({r.status_code}): {r.text}")
        except Exception:
            logging.exception("[FONNTE] ERROR saat mengirim pesan")
        retry += 1
        time.sleep(2)
    return False

def analyze_with_gemini(text):
    """Analisis pesan login menggunakan Gemini (opsional)."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API)
        model = genai.GenerativeModel("gemini-1.5-flash")
        result = model.generate_content(f"Analisis keamanan: {text}")
        return result.text
    except Exception:
        logging.warning("[GEMINI] Analisis gagal (opsional).")
        return None

def monitor_logs():
    """Memonitor file log SSH."""
    logging.info("[MONITOR] Monitoring log SSH dimulai...")

    paths = [p for p in LOG_PATHS if os.path.exists(p)]
    logging.info(f"[MONITOR] Log yang ditemukan: {paths}")

    if not paths:
        logging.error("[MONITOR] Tidak ada file log SSH ditemukan!")
        return

    tails = [tail_file(p) for p in paths]

    for tail in tails:
        threading.Thread(target=lambda t=tail: process_log_stream(t), daemon=True).start()

    while True:
        time.sleep(1)

def process_log_stream(tailer):
    """Proses tiap baris log."""
    for line in tailer:
        if any(user in line for user in IGNORE_USERS):
            continue

        if "Accepted password" in line or "session opened" in line:
            send_fonnte_message(f"[LOGIN] Masuk SSH: {line}")

        if "Failed password" in line:
            send_fonnte_message(f"[FAILED] Gagal SSH: {line}")

def main():
    logging.info("[BotTeman] Monitoring Aktif...")
    monitor_logs()

# =============================
#         ENTRY POINT
# =============================
if __name__ == "__main__":
    logging.info("[BotTeman] Start program monitor.")

    # Kirim pesan startup (tidak boleh membuat crash)
    try:
        threading.Thread(
            target=lambda: send_fonnte_message(
                f"[BotTeman] Monitor aktif di {socket.gethostname()}"
            ),
            daemon=True,
        ).start()
    except Exception:
        logging.exception("ERROR mengirim pesan startup")

    # Jalankan main() dengan try/except agar error tercatat
    try:
        main()
    except Exception as e:
        logging.error("=== ERROR FATAL PADA monitor.py ===")
        logging.exception(e)
        print("\n=========================\nERROR FATAL TERJADI!\n=========================")
        traceback.print_exc()
        sys.exit(1)
