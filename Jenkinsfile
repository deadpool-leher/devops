pipeline {
  agent any
  options { timestamps() }

  environment {
    VENV_DIR = ".venv"
    SCRIPT = "monitor.py"
    PID_FILE = "monitorTeman.pid"
  }

  stages {
    stage('Checkout') {
      steps { checkout scm }
    }

    stage('Setup venv & deps') {
      steps {
        sh '''
          set -e
          # buat/bersihkan venv agar konsisten
          rm -rf ${VENV_DIR}
          python3 -m venv ${VENV_DIR}
          . ${VENV_DIR}/bin/activate
          pip install --upgrade pip setuptools wheel
          if [ -f requirements.txt ]; then
            pip install -r requirements.txt
          fi
        '''
      }
    }

    stage('Start monitor (daemon)') {
      steps {
        // jangan fail build jika start gagal; cukup tunjukkan log
        sh '''
          set +e
          . ${VENV_DIR}/bin/activate

          # jika PID ada dan process hidup, skip start
          if [ -f ${PID_FILE} ]; then
            OLD_PID=$(cat ${PID_FILE} 2>/dev/null || true)
            if [ -n "$OLD_PID" ] && kill -0 $OLD_PID 2>/dev/null; then
              echo "Monitor sudah berjalan (PID $OLD_PID) — skip start."
              exit 0
            else
              echo "PID file ada tapi process tidak hidup — menghapus PID file."
              rm -f ${PID_FILE}
            fi
          fi

          # start monitor sebagai background process (nohup) dan simpan pid
          nohup ${VENV_DIR}/bin/python3 ${SCRIPT} >> monitorTeman.log 2>&1 &
          echo $! > ${PID_FILE}
          echo "Monitor dimulai dengan PID $(cat ${PID_FILE})"
          sleep 1
          echo "==== tail monitorTeman.log (last 200 lines) ===="
          tail -n 200 monitorTeman.log || true
        '''
      }
    }
  }

  post {
    always {
      archiveArtifacts artifacts: 'monitorTeman.log,monitorTeman.pid', allowEmptyArchive: true
      sh 'echo "Done. (logs archived)" || true'
    }
  }
}
