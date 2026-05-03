from api.verification.models import VerificationStatus


def helius_check(data: dict) -> VerificationStatus:
    account_type = data.get("type", "wallet")
    if account_type not in {"wallet", "token_account"}:
        return VerificationStatus.BLOCK
    if data.get("mint_authority"):
        return VerificationStatus.BLOCK
    if data.get("freeze_authority"):
        return VerificationStatus.HOLD
    return VerificationStatus.PASS


def birdeye_check(data: dict) -> VerificationStatus:
    payload = data.get("data", data)
    liquidity = float(payload.get("liquidity", 0) or payload.get("liquidity_usd", 0) or 0)
    volume = float(payload.get("v24hUSD", 0) or payload.get("volume_24h", 0) or 0)
    if liquidity < 50000:
        return VerificationStatus.BLOCK
    if liquidity < 150000:
        return VerificationStatus.HOLD
    if volume < liquidity * 0.2:
        return VerificationStatus.HOLD
    return VerificationStatus.PASS


def detect_single_source_funding(transactions: list[dict]) -> bool:
    sources = {tx.get("src") for tx in transactions if tx.get("src")}
    return len(sources) <= 1 and len(transactions) > 0


def detect_wallet_loops(transactions: list[dict], address: str) -> bool:
    outbound = {tx.get("dst") for tx in transactions if tx.get("src") == address and tx.get("dst")}
    inbound = {tx.get("src") for tx in transactions if tx.get("dst") == address and tx.get("src")}
    return len(outbound.intersection(inbound)) > 0


def solscan_check(data: dict, address: str) -> VerificationStatus:
    txs = data.get("data", data)
    if not isinstance(txs, list):
        txs = []
    if len(txs) < 5:
        return VerificationStatus.BLOCK
    if detect_wallet_loops(txs, address):
        return VerificationStatus.BLOCK
    if detect_single_source_funding(txs):
        return VerificationStatus.BLOCK
    return VerificationStatus.PASS


def score(h: VerificationStatus, b: VerificationStatus, s: VerificationStatus) -> VerificationStatus:
    if VerificationStatus.BLOCK in {h, b, s}:
        return VerificationStatus.BLOCK
    if VerificationStatus.HOLD in {h, b, s}:
        return VerificationStatus.HOLD
    return VerificationStatus.PASS
