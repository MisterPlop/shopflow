pipeline {
    agent {
        docker {
            image 'python:3.11-slim'
            args '--user root -v /var/run/docker.sock:/var/run/docker.sock --network shopflow_default'
        }
    }

    environment {
        APP_NAME = 'shopflow'
        // IMAGE_TAG est défini dynamiquement au stage Build
    }

    stages {
        stage('Install') {
            steps {
                sh '''
                    apt-get update -qq && apt-get install -y git -qq
                    pip install --upgrade pip -q
                    pip install -r requirements.txt -q
                '''
            }
        }

        stage('Lint') {
            steps {
                sh 'flake8 app/ --max-line-length=100 --exclude=__init__.py --format=default --exit-zero || true'
            }
            post {
                failure { echo 'Lint échoué — corriger les erreurs PEP8' }
            }
        }

        stage('Unit Tests') {
            steps {
                sh 'pytest tests/unit/ -v --junitxml=junit-unit.xml --no-cov'
            }
            post {
                always { junit 'junit-unit.xml' }
            }
        }

        stage('Integration Tests') {
            steps {
                sh 'pytest tests/integration/ -v --junitxml=junit-integration.xml --no-cov'
            }
            post {
                always { junit 'junit-integration.xml' }
            }
        }

        stage('Coverage') {
            steps {
                sh '''
                    pytest tests/ \
                        --cov=app \
                        --cov-report=xml:coverage.xml \
                        --cov-report=html:htmlcov \
                        --cov-report=term-missing \
                        --cov-fail-under=80 \
                        --junitxml=junit-report.xml
                '''
            }
            post {
                always {
                    publishHTML(target: [
                        allowMissing: false,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'htmlcov',
                        reportFiles: 'index.html',
                        reportName: 'Coverage Report'
                    ])
                }
            }
        }

        stage('Static Analysis') {
            steps {
                sh '''
                    pip install pylint bandit -q
                    pylint app/ --output-format=parseable --exit-zero > pylint-report.txt || true
                    bandit -r app/ -f json -o bandit-report.json --exit-zero
                    python3 -c "
import json, sys
data = json.load(open('bandit-report.json'))
high = [r for r in data.get('results',[]) if r['issue_severity'] == 'HIGH']
if high:
    print(f'BANDIT: {len(high)} vuln HIGH détectée(s)')
    sys.exit(1)
"
                '''
            }
        }

        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv('sonarqube') {
                    sh '''
                        # Utilisation du binaire si installé ou via pip
                        pip install pysonar-scanner -q
                        pysonar-scanner \
                            -Dsonar.projectKey=shopflow \
                            -Dsonar.sources=app \
                            -Dsonar.tests=tests \
                            -Dsonar.python.coverage.reportPaths=coverage.xml \
                            -Dsonar.python.pylint.reportPaths=pylint-report.txt
                    '''
                }
            }
        }

        stage('Quality Gate') {
            steps {
                timeout(time: 1, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: false
                }
            }
        }

        stage('Build Docker') {
            steps {
                script {
                    env.IMAGE_TAG = env.GIT_COMMIT.take(7)
                    echo "Build image shopflow:${env.IMAGE_TAG}"

                    sh '''
                        apt-get update && apt-get install -y docker.io docker-compose -q
                        docker build -t shopflow:$IMAGE_TAG .
                    '''
                }
            }
        }

        stage('Deploy Staging') {
           when {
                expression {
                    return env.GIT_BRANCH ==~ /.*main/
                }
            }
            steps {
                sh '''
                    docker compose -f docker-compose.staging.yml up -d --remove-orphans
                    apt install curl -q -y
                    sleep 5
                    curl -f http://localhost:8001/health || exit 1
                    echo "Staging déployé avec succès"
                '''
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'junit-*.xml,coverage.xml,bandit-report.json', allowEmptyArchive: true
        }
    }
}