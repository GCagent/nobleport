"""GCagent field operations API.

This module hardens the prototype voice-upload flow into a production-oriented
FastAPI stack with authentication, validation, structured audit events,
Slack signature verification, async n8n dispatch, retry visibility, and
change-order/PDF workflows.
"""

import asyncio
import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import Response
from pydantic import BaseModel, Field

from .settings import get_settings


POSTGRES_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS gcagent_jobs (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    location TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gcagent_tasks (
    id UUID PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES gcagent_jobs(id),
    source TEXT NOT NULL,
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    transcript TEXT NOT NULL CHECK (length(trim(transcript)) > 0),
    assignee TEXT,
    status TEXT NOT NULL DEFAULT 'queued',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gcagent_audit_logs (
    id UUID PRIMARY KEY,
    job_id UUID REFERENCES gcagent_jobs(id),
    task_id UUID REFERENCES gcagent_tasks(id),
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    previous_hash TEXT,
    hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gcagent_retry_queue (
    id UUID PRIMARY KEY,
    task_id UUID NOT NULL REFERENCES gcagent_tasks(id),
    target TEXT NOT NULL,
    payload JSONB NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_error TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gcagent_change_orders (
    id UUID PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES gcagent_jobs(id),
    task_id UUID REFERENCES gcagent_tasks(id),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    cost_delta NUMERIC(12, 2) NOT NULL DEFAULT 0,
    schedule_delta_days INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending_approval',
    requested_by TEXT NOT NULL,
    approved_by TEXT,
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
""".strip()


class JsonFormatter(logging.Formatter):
    """Small structured logger for production ingestion."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "context"):
            payload["context"] = record.context
        return json.dumps(payload, default=str)


logger = logging.getLogger("gcagent")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False


class TaskCategory(str, Enum):
    JOBSITE_LOG = "jobsite_log"
    CHANGE_ORDER = "change_order"
    SCOPE = "scope"
    INSPECTION = "inspection"
    PERMIT = "permit"
    DRAW = "draw"
    PHOTO_PROOF = "photo_proof"
    CLIENT_NOTICE = "client_notice"


class TaskStatus(str, Enum):
    QUEUED = "queued"
    DISPATCHED = "dispatched"
    BLOCKED = "blocked"
    COMPLETED = "completed"


class ChangeOrderStatus(str, Enum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"


class GCJob(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    location: Optional[str] = None
    status: str = "active"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GCTask(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str
    source: str
    category: TaskCategory
    title: str
    transcript: str
    assignee: Optional[str] = None
    status: TaskStatus = TaskStatus.QUEUED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: Optional[str] = None
    task_id: Optional[str] = None
    actor: str
    action: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    previous_hash: Optional[str] = None
    hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RetryQueueItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    target: str
    payload: Dict[str, Any]
    attempts: int = 0
    last_error: Optional[str] = None
    status: str = "pending"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChangeOrder(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str
    task_id: Optional[str] = None
    title: str
    description: str
    cost_delta: float = 0.0
    schedule_delta_days: int = 0
    status: ChangeOrderStatus = ChangeOrderStatus.PENDING_APPROVAL
    requested_by: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChangeOrderCreate(BaseModel):
    job_id: str
    task_id: Optional[str] = None
    title: str
    description: str
    cost_delta: float = 0.0
    schedule_delta_days: int = 0
    requested_by: str


class ChangeOrderDecision(BaseModel):
    approver: str
    approved: bool
    note: Optional[str] = None


class VoiceCommandResponse(BaseModel):
    job_id: str
    task_id: str
    audit_id: str
    routed_to: str
    n8n_status: str
    retry_id: Optional[str] = None


class InMemoryGCRepository:
    """Repository used in dev/test until DATABASE_URL-backed persistence is wired."""

    def __init__(self) -> None:
        self.jobs: Dict[str, GCJob] = {}
        self.tasks: Dict[str, GCTask] = {}
        self.audit_logs: List[AuditLog] = []
        self.retry_queue: Dict[str, RetryQueueItem] = {}
        self.change_orders: Dict[str, ChangeOrder] = {}

    def ensure_job(self, job_id: str, name: Optional[str] = None) -> GCJob:
        if job_id not in self.jobs:
            self.jobs[job_id] = GCJob(id=job_id, name=name or f"Job {job_id[:8]}")
        return self.jobs[job_id]

    def create_task(self, task: GCTask) -> GCTask:
        self.tasks[task.id] = task
        return task

    def update_task_status(self, task_id: str, task_status: TaskStatus) -> None:
        self.tasks[task_id].status = task_status

    def append_audit(
        self,
        job_id: Optional[str],
        task_id: Optional[str],
        actor: str,
        action: str,
        payload: Dict[str, Any],
    ) -> AuditLog:
        previous_hash = self.audit_logs[-1].hash if self.audit_logs else None
        hash_payload = json.dumps(
            {
                "job_id": job_id,
                "task_id": task_id,
                "actor": actor,
                "action": action,
                "payload": payload,
                "previous_hash": previous_hash,
            },
            sort_keys=True,
            default=str,
        )
        digest = hashlib.sha256(hash_payload.encode()).hexdigest()
        audit = AuditLog(
            job_id=job_id,
            task_id=task_id,
            actor=actor,
            action=action,
            payload=payload,
            previous_hash=previous_hash,
            hash=digest,
        )
        self.audit_logs.append(audit)
        return audit

    def enqueue_retry(self, item: RetryQueueItem) -> RetryQueueItem:
        self.retry_queue[item.id] = item
        return item

    def create_change_order(self, change_order: ChangeOrder) -> ChangeOrder:
        self.change_orders[change_order.id] = change_order
        return change_order


repository = InMemoryGCRepository()
router = APIRouter(prefix="/api/gcagent", tags=["gcagent"])


def jsonable_model(model: BaseModel) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return json.loads(json.dumps(model.dict(), default=str))


async def require_gcagent_auth(authorization: str = Header(default="")) -> str:
    settings = get_settings()
    configured_tokens = [token for token in settings.GCAGENT_API_TOKENS if token]
    if not configured_tokens:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GCagent API token is not configured",
        )
    scheme, _, token = authorization.partition(" ")
    valid = scheme.lower() == "bearer" and any(
        hmac.compare_digest(token, expected) for expected in configured_tokens
    )
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid GCagent bearer token",
        )
    return token


def classify_transcript(transcript: str) -> TaskCategory:
    text = transcript.lower()
    if "change order" in text or "awo" in text or "extra work" in text:
        return TaskCategory.CHANGE_ORDER
    if "inspection" in text or "failed" in text:
        return TaskCategory.INSPECTION
    if "permit" in text or "ahj" in text:
        return TaskCategory.PERMIT
    if "draw" in text or "payment" in text:
        return TaskCategory.DRAW
    if "photo" in text or "picture" in text:
        return TaskCategory.PHOTO_PROOF
    if "scope" in text:
        return TaskCategory.SCOPE
    return TaskCategory.JOBSITE_LOG


def route_task(category: TaskCategory) -> str:
    routes = {
        TaskCategory.CHANGE_ORDER: "ChangeOrderHandler",
        TaskCategory.SCOPE: "ProjectScopeBuilder",
        TaskCategory.INSPECTION: "Inspection Failure Trigger",
        TaskCategory.PERMIT: "PermitTracker",
        TaskCategory.DRAW: "DrawScheduleManager",
        TaskCategory.PHOTO_PROOF: "PhotoProofUploader",
        TaskCategory.CLIENT_NOTICE: "ClientNotifier",
        TaskCategory.JOBSITE_LOG: "JobsiteAssistant",
    }
    return routes[category]


async def validate_audio_upload(file: UploadFile) -> bytes:
    settings = get_settings()
    if file.content_type not in settings.GCAGENT_ALLOWED_AUDIO_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported audio type: {file.content_type}",
        )
    payload = await file.read(settings.GCAGENT_MAX_UPLOAD_BYTES + 1)
    if len(payload) > settings.GCAGENT_MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Voice upload exceeds max size",
        )
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Voice upload is empty",
        )
    return payload


async def dispatch_to_n8n(task: GCTask, audit: AuditLog) -> Optional[RetryQueueItem]:
    settings = get_settings()
    if not settings.N8N_WEBHOOK_URL:
        repository.update_task_status(task.id, TaskStatus.BLOCKED)
        return repository.enqueue_retry(
            RetryQueueItem(
                task_id=task.id,
                target="n8n",
                payload={"task": jsonable_model(task), "audit": jsonable_model(audit)},
                last_error="N8N_WEBHOOK_URL is not configured",
            )
        )

    payload = {"task": jsonable_model(task), "audit": jsonable_model(audit)}
    try:
        async with httpx.AsyncClient(timeout=settings.N8N_TIMEOUT_SECONDS) as client:
            response = await client.post(settings.N8N_WEBHOOK_URL, json=payload)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        repository.update_task_status(task.id, TaskStatus.BLOCKED)
        logger.error(
            "n8n dispatch failed",
            extra={"context": {"task_id": task.id, "error": str(exc)}},
        )
        return repository.enqueue_retry(
            RetryQueueItem(
                task_id=task.id,
                target="n8n",
                payload=payload,
                last_error=str(exc),
            )
        )

    repository.update_task_status(task.id, TaskStatus.DISPATCHED)
    logger.info("n8n dispatch succeeded", extra={"context": {"task_id": task.id}})
    return None


def verify_slack_signature(body: bytes, timestamp: str, signature: str) -> None:
    settings = get_settings()
    if not settings.SLACK_SIGNING_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Slack signing secret is not configured",
        )
    if not timestamp.isdigit():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Slack signature timestamp",
        )
    try_timestamp = int(timestamp)
    now_timestamp = int(datetime.now(timezone.utc).timestamp())
    if abs(now_timestamp - try_timestamp) > 300:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Stale Slack signature timestamp",
        )
    base = f"v0:{timestamp}:".encode() + body
    expected = "v0=" + hmac.new(
        settings.SLACK_SIGNING_SECRET.encode(),
        base,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Slack signature",
        )


def build_minimal_pdf(title: str, lines: List[str]) -> bytes:
    escaped_lines = [
        line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        for line in [title, *lines]
    ]
    text_commands = ["BT", "/F1 14 Tf", "72 760 Td", f"({escaped_lines[0]}) Tj"]
    text_commands.extend([f"0 -20 Td ({line}) Tj" for line in escaped_lines[1:]])
    text_commands.append("ET")
    stream = "\n".join(text_commands).encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_start}\n%%EOF\n".encode()
    )
    return bytes(pdf)


@router.get("/schema")
async def postgres_schema(_: str = Depends(require_gcagent_auth)) -> Dict[str, str]:
    return {"postgres_schema_sql": POSTGRES_SCHEMA_SQL}


@router.post(
    "/voice-command",
    response_model=VoiceCommandResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def voice_command(
    file: UploadFile = File(...),
    job_id: str = Form(...),
    actor: str = Form(...),
    transcript: str = Form(...),
    _: str = Depends(require_gcagent_auth),
) -> VoiceCommandResponse:
    clean_transcript = transcript.strip()
    if not clean_transcript:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No transcript, no task",
        )
    audio = await validate_audio_upload(file)
    repository.ensure_job(job_id)
    category = classify_transcript(clean_transcript)
    routed_to = route_task(category)
    task = repository.create_task(
        GCTask(
            job_id=job_id,
            source="voice-command",
            category=category,
            title=clean_transcript[:80],
            transcript=clean_transcript,
            assignee=routed_to,
        )
    )
    audit = repository.append_audit(
        job_id=job_id,
        task_id=task.id,
        actor=actor,
        action="task.created_from_voice",
        payload={
            "filename": file.filename,
            "content_type": file.content_type,
            "audio_sha256": hashlib.sha256(audio).hexdigest(),
            "routed_to": routed_to,
        },
    )
    retry = await dispatch_to_n8n(task, audit)
    n8n_status = "queued_for_retry" if retry else "dispatched"
    return VoiceCommandResponse(
        job_id=job_id,
        task_id=task.id,
        audit_id=audit.id,
        routed_to=routed_to,
        n8n_status=n8n_status,
        retry_id=retry.id if retry else None,
    )


@router.post("/slack/events")
async def slack_events(request: Request) -> Dict[str, str]:
    body = await request.body()
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")
    verify_slack_signature(body, timestamp, signature)
    payload = await request.json()
    if payload.get("type") == "url_verification":
        return {"challenge": payload.get("challenge", "")}
    repository.append_audit(
        None,
        None,
        payload.get("user_id", "slack"),
        "slack.event.received",
        payload,
    )
    return {"status": "ok"}


@router.post(
    "/change-orders",
    response_model=ChangeOrder,
    status_code=status.HTTP_201_CREATED,
)
async def create_change_order(
    change_order_data: ChangeOrderCreate,
    _: str = Depends(require_gcagent_auth),
) -> ChangeOrder:
    repository.ensure_job(change_order_data.job_id)
    change_order = repository.create_change_order(
        ChangeOrder(**jsonable_model(change_order_data))
    )
    repository.append_audit(
        change_order.job_id,
        change_order.task_id,
        change_order.requested_by,
        "change_order.pending_approval",
        jsonable_model(change_order),
    )
    return change_order


@router.post("/change-orders/{change_order_id}/decision", response_model=ChangeOrder)
async def decide_change_order(
    change_order_id: str,
    decision: ChangeOrderDecision,
    _: str = Depends(require_gcagent_auth),
) -> ChangeOrder:
    if change_order_id not in repository.change_orders:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Change order not found",
        )
    change_order = repository.change_orders[change_order_id]
    change_order.status = (
        ChangeOrderStatus.APPROVED
        if decision.approved
        else ChangeOrderStatus.REJECTED
    )
    change_order.approved_by = decision.approver
    change_order.approved_at = datetime.now(timezone.utc)
    repository.append_audit(
        change_order.job_id,
        change_order.task_id,
        decision.approver,
        f"change_order.{change_order.status.value}",
        {"change_order_id": change_order_id, "note": decision.note},
    )
    return change_order


@router.get("/jobs/{job_id}/log.pdf")
async def job_log_pdf(job_id: str, _: str = Depends(require_gcagent_auth)) -> Response:
    if job_id not in repository.jobs:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    lines = [
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "Audit chain:",
        *[
            f"{audit.created_at.isoformat()} {audit.action} "
            f"task={audit.task_id or '-'} hash={audit.hash[:12]}"
            for audit in repository.audit_logs
            if audit.job_id == job_id
        ],
    ]
    return Response(
        build_minimal_pdf(f"GCagent Job Log {job_id}", lines),
        media_type="application/pdf",
    )


@router.get("/change-orders/{change_order_id}.pdf")
async def change_order_pdf(
    change_order_id: str,
    _: str = Depends(require_gcagent_auth),
) -> Response:
    if change_order_id not in repository.change_orders:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Change order not found",
        )
    change_order = repository.change_orders[change_order_id]
    lines = [
        f"Status: {change_order.status.value}",
        f"Requested by: {change_order.requested_by}",
        f"Approved by: {change_order.approved_by or '-'}",
        f"Cost delta: {change_order.cost_delta}",
        f"Schedule delta days: {change_order.schedule_delta_days}",
        f"Description: {change_order.description}",
    ]
    return Response(
        build_minimal_pdf(f"Change Order {change_order.title}", lines),
        media_type="application/pdf",
    )


@router.post("/retry-queue/{retry_id}/run")
async def run_retry(
    retry_id: str,
    _: str = Depends(require_gcagent_auth),
) -> Dict[str, str]:
    if retry_id not in repository.retry_queue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Retry item not found",
        )
    item = repository.retry_queue[retry_id]
    item.attempts += 1
    task = repository.tasks[item.task_id]
    audit = repository.append_audit(
        task.job_id,
        task.id,
        "retry-worker",
        "retry.n8n.started",
        {"retry_id": retry_id},
    )
    retry = await dispatch_to_n8n(task, audit)
    if retry is None:
        item.status = "completed"
    await asyncio.sleep(0)
    return {"status": item.status}
