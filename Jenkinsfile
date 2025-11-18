pipeline {
    agent any
    options { timestamps() }

    environment {
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
                echo "[SETUP] Membuat/merecreate virtualenv jika perlu..."
                sh '''
                    set -e
                    echo "Working dir: $(pwd)"
                    ls -la

                    if ! command -v python3 >/dev/null 2>&1; then
                        echo "ERROR: python3 tidak ditemukan."
                        exit 1
                    fi

                    # jika .venv tidak ada atau activate tidak ada -> hapus & buat ulang
                    if [ ! -d "${VENV_DIR}" ] || [ ! -f "${VENV_DIR}/bin/activate" ]; then
                        echo "Merecreate ${VENV_DIR} karena tidak lengkap atau tidak ada..."
                        rm -rf ${VENV_DIR}
                        python3 -m venv ${VENV_DIR}
                    else
                        echo "${VENV_DIR} dan activate ditemukan, melewatkan recreate."
                    fi

                    # pastikan activate ada sekarang
                    if [ ! -f "${VENV_DIR}/bin/activate" ]; then
                        echo "ERROR: ${VENV_DIR}/bin/activate tidak ditemukan setelah pembuatan."
                        ls -la ${VENV_DIR} || true
                        exit 1
                    fi

                    # aktifkan di dalam blok sh ini
                    . ${VENV_DIR}/bin/activate

                    pip install --upgrade pip setuptools wheel

                    if [ -f requirements.txt ]; then
                        pip install -r requirements.txt
                    else
                        echo "requirements.txt tidak ditemukan — melewatkan install deps."
                    fi

                    pip --version || true
                '''
            }
        }

        stage('Run script') {
            steps {
                echo "[RUN] Menjalankan script Python..."
                sh '''
                    set -e
                    . ${VENV_DIR}/bin/activate

                    if [ ! -f "${SCRIPT_FILE}" ]; then
                        echo "ERROR: ${SCRIPT_FILE} tidak ditemukan."
                        exit 1
                    fi

                    python3 ${SCRIPT_FILE} > monitor.log 2>&1 || {
                        echo "Script keluar dengan kode error: $?"
                        exit 1
                    }
                '''
            }
        }
    }

    post {
        always {
            echo "[POST] Mengarsipkan artefak..."
            archiveArtifacts artifacts: 'monitor.log,*.log', allowEmptyArchive: true
            sh '''
                echo "---- tail monitor.log (up to 200 lines) ----"
                if [ -f monitor.log ]; then
                    tail -n 200 monitor.log || true
                else
                    echo "monitor.log tidak ada."
                fi
            '''
        }
    }
}
