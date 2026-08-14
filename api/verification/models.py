from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class VerificationStatus(str, Enum):
    PASS = "PASS"
    HOLD = "HOLD"
    BLOCK = "BLOCK"


class VerifyResponse(BaseModel):
    status: VerificationStatus
    reason: str | None = None


class AuditRecord(BaseModel):
    id: str
    address: str
    helius_status: VerificationStatus
    birdeye_status: VerificationStatus
    solscan_status: VerificationStatus
    final_decision: VerificationStatus
    source_health: dict[str, bool]
    provider_payload_hash: str
    prev_hash: str | None = None
    record_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
