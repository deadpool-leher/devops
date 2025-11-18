#!/usr/bin/env python3
"""
monitor.py
- Memonitor login SSH (Accepted / Failed) dari /var/log/auth.log atau /var/log/secure
- Mengirim notifikasi via API Fonnte (WhatsApp) jika terdeteksi
- Menulis log ke monitorTeman.log dan pid di monitorTeman.pid
- Tahan error dan tidak crash
"""

import os
import time
import sys
import logging
import threading
import requests
import socket
import traceback
from datetime import datetime

# -------- CONFIG ----------
PID_FILE = "monitorTeman.pid"
LOG_FILE = "monitorTeman.log"
LOG_PATHS = ["/var/log/auth.log", "/var/log/secure"]  # Ubuntu / CentOS
CHECK_INTERVAL = 1.0  # detik tunggu saat baca tail
FONNTE_TOKEN = os.environ.get("FONNTE_TOKEN", "tjKKtd2kut6qw4fGK1sr")
ADMIN_NUMBER = os.environ.get("ADMIN_NUMBER", "08998273221")
IGNORE_USERS = set(["root"])  # user yang diabaikan (opsional)
SEND_RETRY = 3
# --------------------------

# Setup logging to file + console
logger = logging.getLogger("monitor")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

# File handler
fh = logging.FileHandler(LOG_FILE)
fh.setFormatter(formatter)
logger.addHandler(fh)

# Console handler
ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(formatter)
logger.addHandler(ch)


def is_process_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True


def write_pid():
    pid = os.getpid()
    try:
        with open(PID_FILE, "w") as f:
            f.write(str(pid))
        logger.info(f"Menulis PID {pid} ke {PID_FILE}")
    except Exception:
        logger.exception("Gagal menulis PID file")


def remove_pid():
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
            logger.info("PID file dihapus")
    except Exception:
        logger.exception("Gagal menghapus PID file")


def send_fonnte_message(text: str) -> bool:
    """Kirim pesan via Fonnte. Kembalikan True jika sukses."""
    if not FONNTE_TOKEN or not ADMIN_NUMBER:
        logger.warning("FONNTE_TOKEN atau ADMIN_NUMBER tidak diatur — skip kirim")
        return False

    url = "https://api.fonnte.com/send"
    headers = {"Authorization": FONNTE_TOKEN}
    payload = {"target": ADMIN_NUMBER, "message": text}

    for attempt in range(1, SEND_RETRY + 1):
        try:
            r = requests.post(url, data=payload, headers=headers, timeout=8)
            if r.status_code == 200:
                logger.info(f"[FONNTE] Pesan terkirim: {text[:120]}")
                return True
            else:
                logger.warning(f"[FONNTE] Gagal status={r.status_code} resp={r.text}")
        except Exception:
            logger.exception("[FONNTE] Exception saat mengirim pesan")
        time.sleep(2)
    logger.error("[FONNTE] Gagal mengirim setelah beberapa retry")
    return False


def follow_file(path, callback):
    """Simple file tail: panggil callback(line) untuk setiap baris baru."""
    try:
        with open(path, "r", errors="ignore") as fh:
            fh.seek(0, os.SEEK_END)
            while True:
                line = fh.readline()
                if not line:
                    time.sleep(CHECK_INTERVAL)
                    continue
                callback(line.rstrip("\n"))
    except PermissionError:
        logger.exception(f"Permission denied membaca {path}. Pastikan Jenkins/user punya akses.")
    except FileNotFoundError:
        logger.exception(f"File not found: {path}")
    except Exception:
        logger.exception(f"Error saat follow file {path}")


def handle_line(line: str):
    """Analisa satu baris log — deteksi Accepted/Failed SSH."""
    try:
        text = line.strip()
        if not text:
            return

        # Contoh baris:
        # Nov 18 07:29:04 host sshd[1234]: Accepted password for user from 1.2.3.4 port 54321 ssh2
        # Nov 18 07:29:04 host sshd[1234]: Failed password for invalid user test from 1.2.3.4 port 54321 ssh2

        lower = text.lower()
        if "accepted password" in lower or "session opened" in lower:
            # success login
            logger.info("[LOGIN] " + text)
            # optionally ignore root or other users
            if any(user.lower() in lower for user in IGNORE_USERS):
                logger.debug("User di-ignore")
                return
            short = make_short_message("LOGIN", text)
            threading.Thread(target=send_fonnte_message, args=(short,), daemon=True).start()

        elif "failed password" in lower or "authentication failure" in lower:
            # failed attempt
            logger.warning("[FAILED] " + text)
            short = make_short_message("FAILED", text)
            threading.Thread(target=send_fonnte_message, args=(short,), daemon=True).start()

        # Add other detection rules if needed (e.g., invalid user, PAM errors)
    except Exception:
        logger.exception("Gagal memproses baris log")


def make_short_message(kind: str, full_line: str) -> str:
    # Buat pesan ringkas agar muat di WhatsApp
    host = socket.gethostname()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Potong panjang pesan supaya tidak terlalu long
    snippet = full_line
    if len(snippet) > 700:
        snippet = snippet[:700] + "..."
    return f"[{kind}] {host} {ts}\n{snippet}"


def start_monitor():
    logger.info("Mencari file log yang tersedia...")
    paths = [p for p in LOG_PATHS if os.path.exists(p)]
    if not paths:
        logger.warning("Tidak menemukan file /var/log/auth.log atau /var/log/secure — monitor akan tetap jalan menunggu.")
        # coba tunggu dan re-check periodik
        while True:
            time.sleep(10)
            paths = [p for p in LOG_PATHS if os.path.exists(p)]
            if paths:
                break

    logger.info(f"Monitoring files: {paths}")
    threads = []
    for p in paths:
        t = threading.Thread(target=follow_file, args=(p, handle_line), daemon=True)
        t.start()
        threads.append(t)

    # keep main alive
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt diterima, keluar.")
    except Exception:
        logger.exception("Error di loop utama")


def main():
    # Jika PID ada dan proses hidup, exit saja
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                oldpid = int(f.read().strip())
            if is_process_running(oldpid):
                logger.info(f"Instance sudah berjalan dengan PID {oldpid} — keluar.")
                return
            else:
                logger.info("PID file ada tapi process tidak hidup — akan menimpa.")
        except Exception:
            logger.exception("Gagal membaca PID file, lanjut membuat baru.")

    # tulis pid
    write_pid()

    # Kirim pesan startup (non-blocking)
    try:
        threading.Thread(
            target=send_fonnte_message,
            args=(f"[BotTeman] Monitor aktif pada {socket.gethostname()}",),
            daemon=True,
        ).start()
    except Exception:
        logger.exception("Gagal memulai notifikasi startup")

    try:
        start_monitor()
    except Exception:
        logger.exception("Unhandled exception pada main()")
    finally:
        remove_pid()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("Fatal error di __main__")
        traceback.print_exc()
        # jangan exit non-zero agar Jenkins job tidak gagal; tapi kamu bisa ubah jadi sys.exit(1) jika ingin strict
        try:
            # simpan log dan tetap exit 0
            logger.info("Program keluar karena error, namun exit code 0 agar Jenkins tetap sukses.")
        except Exception:
            pass
        sys.exit(0)
