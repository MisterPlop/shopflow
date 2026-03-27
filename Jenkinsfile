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
                sh '''
                    pip install --upgrade pip -q
                    pip install -r requirements.txt -q
                    echo "Dépendances installées"
                '''
            }
        }

        stage('Lint') {
            steps {
                sh '''
                    flake8 app/ \
                        --max-line-length=100 \
                        --exclude=__init__.py \
                        --format=default
                '''
            }
            post {
                failure {
                    echo 'Lint échoué — corriger les erreurs PEP8'
                }
            }
        }

        stage('Unit Tests') {
            steps {
                sh '''
                    pytest tests/unit/ \
                        -v \
                        -m unit \
                        --junitxml=junit-unit.xml \
                        --no-cov
                '''
            }
            post {
                always {
                    junit 'junit-unit.xml'
                }
            }
        }

        stage('Integration Tests') {
            steps {
                sh '''
                    pytest tests/integration/ \
                        -v \
                        -m integration \
                        --junitxml=junit-integration.xml \
                        --no-cov
                '''
            }
            post {
                always {
                    junit 'junit-integration.xml'
                }
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
                failure {
                    echo 'Coverage < 80% — ajouter des tests'
                }
            }
        }

        stage('Static Analysis') {
            steps {
                sh '''
                    pip install pylint bandit -q
                    pylint app/ \
                        --output-format=parseable \
                        --exit-zero \
                        > pylint-report.txt || true
                    echo "Pylint terminé"

                    bandit -r app/ \
                        -f json \
                        -o bandit-report.json \
                        --exit-zero

                    python3 -c "
import json, sys
data = json.load(open('bandit-report.json'))
high = [r for r in data.get('results',[]) if r['issue_severity'] == 'HIGH']
if high:
    print(f'BANDIT: {len(high)} vuln HIGH détectée(s)')
    sys.exit(1)
print('BANDIT: aucune vulnérabilité HIGH')
"
                '''
            }
        }

        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv('SonarQube') {
                    sh '''
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
                timeout(time: 5, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        stage('Build Docker') {
            steps {
                script {
                    env.IMAGE_TAG = sh(
                        script: 'git rev-parse --short HEAD',
                        returnStdout: true
                    ).trim()
                    echo "Build image shopflow:${env.IMAGE_TAG}"
                    sh "docker build -t shopflow:${env.IMAGE_TAG} ."
                }
            }
        }

        stage('Deploy Staging') {
            when {
                branch 'main'
            }
            steps {
                sh '''
                    export IMAGE_TAG=${IMAGE_TAG}
                    docker compose -f docker-compose.staging.yml up -d --remove-orphans
                    docker compose -f docker-compose.staging.yml ps
                    sleep 5
                    curl -f http://localhost:8001/health || exit 1
                    echo "Staging déployé et opérationnel"
                '''
            }
            post {
                failure {
                    sh 'docker compose -f docker-compose.staging.yml logs --tail=50'
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'junit-*.xml,coverage.xml,bandit-report.json',
                allowEmptyArchive: true
            sh 'docker system prune -f --filter label=stage=ci || true'
        }
        success {
            echo "Pipeline OK — ShopFlow:${env.IMAGE_TAG} déployé"
        }
        failure {
            echo 'Pipeline FAILED — voir les logs ci-dessus'
        }
        unstable {
            echo 'Pipeline instable — des tests ont échoué'
        }
    }
}