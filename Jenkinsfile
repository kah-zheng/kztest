pipeline {
  agent any

  environment {
    AWS_REGION      = 'ap-southeast-1'
    AWS_ACCOUNT_ID  = '405937588543'
    ECR_REPO        = 'kztest'
    IMAGE           = "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}"
    K8S_NAMESPACE   = 'kztest-staging'
    APP_NAME        = 'kztest'
    PROD_NAMESPACE  = 'kztest-prod'   // still used by Argo Application (destination)
    // --- GitOps (Argo CD) settings ---
    GITOPS_REPO_URL = 'git@github.com:kah-zheng/kztest-gitops.git'   // <-- TODO
    GITOPS_BRANCH   = 'main'                                       // <-- adjust if needed
    GITOPS_PATH_PROD = 'envs/prod'                                 // path Argo app points to
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
          set -e
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
            set -e
            aws ecr describe-repositories --repository-names ${ECR_REPO} --region ${AWS_REGION} >/dev/null 2>&1 || \
              aws ecr create-repository --repository-name ${ECR_REPO} --region ${AWS_REGION}

            aws ecr get-login-password --region ${AWS_REGION} | \
              docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

            docker push ${IMAGE}:${BUILD_NUMBER}
            docker tag ${IMAGE}:${BUILD_NUMBER} ${IMAGE}:latest
            docker push ${IMAGE}:latest
          '''
        }
      }
    }

    // ----- Staging stays direct (kubectl) for now -----
    stage('Deploy to EKS (staging)') {
      steps {
        withAWS(credentials: 'aws-creds', region: env.AWS_REGION) {
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
          input message: "Promote build ${BUILD_NUMBER} to PROD via Argo CD (GitOps)?", ok: 'Promote'
        }
      }
    }

    // ----- PROD via GitOps: Jenkins commits the new image tag; Argo CD syncs -----
    stage('Promote via Argo CD (GitOps)') {
      steps {
        withCredentials([sshUserPrivateKey(credentialsId: 'gitops-deploy-key', keyFileVariable: 'GIT_SSH_KEY', usernameVariable: 'GIT_USER')]) {
          sh '''
            set -euo pipefail
            rm -rf gitops && mkdir -p gitops
            cd gitops
    
            # Trust GitHub host key
            mkdir -p ~/.ssh && chmod 700 ~/.ssh
            ssh-keyscan -T 10 -t rsa,ecdsa,ed25519 github.com >> ~/.ssh/known_hosts
            chmod 644 ~/.ssh/known_hosts
    
            eval $(ssh-agent -s)
            ssh-add "$GIT_SSH_KEY"
    
            # Clone GitOps repo
            git clone -b "${GITOPS_BRANCH}" "${GITOPS_REPO_URL}" .
            git config user.name "jenkins-bot"
            git config user.email "ci@example.com"
    
            TARGET_FILE="${GITOPS_PATH_PROD}/kustomization.yaml"
            TARGET_IMAGE="${IMAGE}:${BUILD_NUMBER}"
    
            echo "Current value lines in ${TARGET_FILE}:"
            grep -nE "^[[:space:]]*value:[[:space:]]" "$TARGET_FILE" || true
    
            # Replace ANY existing 'value:' line with the new image:tag
            # (Keeps indentation at 8 spaces used in your file)
            sed -E -i "s|^[[:space:]]*value:[[:space:]].*|        value: ${TARGET_IMAGE}|" "$TARGET_FILE"
    
            echo "----- Diff (if any) -----"
            git --no-pager diff -- "$TARGET_FILE" || true
    
            # Commit only if changed
            if ! git diff --quiet -- "$TARGET_FILE"; then
              git add "$TARGET_FILE"
              git commit -m "promote ${APP_NAME}:${BUILD_NUMBER} (ECR) to prod"
              git push origin "${GITOPS_BRANCH}"
              echo "Pushed ${TARGET_IMAGE} to GitOps."
            else
              echo "No changes detected; skipping commit/push."
            fi
          '''
        }
      }
    }
    // If you previously had a direct "Deploy to EKS (Prod)" stage, it's no longer needed.
    // Argo CD will detect the commit and sync the new image to the cluster.
  }

  post {
    success { echo "✅ Staging deployed. Promotion committed to GitOps for Argo CD to sync PROD." }
    failure { echo "❌ Build failed. Check the logs." }
  }
}
