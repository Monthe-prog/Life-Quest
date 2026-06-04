pipeline {
  agent any

  options {
    timestamps()
    disableConcurrentBuilds()
    buildDiscarder(logRotator(numToKeepStr: '20'))
  }

  environment {
    APP_DIR = '/opt/life-quest'
    DEPLOY_HOST = '158.220.90.106'
    DEPLOY_USER = 'deploy'
    SSH_CREDENTIALS_ID = 'life-quest-vps-ssh'
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Install Frontend Dependencies') {
      steps {
        sh 'cp .env.example .env'
        sh 'npm ci'
      }
    }

    stage('Test') {
      parallel {
        stage('Frontend Typecheck') {
          steps {
            sh 'npm run typecheck'
          }
        }

        stage('Backend Compile') {
          steps {
            sh 'python3 -m compileall apps/backend/app'
          }
        }
      }
    }

    stage('Build') {
      steps {
        sh 'docker compose config'
        sh 'docker compose build frontend backend'
      }
    }

    stage('Deploy') {
      when {
        branch 'main'
      }
      steps {
        sshagent(credentials: [env.SSH_CREDENTIALS_ID]) {
          sh '''
            ssh -o StrictHostKeyChecking=accept-new ${DEPLOY_USER}@${DEPLOY_HOST} "
              set -e
              cd ${APP_DIR}
              git fetch origin main
              git reset --hard origin/main
              docker compose up -d --build
              docker compose exec -T backend alembic upgrade head
              docker compose ps
            "
          '''
        }
      }
    }
  }

  post {
    success {
      echo 'CI/CD pipeline completed successfully.'
    }
    failure {
      echo 'CI/CD pipeline failed. Check the Jenkins stage logs.'
    }
  }
}
