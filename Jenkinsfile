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
                checkout scm
            }
        }

        stage('Setup Virtualenv') {
            steps {
                sh '''
                    set -e

                    # Hapus VENV lama biar bersih
                    rm -rf .venv

                    # Buat ulang VENV
                    python3 -m venv .venv

                    # Aktivasi
                    . .venv/bin/activate

                    # Install PIP + requirements
                    pip install --upgrade pip setuptools wheel

                    if [ -f requirements.txt ]; then
                        pip install -r requirements.txt
                    fi
                '''
            }
        }

        stage('Run Script (Tidak Gagal)') {
            steps {
                sh '''
                    # Jangan hentikan build meskipun script error
                    set +e

                    . .venv/bin/activate

                    python3 -u monitor.py > monitorTeman.log 2>&1

                    echo "===== LOG OUTPUT ====="
                    tail -n 200 monitorTeman.log || true

                    echo "===== EXIT CODE (abaikan) ====="
                    echo $?
                '''
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'monitorTeman.log', allowEmptyArchive: true
        }
    }
}
