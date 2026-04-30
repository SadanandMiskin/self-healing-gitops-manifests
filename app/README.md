# self-healing-api

Small FastAPI service used by the GitOps self-healing demo.

The app intentionally requires `REQUIRED_GREETING` at process startup. If that env var is absent, the process exits and Kubernetes restarts the container, creating the `CrashLoopBackOff` failure used in the demo.

Run locally:

```powershell
pip install -r requirements.txt
$env:REQUIRED_GREETING="hello from local"
uvicorn app:app --host 0.0.0.0 --port 8080
```

Build:

```powershell
docker build -t self-healing-api:local .
```
