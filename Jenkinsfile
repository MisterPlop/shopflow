pipeline {
    agent {
        docker {
            image 'python:3.11-slim'
            args '--user root -v /var/run/docker.sock:/var/run/docker.sock'
        }
    }

    environment {
        APP_NAME = 'shopflow'
    }

    stages {
        stage('Install') {
            steps {
                sh 'pip install --upgrade pip -q && pip install -r requirements.txt -q'
            }
        }

        stage('Lint') {
            steps {
                sh 'flake8 app/ --max-line-length=100 --exclude=__init__.py --exit-zero'
            }
        }

        stage('Unit Tests') {
            steps {
                sh 'pytest tests/unit/ -v -m unit --junitxml=junit-unit.xml --no-cov'
            }
            post { always { junit 'junit-unit.xml' } }
        }

        stage('Build Docker') {
            steps {
                script {
                    env.IMAGE_TAG = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
                    sh "docker build -t shopflow:${env.IMAGE_TAG} ."
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'junit-*.xml,coverage.xml,bandit-report.json', allowEmptyArchive: true
            // Suppression du docker prune ici car l'image python ne peut pas l'exécuter
            echo "Fin du pipeline pour ${env.IMAGE_TAG}"
        }
    }
}