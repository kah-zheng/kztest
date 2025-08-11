# CI/CD Starter: Jenkins + AWS ECR + EKS (Staging)

This repository is a minimal, beginner-friendly starting point. It builds a container image,
pushes it to Amazon ECR, and deploys to an EKS namespace using `kubectl` from a Jenkins pipeline.

## Structure
```
app/                 # sample Flask app
k8s/                 # K8s manifests templated with __PLACEHOLDERS__
Jenkinsfile          # minimal pipeline
```

## What you need
- An EKS cluster and kubectl access tested locally
- An ECR repository (e.g. `myapp`) in your AWS account
- Jenkins (on a VM or container) with:
  - Docker engine available to the Jenkins agent
  - AWS CLI and kubectl installed
  - Credentials in Jenkins:
    - `aws-creds` (AWS Access Key ID + Secret with ECR push and EKS access)
    - `kubeconfig-staging` (Secret file or Kubernetes credentials that give access to your EKS cluster)

## Quick start
1) Replace placeholders inside `Jenkinsfile`:
   - `AWS_REGION`, `AWS_ACCOUNT_ID`, `ECR_REPO`, `K8S_NAMESPACE`, `APP_NAME`
2) In Jenkins, create a Multibranch Pipeline or Pipeline job pointing to this repo.
3) Run the job. On success you should see a Deployment and Service in your cluster.
4) Port-forward to test:
   ```bash
   kubectl -n <K8S_NAMESPACE> port-forward svc/<APP_NAME> 8080:80
   curl http://localhost:8080/
   ```

## Next steps
- Add a test stage (pytest) to fail the build on test failures
- Add Trivy scanning: `docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image <image>`
- Convert k8s manifests to a Helm chart and promote to prod with a manual approval
