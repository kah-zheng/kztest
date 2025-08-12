pipeline {
  agent any

  environment {
    AWS_REGION      = 'ap-southeast-1'       // TODO: set your region
    AWS_ACCOUNT_ID  = '405937588543'         // TODO: set your AWS account ID
    ECR_REPO        = 'kztest'                // TODO: set your ECR repo name (must exist)
    IMAGE           = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}"
    K8S_NAMESPACE   = 'kztest-staging'        // TODO: set your target namespace
    APP_NAME        = 'kztest'                // TODO: app name (used by k8s objects)
    PROD_NAMESPACE = 'kztest-prod'     // TODO: set your prod namespace
  }

  options {
    timestamps()
    buildDiscarder(logRotator(numToKeepStr: '20'))
  }

  stages {
    stage('Checkout') {
      steps { checkout scm }
    }

    stage('Unit tests') {
      steps {
        sh '''
          export PYTHONPATH="$WORKSPACE"
          pip install -r app/requirements.txt
          pytest -q
        '''
      }
    }    

    stage('Build image') {
      steps {
        sh '''
          docker version || true
          docker build -t ${IMAGE}:${BUILD_NUMBER} ./app
        '''
      }
    }

    stage('Login to ECR & Push') {
      steps {
        withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', credentialsId: 'aws-creds']]) {
          sh '''
            aws ecr describe-repositories --repository-names ${ECR_REPO} --region ${AWS_REGION} >/dev/null 2>&1 ||                       aws ecr create-repository --repository-name ${ECR_REPO} --region ${AWS_REGION}

            aws ecr get-login-password --region ${AWS_REGION} |                       docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

            docker push ${IMAGE}:${BUILD_NUMBER}
            docker tag ${IMAGE}:${BUILD_NUMBER} ${IMAGE}:latest
            docker push ${IMAGE}:latest
          '''
        }
      }
    }

    stage('Deploy to EKS (staging)') {
      steps {
        withAWS(credentials: 'aws-creds', region: env.AWS_REGION) {   // ensures aws-iam auth works
          withCredentials([file(credentialsId: 'kubeconfig-staging', variable: 'KUBECFG')]) {
            sh '''
              set -e
              export KUBECONFIG="$KUBECFG"
    
              kubectl create namespace ${K8S_NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
    
              sed -e "s|__IMAGE__|${IMAGE}:${BUILD_NUMBER}|g" \
                  -e "s|__APP__|${APP_NAME}|g" \
                  -e "s|__NS__|${K8S_NAMESPACE}|g" k8s/deployment.yaml | kubectl apply -f -
    
              sed -e "s|__APP__|${APP_NAME}|g" \
                  -e "s|__NS__|${K8S_NAMESPACE}|g" k8s/service.yaml | kubectl apply -f -
    
              kubectl -n ${K8S_NAMESPACE} rollout status deploy/${APP_NAME} --timeout=120s
            '''
          }
        }
      }
    }
    stage('Approve promotion to PROD') {
      steps {
        timeout(time: 15, unit: 'MINUTES') {
          input message: "Promote build ${BUILD_NUMBER} to PROD?", ok: 'Promote'
        }
      }
    }
    stage('Deploy to EKS (Prod)') {
      steps {
        withAWS(credentials: 'aws-creds', region: env.AWS_REGION) {   // ensures aws-iam auth works
          withCredentials([file(credentialsId: 'kubeconfig-staging', variable: 'KUBECFG')]) {
            sh '''
              set -e
              export KUBECONFIG="$KUBECFG"
    
              kubectl create namespace ${PROD_NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -
    
              sed -e "s|__IMAGE__|${IMAGE}:${BUILD_NUMBER}|g" \
                  -e "s|__APP__|${APP_NAME}|g" \
                  -e "s|__NS__|${PROD_NAMESPACE}|g" k8s/deployment.yaml | kubectl apply -f -
    
              sed -e "s|__APP__|${APP_NAME}|g" \
                  -e "s|__NS__|${PROD_NAMESPACE}|g" k8s/service.yaml | kubectl apply -f -
    
              kubectl -n ${PROD_NAMESPACE} rollout status deploy/${APP_NAME} --timeout=120s
            '''
          }
        }
      }
    }
  }

  post {
    success { echo "✅ Deployed ${APP_NAME} to namespace ${K8S_NAMESPACE}" }
    failure { echo "❌ Build failed. Check the logs." }
  }
}
