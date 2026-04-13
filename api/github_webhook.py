import hmac
import hashlib
import subprocess
from fastapi import APIRouter, Request, HTTPException
from .settings import get_settings

router = APIRouter()
settings = get_settings()


def verify_signature(payload: bytes, signature: str):
    expected = "sha256=" + hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/deploy")
async def github_deploy(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    if not signature or not verify_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()

    repo = payload.get("repository", {}).get("full_name")
    ref = payload.get("ref", "")

    if repo not in settings.GITHUB_ALLOWED_REPOS:
        raise HTTPException(status_code=403, detail="Repo not allowed")

    if settings.DEPLOY_BRANCH not in ref:
        return {"status": "ignored"}

    subprocess.Popen([settings.DEPLOY_SCRIPT])

    return {"status": "deployment triggered"}
