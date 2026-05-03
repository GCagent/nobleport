import hashlib
import json
import os
import uuid
from datetime import datetime

from api.verification.models import AuditRecord

_AUDIT_CHAIN: list[AuditRecord] = []


def _sha256(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_audit_log(address: str, helius_status, birdeye_status, solscan_status, final_decision, source_health: dict, raw_payload: dict) -> AuditRecord:
    prev_hash = _AUDIT_CHAIN[-1].record_hash if _AUDIT_CHAIN else None
    payload_hash = _sha256(json.dumps(raw_payload, sort_keys=True, default=str))
    body = {
        "id": str(uuid.uuid4()),
        "address": address,
        "helius_status": helius_status,
        "birdeye_status": birdeye_status,
        "solscan_status": solscan_status,
        "final_decision": final_decision,
        "source_health": source_health,
        "provider_payload_hash": payload_hash,
        "prev_hash": prev_hash,
        "created_at": datetime.utcnow().isoformat(),
    }
    body_hash = _sha256(json.dumps(body, sort_keys=True, default=str))

    record = AuditRecord(**body, record_hash=body_hash)
    _AUDIT_CHAIN.append(record)

    log_file = os.getenv("VERIFY_AUDIT_LOG_FILE", "")
    if log_file:
        with open(log_file, "a", encoding="utf-8") as handle:
            handle.write(record.model_dump_json() + "\n")

    return record
