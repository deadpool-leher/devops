pipeline {
    agent any
    options {
        timestamps()
        // agar log lebih rapi
    }

    environment {
        // Ganti nama script jika di repo bernama lain, atau set di Jenkins job
        SCRIPT_FILE = "monitor.py"
        VENV_DIR = ".venv"
    }

    stages {
        stage('Checkout') {
            steps {
                echo "[GIT] Checkout repository..."
                checkout scm
            }
        }

        stage('Setup virtualenv & deps') {
            steps {
                echo "[SETUP] Membuat virtual environment jika belum ada, lalu install deps..."
                sh '''
                    set -e
                    echo "Working dir: $(pwd)"
                    echo "List files:"
                    ls -la

                    # cek python3
                    if ! command -v python3 >/dev/null 2>&1; then
                        echo "ERROR: python3 tidak ditemukan pada agent. Install python3 atau gunakan agent lain."
                        exit 1
                    fi

                    # buat venv jika belum ada
                    if [ ! -d "${VENV_DIR}" ]; then
                        echo "Membuat ${VENV_DIR}..."
                        python3 -m venv ${VENV_DIR}
                    else
                        echo "${VENV_DIR} sudah ada, melewatkan pembuatan."
                    fi

                    # cek file activate
                    if [ ! -f "${VENV_DIR}/bin/activate" ]; then
                        echo "ERROR: ${VENV_DIR}/bin/activate tidak ditemukan setelah pembuatan venv."
                        exit 1
                    fi

                    # aktifkan venv untuk perintah berikut di blok sh ini
                    . ${VENV_DIR}/bin/activate

                    # upgrade pip dan install requirements jika ada
                    pip install --upgrade pip setuptools wheel

                    if [ -f requirements.txt ]; then
                        echo "Menginstall dependencies dari requirements.txt..."
                        pip install -r requirements.txt
                    else
                        echo "requirements.txt tidak ditemukan — melewatkan install deps."
                    fi

                    # tunjukkan pip list singkat
                    pip --version || true
                    pip list --format=columns | sed -n '1,20p' || true
                '''
            }
        }

        stage('Run script') {
            steps {
                echo "[RUN] Menjalankan script Python..."
                // setiap sh invocation baru harus activate venv lagi
                sh '''
                    set -e
                    if [ ! -f "${VENV_DIR}/bin/activate" ]; then
                        echo "ERROR: ${VENV_DIR}/bin/activate tidak ada. Pastikan stage Setup berjalan sukses."
                        exit 1
                    fi

                    . ${VENV_DIR}/bin/activate

                    echo "Menjalankan: python3 ${SCRIPT_FILE}"
                    if [ ! -f "${SCRIPT_FILE}" ]; then
                        echo "WARNING: ${SCRIPT_FILE} tidak ditemukan di workspace. Cek nama file."
                        exit 1
                    fi

                    # contoh menjalankan, redirect log ke file agar bisa diarsipkan
                    python3 ${SCRIPT_FILE} > monitor.log 2>&1 || {
                        echo "Script keluar dengan kode error: $?"
                        # tetap arsipkan log untuk debugging
                        exit 1
                    }
                '''
            }
        }
    }

    post {
        always {
            echo "[POST] Mengarsipkan artefak dan menunjukkan beberapa info..."
            sh 'echo "Build finished at: $(date)"'
            // arsip log dan file lain bila ada
            archiveArtifacts artifacts: 'monitor.log,*.log', allowEmptyArchive: true
            // tampilkan beberapa baris log agar mudah debugging di job console
            sh '''
                echo "---- tail monitor.log (up to 200 lines) ----"
                if [ -f monitor.log ]; then
                    tail -n 200 monitor.log || true
                else
                    echo "monitor.log tidak ada."
                fi
            '''
        }
        failure {
            echo "[POST] Build gagal — cek console output dan monitor.log"
        }
    }
}
