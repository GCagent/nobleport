import os
import requests

DEFAULT_TIMEOUT_SECONDS = float(os.getenv("VERIFY_PROVIDER_TIMEOUT_SECONDS", "4"))


def _get_json(url: str, headers: dict[str, str] | None = None):
    try:
        response = requests.get(url, headers=headers or {}, timeout=DEFAULT_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def get_helius_account(address: str):
    api_key = os.getenv("HELIUS_API_KEY", "")
    if not api_key:
        return None
    url = f"https://api.helius.xyz/v0/addresses/{address}/balances?api-key={api_key}"
    return _get_json(url)


def get_birdeye_liquidity(address: str):
    api_key = os.getenv("BIRDEYE_API_KEY", "")
    if not api_key:
        return None
    headers = {"x-api-key": api_key}
    url = f"https://public-api.birdeye.so/defi/token_overview?address={address}"
    return _get_json(url, headers=headers)


def get_solscan_transactions(address: str):
    api_key = os.getenv("SOLSCAN_API_KEY", "")
    if not api_key:
        return None
    headers = {"token": api_key}
    url = f"https://pro-api.solscan.io/v2.0/account/transactions?address={address}&limit=20"
    return _get_json(url, headers=headers)
