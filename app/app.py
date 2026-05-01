import os

from fastapi import FastAPI


REQUIRED_GREETING = os.getenv("REQUIRED_GREETING")

if not REQUIRED_GREETING:
    raise RuntimeError("REQUIRED_GREETING environment variable is missing")


app = FastAPI(title="Self-Healing API", version="1.0.0")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> dict[str, str]:
    return {"message": REQUIRED_GREETING}
