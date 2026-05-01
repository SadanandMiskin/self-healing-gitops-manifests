# End-to-End Demo Script

Use two GitHub repositories for the cleanest demo:

- App repo: this project with `app/` and `.github/workflows/ci.yml`
- Manifests repo: this project with `manifests/`

For a local walkthrough, you can keep one folder and point Argo CD at the same GitHub repo path.

## 1. Prepare Image

Update `manifests/apps/self-healing-api/deployment.yaml`:

```yaml
image: docker.io/YOUR_DOCKERHUB_USERNAME/self-healing-api:latest
```

Push the app repo to GitHub. GitHub Actions builds and pushes the image.

Manual local image build option:

```powershell
cd app
docker build -t docker.io/YOUR_DOCKERHUB_USERNAME/self-healing-api:latest .
docker push docker.io/YOUR_DOCKERHUB_USERNAME/self-healing-api:latest
```

## 2. Start Cluster

```powershell
minikube start --cpus=4 --memory=8192
kubectl create namespace self-healing
```

## 3. Install Argo CD

```powershell
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl wait --for=condition=available --timeout=300s deployment/argocd-server -n argocd
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

In another terminal:

```powershell
argocd admin initial-password -n argocd
argocd login localhost:8080 --username admin --password <PASSWORD> --insecure
```

Open `https://localhost:8080`.

## 4. Deploy App Through Argo CD

Update `manifests/argocd/application.yaml` with your manifests repo URL.

```powershell
kubectl apply -f manifests/argocd/application.yaml -n argocd
argocd app sync self-healing-api
argocd app get self-healing-api
```

## 5. Confirm Failure

```powershell
kubectl get pods -n self-healing
kubectl logs -n self-healing -l app=self-healing-api --tail=100
```

Expected:

```text
RuntimeError: REQUIRED_GREETING environment variable is missing
```

## 6. Install Monitoring

```powershell
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install monitoring prometheus-community/kube-prometheus-stack `
  --namespace monitoring `
  --create-namespace `
  -f manifests/monitoring/prometheus-values.yaml
kubectl apply -f manifests/monitoring/prometheus-alert-rule.yaml
kubectl port-forward svc/monitoring-kube-prometheus-prometheus -n monitoring 9090:9090
```

Check alert state:

```powershell
curl http://localhost:9090/api/v1/alerts
```

## 7. Run Agent

Set your Mistral API key:

```powershell
$env:MISTRAL_API_KEY="<YOUR_MISTRAL_API_KEY>"
```

Start the continuously running agent:

```powershell
python run_agent.py --github-repo OWNER/self-healing-gitops-manifests --manifests-repo-path C:\absolute\path\to\manifests-repo
```

Fast one-cycle demo with mock alert:

```powershell
python run_agent.py --mock-alert --llm mock --once --dry-run
```

## 8. Review and Merge PR

```powershell
gh pr list --repo OWNER/self-healing-gitops-manifests
gh pr view <PR_NUMBER> --repo OWNER/self-healing-gitops-manifests --web
gh pr merge <PR_NUMBER> --repo OWNER/self-healing-gitops-manifests --squash --delete-branch
```

The PR adds:

```yaml
- name: REQUIRED_GREETING
  value: hello-from-gitops
```

## 9. Watch Argo CD Recover the App

```powershell
argocd app refresh self-healing-api
argocd app get self-healing-api
kubectl rollout status deployment/self-healing-api -n self-healing
kubectl get pods -n self-healing
```

Validate service:

```powershell
kubectl port-forward svc/self-healing-api -n self-healing 8081:80
curl http://localhost:8081/healthz
curl http://localhost:8081/
```

Expected:

```json
{"message":"hello-from-gitops"}
```
