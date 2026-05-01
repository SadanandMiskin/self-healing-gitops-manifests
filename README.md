# Self-Healing Agentic DevOps Pipeline with GitOps

Production-style local demo of a small GitOps pipeline where Argo CD deploys a broken Kubernetes app, Prometheus detects the failure, and a Python AI agent proposes a manifest-only fix through a GitHub pull request.

The project is intentionally small:

- 1 microservice: `self-healing-api`
- 1 failure mode: missing `REQUIRED_GREETING` env var causing `CrashLoopBackOff`
- 1 safe fix: add the missing env var to `manifests/apps/self-healing-api/deployment.yaml`

## Complete Project Structure

```text
.
|-- .github/
|   `-- workflows/
|       `-- ci.yml
|-- run_agent.py
|-- agents/
|   |-- README.md
|   |-- agent/
|   |   |-- __init__.py
|   |   |-- config.py
|   |   |-- decision.py
|   |   |-- detector.py
|   |   |-- diagnoser.py
|   |   |-- executor.py
|   |   |-- fixer.py
|   |   |-- main.py
|   |   |-- state.py
|   |   `-- observer.py
|   |-- config.example.yaml
|   |-- requirements.txt
|   `-- tests/
|       `-- test_fixer.py
|-- app/
|   |-- Dockerfile
|   |-- README.md
|   |-- app.py
|   `-- requirements.txt
|-- manifests/
|   |-- README.md
|   |-- apps/
|   |   `-- self-healing-api/
|   |       |-- deployment.yaml
|   |       |-- kustomization.yaml
|   |       `-- service.yaml
|   |-- argocd/
|   |   `-- application.yaml
|   `-- monitoring/
|       |-- prometheus-alert-rule.yaml
|       `-- prometheus-values.yaml
`-- scripts/
    `-- validate.py
```

## GitOps Flow

Code -> Docker image -> Git manifest -> Argo CD -> Kubernetes cluster

Failure -> Prometheus alert -> Agent observes -> Agent reads logs -> LLM diagnoses -> Agent edits Git manifest -> Agent opens PR -> Human merges -> Argo CD auto-syncs -> Pod recovers

The agent never patches the cluster. It only edits files in the manifests Git repository.

## Local Setup Instructions

Install:

- Docker Desktop
- `kubectl`
- Minikube or Kind
- Helm
- Argo CD CLI
- GitHub CLI: `gh`
- Python 3.11+
- Mistral AI API key from Mistral AI Studio

Docker Hub requirements:

- Docker Hub username
- Docker Hub access token
- GitHub repository secrets: `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`

GitHub requirements:

- App repo: contains `app/` and `.github/workflows/ci.yml`
- Manifests repo: contains `manifests/`
- `gh auth login` completed locally for PR automation
- `MISTRAL_API_KEY` environment variable set for Mistral diagnosis

You can keep this scaffold as one local folder for learning, but the production-style GitOps model treats `app/` and `manifests/` as separate repositories.

## A. Setup Cluster

Using Minikube:

```powershell
minikube start --cpus=4 --memory=8192
kubectl config current-context
kubectl create namespace self-healing
```

Using Kind:

```powershell
kind create cluster --name self-healing-gitops
kubectl config use-context kind-self-healing-gitops
kubectl create namespace self-healing
```

## B. Install Argo CD

```powershell
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl wait --for=condition=available --timeout=300s deployment/argocd-server -n argocd
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

Get the initial password in another terminal:

```powershell
argocd admin initial-password -n argocd
argocd login localhost:8080 --username admin --password <PASSWORD> --insecure
```

Argo CD UI:

```text
https://localhost:8080
```

## C. Deploy App via Argo CD

Update `manifests/argocd/application.yaml`:

- Replace `https://github.com/YOUR_GITHUB_ORG/self-healing-gitops-manifests.git`
- Keep `path: manifests/apps/self-healing-api` if your manifests repo stores this whole scaffold
- Use `path: apps/self-healing-api` if your manifests repo root is the `manifests/` directory

Apply the Argo CD application:

```powershell
kubectl apply -f manifests/argocd/application.yaml -n argocd
argocd app sync self-healing-api
argocd app get self-healing-api
```

Auto-sync is enabled in the Application manifest.

## D. Verify Failure

The deployment intentionally omits `REQUIRED_GREETING`, so the container exits at startup.

```powershell
kubectl get pods -n self-healing
kubectl describe pod -n self-healing -l app=self-healing-api
kubectl logs -n self-healing -l app=self-healing-api --tail=100
```

Expected log:

```text
RuntimeError: REQUIRED_GREETING environment variable is missing
```

Expected pod state:

```text
CrashLoopBackOff
```

## E. Setup Monitoring

Install Prometheus with kube-state-metrics via Helm:

```powershell
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install monitoring prometheus-community/kube-prometheus-stack `
  --namespace monitoring `
  --create-namespace `
  -f manifests/monitoring/prometheus-values.yaml
kubectl apply -f manifests/monitoring/prometheus-alert-rule.yaml
kubectl get prometheusrule -n monitoring
```

Forward Prometheus:

```powershell
kubectl port-forward svc/monitoring-kube-prometheus-prometheus -n monitoring 9090:9090
```

Check alerts:

```powershell
curl http://localhost:9090/api/v1/alerts
```

## F. Run Agent

Set your Mistral API key:

```powershell
$env:MISTRAL_API_KEY="<YOUR_MISTRAL_API_KEY>"
```

Run continuously with one Python command from the project root:

```powershell
python run_agent.py --github-repo OWNER/MANIFESTS_REPO --manifests-repo-path C:\absolute\path\to\manifests-repo
```

The launcher installs `agents/requirements.txt` with the Python interpreter running it, creates `agents/config.local.yaml` if missing, and starts the continuous Prometheus polling loop. You can also put `MISTRAL_API_KEY`, `GITHUB_REPO`, and `MANIFESTS_REPO_PATH` in your environment and run only `python run_agent.py`.

Debug a single cycle with a mock alert and mock LLM:

```powershell
python run_agent.py --mock-alert --llm mock --once --dry-run
```

## G. Fix via GitOps

The agent:

1. Reads a Prometheus alert.
2. Confirms the app is crashing.
3. Reads logs with `kubectl logs`.
4. Uses the LLM only for diagnosis.
5. Applies a safe decision policy.
6. Adds `REQUIRED_GREETING` to `deployment.yaml`.
7. Creates a branch.
8. Commits the manifest change.
9. Opens a GitHub PR with `gh pr create`.

No `kubectl patch`, `kubectl apply`, or direct cluster mutation is used by the agent.

## H. Redeploy via Argo CD

Merge the PR in GitHub:

```powershell
gh pr merge <PR_NUMBER> --repo OWNER/MANIFESTS_REPO --squash --delete-branch
```

Argo CD auto-syncs the updated manifest.

To force a refresh during the demo:

```powershell
argocd app refresh self-healing-api
argocd app get self-healing-api
```

## I. Validation Commands

```powershell
kubectl get pods -n self-healing
kubectl logs -n self-healing -l app=self-healing-api --tail=50
kubectl get svc -n self-healing
argocd app get self-healing-api
```

For Minikube:

```powershell
minikube service self-healing-api -n self-healing --url
curl <MINIKUBE_SERVICE_URL>/healthz
curl <MINIKUBE_SERVICE_URL>/
```

For port-forward:

```powershell
kubectl port-forward svc/self-healing-api -n self-healing 8081:80
curl http://localhost:8081/healthz
curl http://localhost:8081/
```

Expected healthy response:

```json
{"status":"ok"}
```

## Demo Script

1. Push app code to GitHub.
2. GitHub Actions builds and pushes `docker.io/YOUR_DOCKERHUB_USERNAME/self-healing-api:<sha>`.
3. Update the image in the manifests repo if needed.
4. Argo CD syncs manifests to the local cluster.
5. Pod enters `CrashLoopBackOff`.
6. Confirm logs show missing `REQUIRED_GREETING`.
7. Prometheus alert fires.
8. Start the continuously running agent.
9. Agent opens PR that adds `REQUIRED_GREETING`.
10. Merge PR.
11. Argo CD auto-syncs.
12. Pod becomes healthy.
13. Curl the service.

## CI Pipeline

The GitHub Actions workflow at `.github/workflows/ci.yml`:

- Builds `app/Dockerfile`
- Pushes to Docker Hub
- Optionally updates the image tag in the manifests repo when `MANIFESTS_REPO` and `MANIFESTS_REPO_TOKEN` are configured

Required app repo secrets:

```text
DOCKERHUB_USERNAME
DOCKERHUB_TOKEN
```

Optional manifest update secrets:

```text
MANIFESTS_REPO
MANIFESTS_REPO_TOKEN
```

## Safety Boundaries

The agent enforces these constraints:

- Only responds to `CrashLoopBackOff` alerts for `self-healing-api`
- Only diagnoses logs
- Only fixes missing `REQUIRED_GREETING`
- Only edits `deployment.yaml`
- Only creates Git commits and PRs
- Never mutates the Kubernetes cluster directly
