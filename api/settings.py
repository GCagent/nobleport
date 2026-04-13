from functools import lru_cache
from typing import List
import os


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "NoblePort ENS Stack")
    APP_ENV: str = os.getenv("APP_ENV", "production")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.1.0")

    MAINNET_RPC_URL: str = os.getenv("MAINNET_RPC_URL", "")
    ENS_REGISTRY_ADDRESS: str = os.getenv(
        "ENS_REGISTRY_ADDRESS", "0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e"
    )
    ENS_NAME: str = os.getenv("ENS_NAME", "nobleport.eth")
    ENS_PRIVATE_KEY: str = os.getenv("ENS_PRIVATE_KEY", "")
    ENS_DEFAULT_COIN_TYPE: int = int(os.getenv("ENS_DEFAULT_COIN_TYPE", "60"))

    GITHUB_WEBHOOK_SECRET: str = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    DEPLOY_SCRIPT: str = os.getenv("DEPLOY_SCRIPT", "./scripts/redeploy.sh")
    DEPLOY_BRANCH: str = os.getenv("DEPLOY_BRANCH", "main")
    DEPLOY_REF_TYPE: str = os.getenv("DEPLOY_REF_TYPE", "branch")
    GITHUB_ALLOWED_REPOS: List[str] = [
        item.strip()
        for item in os.getenv("GITHUB_ALLOWED_REPOS", "GCagent/nobleport").split(",")
        if item.strip()
    ]

    PUBLIC_BASE_URL: str = os.getenv("PUBLIC_BASE_URL", "https://api.nobleport.eth")
    ENS_TEXT_GITHUB_KEY: str = os.getenv("ENS_TEXT_GITHUB_KEY", "com.github")
    ENS_TEXT_API_KEY: str = os.getenv("ENS_TEXT_API_KEY", "url")
    ENS_TEXT_DOCS_KEY: str = os.getenv("ENS_TEXT_DOCS_KEY", "com.nobleport.docs")
    ENS_TEXT_DEPLOYMENT_KEY: str = os.getenv(
        "ENS_TEXT_DEPLOYMENT_KEY", "com.nobleport.deployment"
    )

    ALLOWED_ORIGINS: List[str] = [
        item.strip()
        for item in os.getenv("ALLOWED_ORIGINS", "*").split(",")
        if item.strip()
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
