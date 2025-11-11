pipeline {
    agent any
    options { timestamps() }

    // Triggers: GitHub webhook + fallback poll
    triggers {
        githubPush()
        pollSCM('H/2 * * * *')
    }

    // Keep non-secret defaults here; secret values should be stored as Jenkins Credentials
    environment {
        SCRIPT_FILE = "monitor.py"
        // NOTE: do NOT store tokens here in plaintext. Use credentials below (with 'credentials' block).
        //FONNTE_TOKEN = "qgYnAhKSR8NtymzySksJ"
        //GEMINI_API_KEY = "AIzaSy..."
        GEMINI_MODEL = "gemini-2.5-flash"
    }

    // Bind secret credentials (replace IDs with your Jenkins credential IDs)
    // - fonnte_token_id : Secret text (Fonnte token)
    // - gemini_api_key_id: Secret text (Gemini API key)
    // - fonnte_targets_id: Username/password or plain text (if you want)
    // If you don't have credentials set, create them in Jenkins and replace the IDs below.
    credentials {
        string(credentialsId: 'fonnte_token_id', variable: 'FONNTE_TOKEN')
        string(credentialsId: 'gemini_api_key_id', variable: 'GEMINI_API_KEY')
        string(credentialsId: 'fonnte_targets_id', variable: 'FONNTE_TARGETS')
    }

    stages {
        stage('Checkout') {
            steps {
                echo "[CHECKOUT] Ambil source code dari repo..."
                checkout scm
                sh '''
                  echo "[CHECKOUT] Workspace: ${WORKSPACE}"
                  ls -la "${WORKSPACE}"
                  if [ ! -f "${WORKSPACE}/${SCRIPT_FILE}" ]; then
                    echo "[CHECKOUT] ERROR: ${SCRIPT_FILE} tidak ditemukan di repo!"
                    ls -la "${WORKSPACE}"
                    exit 1
                  fi
                '''
            }
        }

        stage('Setup Python') {
            steps {
                sh '''
                  set -euo pipefail
                  echo "[SETUP] Cek python3..."
                  if ! command -v python3 >/dev/null 2>&1; then
                    echo "[SETUP] ERROR: python3 tidak ditemukan pada node ini. Pasang python3 sebelum melanjutkan."
                    exit 2
                  fi

                  # Cek apakah modul venv bisa digunakan
                  echo "[SETUP] Cek kemampuan venv..."
                  if ! python3 -c "import venv" >/dev/null 2>&1; then
                    echo "[SETUP] ERROR: modul 'venv' tidak tersedia. Di Debian/Ubuntu: apt-get install python3-venv"
                    exit 3
                  fi

                  cd "${WORKSPACE}"

                  # Buat venv kalau belum ada
                  if [ ! -d ".venv" ]; then
                    echo "[SETUP] Membuat virtual environment..."
                    python3 -m venv .venv
                  else
                    echo "[SETUP] Virtualenv sudah ada, skip pembuatan."
                  fi

                  # Aktifkan venv dan pasang deps
                  . .venv/bin/activate
                  echo "[SETUP] Python di venv: $(python -V)"
                  python -m pip install --upgrade pip
                  if [ -f requirements.txt ]; then
                    python -m pip install -r requirements.txt
                  else
                    python -m pip install requests python-dotenv || true
                  fi
                '''
            }
        }

        stage('Notify WhatsApp CI Start') {
            steps {
                sh '''
                  set -e
                  cd "${WORKSPACE}"
                  . .venv/bin/activate
                  python - <<'PY'
import os, socket, datetime, requests
HOSTNAME = socket.gethostname()
ts = datetime.datetime.now().isoformat()
msg = f"[BotTeman] Jenkins start: {HOSTNAME} @ {ts}. Script: {os.getenv('SCRIPT_FILE')}"

# Try to check Gemini connectivity quickly (best-effort)
gemini_ok = "not checked"
try:
    # If using google.generativeai, ensure package present and GEMINI_API_KEY set.
    key = os.getenv('GEMINI_API_KEY')
    if key:
        import google.generativeai as genai
        genai.configure(api_key=key)
        model = genai.GenerativeModel(os.getenv('GEMINI_MODEL', 'gemini-2.5-flash'))
        resp = model.generate_content("OK")
        text = getattr(resp, 'text', None)
        if text:
            gemini_ok = "OK"
        else:
            gemini_ok = "response_no_text"
    else:
        gemini_ok = "no_key"
except Exception as e:
    gemini_ok = f"error:{e}"

msg += "\\nGemini: " + gemini_ok

token = os.getenv('FONNTE_TOKEN')
targets = [t.strip() for t in os.getenv('FONNTE_TARGETS', '').split(',') if t.strip()]
if not token or not targets:
    print("[NOTIFY] Fonnte token or targets not configured; skipping notification.")
else:
    for t in targets:
        try:
            r = requests.post(
                "https://api.fonnte.com/send",
                headers={"Authorization": token},
                data={"target": t, "message": msg},
                timeout=10
            )
            print(f"[NOTIFY] Fonnte {t} {r.status_code}")
        except Exception as e:
            print("[NOTIFY] Fonnte error", e)
PY
                '''
            }
        }

        stage('Run Monitor') {
            steps {
                sh '''
                  set -euo pipefail
                  cd "${WORKSPACE}"
                  LOG_FILE="${WORKSPACE}/monitorTeman.log"
                  PID_FILE="${WORKSPACE}/monitorTeman.pid"
                  echo "[RUN] Menjalankan ${SCRIPT_FILE}..."

                  if [ ! -f "${WORKSPACE}/${SCRIPT_FILE}" ]; then
                    echo "[RUN] FAIL: ${SCRIPT_FILE} tidak ditemukan!"
                    exit 1
                  fi

                  # Stop existing PID if valid
                  if [ -f "${PID_FILE}" ]; then
                    OLD=$(cat "${PID_FILE}" || true)
                    if [ -n "$OLD" ] && kill -0 "$OLD" 2>/dev/null; then
                      echo "[RUN] Stop monitor lama (PID $OLD)..."
                      kill "$OLD" || true
                      sleep 1
                    fi
                    rm -f "${PID_FILE}" || true
                  fi

                  # Extra kill any lingering process with same script name (best-effort)
                  pkill -f "${WORKSPACE}/${SCRIPT_FILE}" 2>/dev/null || true
                  sleep 1

                  . .venv/bin/activate
                  echo "[RUN] Python: $(python -V)"

                  RUNNER="python -u ${WORKSPACE}/${SCRIPT_FILE}"
                  # Run in background with nohup+setsid so Jenkins won't kill it on finish
                  nohup setsid bash -lc "${RUNNER} > \"${LOG_FILE}\" 2>&1 < /dev/null" >/dev/null 2>&1 &
                  echo $! > "${PID_FILE}"
                  sleep 2

                  PID=$(cat "${PID_FILE}" || echo)
                  if [ -n "$PID" ] && ps -p "$PID" >/dev/null 2>&1; then
                    echo "[RUN] OK: ${SCRIPT_FILE} berjalan (PID=${PID})"
                  else
                    echo "[RUN] FAIL: Gagal menjalankan ${SCRIPT_FILE}, tail log:"
                    tail -n 200 "${LOG_FILE}" || true
                    exit 1
                  fi
                '''
            }
        }
    }

    post {
        always {
            echo "[POST] Arsipkan log..."
            archiveArtifacts artifacts: 'monitorTeman.log,monitorTeman.pid', allowEmptyArchive: true
        }
        success { echo "[POST] Build sukses." }
        failure { echo "[POST] Build gagal." }
    }
}
