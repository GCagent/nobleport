"""GCagent field-operations API with persistent Postgres support.

The module supports an explicit in-memory backend for development/test only and
an async Postgres repository for staging/production. Every write is paired with
an audit record, and the audit hash chain is serialized in Postgres.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

import asyncpg
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
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    location TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gcagent_tasks (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES gcagent_jobs(id),
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
    id TEXT PRIMARY KEY,
    job_id TEXT REFERENCES gcagent_jobs(id),
    task_id TEXT REFERENCES gcagent_tasks(id),
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    previous_hash TEXT,
    hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gcagent_retry_queue (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES gcagent_tasks(id),
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
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES gcagent_jobs(id),
    task_id TEXT REFERENCES gcagent_tasks(id),
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

CREATE INDEX IF NOT EXISTS idx_gcagent_tasks_job_id ON gcagent_tasks(job_id);
CREATE INDEX IF NOT EXISTS idx_gcagent_audit_logs_job_created ON gcagent_audit_logs(job_id, created_at);
CREATE INDEX IF NOT EXISTS idx_gcagent_retry_queue_status_next ON gcagent_retry_queue(status, next_attempt_at);
CREATE INDEX IF NOT EXISTS idx_gcagent_change_orders_job_id ON gcagent_change_orders(job_id);
""".strip()


class JsonFormatter(logging.Formatter):
    """Small structured logger for field-operation ingestion."""

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
    id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=256)
    location: Optional[str] = Field(default=None, max_length=512)
    status: str = "active"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GCTask(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str = Field(min_length=1, max_length=128)
    source: str = Field(min_length=1, max_length=100)
    category: TaskCategory
    title: str = Field(min_length=1, max_length=512)
    transcript: str = Field(min_length=1)
    assignee: Optional[str] = Field(default=None, max_length=256)
    status: TaskStatus = TaskStatus.QUEUED
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: Optional[str] = None
    task_id: Optional[str] = None
    actor: str = Field(min_length=1, max_length=256)
    action: str = Field(min_length=1, max_length=256)
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
    title: str = Field(min_length=1, max_length=512)
    description: str = Field(min_length=1)
    cost_delta: float = 0.0
    schedule_delta_days: int = 0
    status: ChangeOrderStatus = ChangeOrderStatus.PENDING_APPROVAL
    requested_by: str = Field(min_length=1, max_length=256)
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChangeOrderCreate(BaseModel):
    job_id: str = Field(min_length=1, max_length=128)
    task_id: Optional[str] = None
    title: str = Field(min_length=1, max_length=512)
    description: str = Field(min_length=1)
    cost_delta: float = 0.0
    schedule_delta_days: int = 0
    requested_by: str = Field(min_length=1, max_length=256)


class ChangeOrderDecision(BaseModel):
    approver: str = Field(min_length=1, max_length=256)
    approved: bool
    note: Optional[str] = Field(default=None, max_length=2000)


class VoiceCommandResponse(BaseModel):
    job_id: str
    task_id: str
    audit_id: str
    routed_to: str
    n8n_status: str
    retry_id: Optional[str] = None


def jsonable_model(model: BaseModel) -> Dict[str, Any]:
    return model.model_dump(mode="json")


def _audit_hash(
    job_id: Optional[str],
    task_id: Optional[str],
    actor: str,
    action: str,
    payload: Dict[str, Any],
    previous_hash: Optional[str],
) -> str:
    serialized = json.dumps(
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
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode()).hexdigest()


def _json_value(value: Any) -> Dict[str, Any]:
    if isinstance(value, str):
        return json.loads(value)
    if isinstance(value, dict):
        return value
    return dict(value or {})


class InMemoryGCRepository:
    """Development/test implementation. Never acceptable for production data."""

    persistent = False
    backend = "memory"

    def __init__(self) -> None:
        self.jobs: Dict[str, GCJob] = {}
        self.tasks: Dict[str, GCTask] = {}
        self.audit_logs: List[AuditLog] = []
        self.retry_queue: Dict[str, RetryQueueItem] = {}
        self.change_orders: Dict[str, ChangeOrder] = {}

    async def startup(self) -> None:
        return None

    async def shutdown(self) -> None:
        return None

    async def ensure_job(self, job_id: str, name: Optional[str] = None) -> GCJob:
        if job_id not in self.jobs:
            self.jobs[job_id] = GCJob(id=job_id, name=name or f"Job {job_id[:24]}")
        return self.jobs[job_id]

    async def get_job(self, job_id: str) -> Optional[GCJob]:
        return self.jobs.get(job_id)

    async def create_task(self, task: GCTask) -> GCTask:
        self.tasks[task.id] = task
        return task

    async def get_task(self, task_id: str) -> Optional[GCTask]:
        return self.tasks.get(task_id)

    async def update_task_status(self, task_id: str, task_status: TaskStatus) -> None:
        self.tasks[task_id].status = task_status

    async def append_audit(
        self,
        job_id: Optional[str],
        task_id: Optional[str],
        actor: str,
        action: str,
        payload: Dict[str, Any],
    ) -> AuditLog:
        previous_hash = self.audit_logs[-1].hash if self.audit_logs else None
        audit = AuditLog(
            job_id=job_id,
            task_id=task_id,
            actor=actor,
            action=action,
            payload=payload,
            previous_hash=previous_hash,
            hash=_audit_hash(job_id, task_id, actor, action, payload, previous_hash),
        )
        self.audit_logs.append(audit)
        return audit

    async def list_audits(self, job_id: str) -> List[AuditLog]:
        return [audit for audit in self.audit_logs if audit.job_id == job_id]

    async def enqueue_retry(self, item: RetryQueueItem) -> RetryQueueItem:
        self.retry_queue[item.id] = item
        return item

    async def get_retry(self, retry_id: str) -> Optional[RetryQueueItem]:
        return self.retry_queue.get(retry_id)

    async def mark_retry_failed(self, retry_id: str, error: str) -> None:
        item = self.retry_queue[retry_id]
        item.attempts += 1
        item.last_error = error
        item.status = "pending"

    async def mark_retry_completed(self, retry_id: str) -> None:
        item = self.retry_queue[retry_id]
        item.attempts += 1
        item.last_error = None
        item.status = "completed"

    async def create_change_order(self, change_order: ChangeOrder) -> ChangeOrder:
        self.change_orders[change_order.id] = change_order
        return change_order

    async def get_change_order(self, change_order_id: str) -> Optional[ChangeOrder]:
        return self.change_orders.get(change_order_id)

    async def decide_change_order(
        self,
        change_order_id: str,
        status_value: ChangeOrderStatus,
        approver: str,
        approved_at: datetime,
    ) -> Optional[ChangeOrder]:
        change_order = self.change_orders.get(change_order_id)
        if change_order is None:
            return None
        change_order.status = status_value
        change_order.approved_by = approver
        change_order.approved_at = approved_at
        return change_order


class PostgresGCRepository:
    """Async PostgreSQL repository for durable GCagent operational records."""

    persistent = True
    backend = "postgres"

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None

    def _pool(self) -> asyncpg.Pool:
        if self.pool is None:
            raise RuntimeError("GCagent Postgres repository is not initialized")
        return self.pool

    async def startup(self) -> None:
        self.pool = await asyncpg.create_pool(
            dsn=self.database_url,
            min_size=1,
            max_size=5,
            command_timeout=10,
        )
        async with self._pool().acquire() as connection:
            table = await connection.fetchval("SELECT to_regclass('public.gcagent_jobs')")
        if table is None:
            await self.shutdown()
            raise RuntimeError("GCagent migration is missing: gcagent_jobs table not found")

    async def shutdown(self) -> None:
        if self.pool is not None:
            await self.pool.close()
            self.pool = None

    async def ensure_job(self, job_id: str, name: Optional[str] = None) -> GCJob:
        row = await self._pool().fetchrow(
            """
            INSERT INTO gcagent_jobs (id, name)
            VALUES ($1, $2)
            ON CONFLICT (id) DO UPDATE SET updated_at = NOW()
            RETURNING id, name, location, status, created_at
            """,
            job_id,
            name or f"Job {job_id[:24]}",
        )
        return GCJob(**dict(row))

    async def get_job(self, job_id: str) -> Optional[GCJob]:
        row = await self._pool().fetchrow(
            "SELECT id, name, location, status, created_at FROM gcagent_jobs WHERE id = $1",
            job_id,
        )
        return GCJob(**dict(row)) if row else None

    async def create_task(self, task: GCTask) -> GCTask:
        row = await self._pool().fetchrow(
            """
            INSERT INTO gcagent_tasks (id, job_id, source, category, title, transcript, assignee, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id, job_id, source, category, title, transcript, assignee, status, created_at
            """,
            task.id,
            task.job_id,
            task.source,
            task.category.value,
            task.title,
            task.transcript,
            task.assignee,
            task.status.value,
        )
        return GCTask(**dict(row))

    async def get_task(self, task_id: str) -> Optional[GCTask]:
        row = await self._pool().fetchrow(
            """
            SELECT id, job_id, source, category, title, transcript, assignee, status, created_at
            FROM gcagent_tasks WHERE id = $1
            """,
            task_id,
        )
        return GCTask(**dict(row)) if row else None

    async def update_task_status(self, task_id: str, task_status: TaskStatus) -> None:
        result = await self._pool().execute(
            "UPDATE gcagent_tasks SET status = $2, updated_at = NOW() WHERE id = $1",
            task_id,
            task_status.value,
        )
        if result.endswith("0"):
            raise KeyError(f"Task not found: {task_id}")

    async def append_audit(
        self,
        job_id: Optional[str],
        task_id: Optional[str],
        actor: str,
        action: str,
        payload: Dict[str, Any],
    ) -> AuditLog:
        payload_json = json.dumps(payload, sort_keys=True, default=str)
        async with self._pool().acquire() as connection:
            async with connection.transaction():
                await connection.execute(
                    "SELECT pg_advisory_xact_lock(hashtext('gcagent_audit_chain'))"
                )
                previous_hash = await connection.fetchval(
                    "SELECT hash FROM gcagent_audit_logs ORDER BY created_at DESC, id DESC LIMIT 1"
                )
                digest = _audit_hash(job_id, task_id, actor, action, payload, previous_hash)
                row = await connection.fetchrow(
                    """
                    INSERT INTO gcagent_audit_logs
                        (id, job_id, task_id, actor, action, payload, previous_hash, hash)
                    VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8)
                    RETURNING id, job_id, task_id, actor, action, payload, previous_hash, hash, created_at
                    """,
                    str(uuid.uuid4()),
                    job_id,
                    task_id,
                    actor,
                    action,
                    payload_json,
                    previous_hash,
                    digest,
                )
        values = dict(row)
        values["payload"] = _json_value(values["payload"])
        return AuditLog(**values)

    async def list_audits(self, job_id: str) -> List[AuditLog]:
        rows = await self._pool().fetch(
            """
            SELECT id, job_id, task_id, actor, action, payload, previous_hash, hash, created_at
            FROM gcagent_audit_logs
            WHERE job_id = $1
            ORDER BY created_at ASC, id ASC
            """,
            job_id,
        )
        audits: List[AuditLog] = []
        for row in rows:
            values = dict(row)
            values["payload"] = _json_value(values["payload"])
            audits.append(AuditLog(**values))
        return audits

    async def enqueue_retry(self, item: RetryQueueItem) -> RetryQueueItem:
        row = await self._pool().fetchrow(
            """
            INSERT INTO gcagent_retry_queue (id, task_id, target, payload, attempts, last_error, status)
            VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7)
            RETURNING id, task_id, target, payload, attempts, last_error, status, created_at
            """,
            item.id,
            item.task_id,
            item.target,
            json.dumps(item.payload, sort_keys=True, default=str),
            item.attempts,
            item.last_error,
            item.status,
        )
        values = dict(row)
        values["payload"] = _json_value(values["payload"])
        return RetryQueueItem(**values)

    async def get_retry(self, retry_id: str) -> Optional[RetryQueueItem]:
        row = await self._pool().fetchrow(
            """
            SELECT id, task_id, target, payload, attempts, last_error, status, created_at
            FROM gcagent_retry_queue WHERE id = $1
            """,
            retry_id,
        )
        if row is None:
            return None
        values = dict(row)
        values["payload"] = _json_value(values["payload"])
        return RetryQueueItem(**values)

    async def mark_retry_failed(self, retry_id: str, error: str) -> None:
        await self._pool().execute(
            """
            UPDATE gcagent_retry_queue
            SET attempts = attempts + 1, last_error = $2, status = 'pending', updated_at = NOW()
            WHERE id = $1
            """,
            retry_id,
            error[:4000],
        )

    async def mark_retry_completed(self, retry_id: str) -> None:
        await self._pool().execute(
            """
            UPDATE gcagent_retry_queue
            SET attempts = attempts + 1, last_error = NULL, status = 'completed', updated_at = NOW()
            WHERE id = $1
            """,
            retry_id,
        )

    async def create_change_order(self, change_order: ChangeOrder) -> ChangeOrder:
        row = await self._pool().fetchrow(
            """
            INSERT INTO gcagent_change_orders
                (id, job_id, task_id, title, description, cost_delta, schedule_delta_days, status, requested_by)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id, job_id, task_id, title, description, cost_delta, schedule_delta_days,
                      status, requested_by, approved_by, approved_at, created_at
            """,
            change_order.id,
            change_order.job_id,
            change_order.task_id,
            change_order.title,
            change_order.description,
            Decimal(str(change_order.cost_delta)),
            change_order.schedule_delta_days,
            change_order.status.value,
            change_order.requested_by,
        )
        return self._change_order_from_row(row)

    async def get_change_order(self, change_order_id: str) -> Optional[ChangeOrder]:
        row = await self._pool().fetchrow(
            """
            SELECT id, job_id, task_id, title, description, cost_delta, schedule_delta_days,
                   status, requested_by, approved_by, approved_at, created_at
            FROM gcagent_change_orders WHERE id = $1
            """,
            change_order_id,
        )
        return self._change_order_from_row(row) if row else None

    async def decide_change_order(
        self,
        change_order_id: str,
        status_value: ChangeOrderStatus,
        approver: str,
        approved_at: datetime,
    ) -> Optional[ChangeOrder]:
        row = await self._pool().fetchrow(
            """
            UPDATE gcagent_change_orders
            SET status = $2, approved_by = $3, approved_at = $4, updated_at = NOW()
            WHERE id = $1
            RETURNING id, job_id, task_id, title, description, cost_delta, schedule_delta_days,
                      status, requested_by, approved_by, approved_at, created_at
            """,
            change_order_id,
            status_value.value,
            approver,
            approved_at,
        )
        return self._change_order_from_row(row) if row else None

    @staticmethod
    def _change_order_from_row(row: asyncpg.Record) -> ChangeOrder:
        values = dict(row)
        values["cost_delta"] = float(values["cost_delta"])
        return ChangeOrder(**values)


repository: Any = InMemoryGCRepository()
router = APIRouter(prefix="/api/gcagent", tags=["gcagent"])


async def configure_repository() -> Dict[str, Any]:
    """Select and initialize the repository once per application process."""
    global repository
    settings = get_settings()

    if settings.PERSISTENCE_BACKEND == "postgres":
        candidate = PostgresGCRepository(settings.DATABASE_URL)
        await candidate.startup()
        repository = candidate
    else:
        repository = InMemoryGCRepository()
        await repository.startup()

    return repository_status()


async def shutdown_repository() -> None:
    await repository.shutdown()


def repository_status() -> Dict[str, Any]:
    return {
        "ok": bool(getattr(repository, "persistent", False)),
        "backend": str(getattr(repository, "backend", "unknown")),
        "state": "persistent_repository_active"
        if getattr(repository, "persistent", False)
        else "in_memory_repository_active",
    }


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


async def dispatch_to_n8n(
    task: GCTask,
    audit: AuditLog,
    retry_id: Optional[str] = None,
) -> Optional[RetryQueueItem]:
    settings = get_settings()
    payload = {"task": jsonable_model(task), "audit": jsonable_model(audit)}

    if not settings.N8N_WEBHOOK_URL:
        await repository.update_task_status(task.id, TaskStatus.BLOCKED)
        error = "N8N_WEBHOOK_URL is not configured"
        if retry_id:
            await repository.mark_retry_failed(retry_id, error)
            return await repository.get_retry(retry_id)
        return await repository.enqueue_retry(
            RetryQueueItem(task_id=task.id, target="n8n", payload=payload, last_error=error)
        )

    try:
        async with httpx.AsyncClient(timeout=settings.N8N_TIMEOUT_SECONDS) as client:
            response = await client.post(settings.N8N_WEBHOOK_URL, json=payload)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        await repository.update_task_status(task.id, TaskStatus.BLOCKED)
        error = str(exc)
        logger.error("n8n dispatch failed", extra={"context": {"task_id": task.id, "error": error}})
        if retry_id:
            await repository.mark_retry_failed(retry_id, error)
            return await repository.get_retry(retry_id)
        return await repository.enqueue_retry(
            RetryQueueItem(task_id=task.id, target="n8n", payload=payload, last_error=error)
        )

    await repository.update_task_status(task.id, TaskStatus.DISPATCHED)
    if retry_id:
        await repository.mark_retry_completed(retry_id)
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
    if abs(int(datetime.now(timezone.utc).timestamp()) - int(timestamp)) > 300:
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


@router.get("/persistence")
async def persistence_status(_: str = Depends(require_gcagent_auth)) -> Dict[str, Any]:
    return repository_status()


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
    await repository.ensure_job(job_id)
    category = classify_transcript(clean_transcript)
    routed_to = route_task(category)
    task = await repository.create_task(
        GCTask(
            job_id=job_id,
            source="voice-command",
            category=category,
            title=clean_transcript[:80],
            transcript=clean_transcript,
            assignee=routed_to,
        )
    )
    audit = await repository.append_audit(
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
    return VoiceCommandResponse(
        job_id=job_id,
        task_id=task.id,
        audit_id=audit.id,
        routed_to=routed_to,
        n8n_status="queued_for_retry" if retry else "dispatched",
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
    await repository.append_audit(
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
    await repository.ensure_job(change_order_data.job_id)
    change_order = await repository.create_change_order(
        ChangeOrder(**jsonable_model(change_order_data))
    )
    await repository.append_audit(
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
    decision_status = (
        ChangeOrderStatus.APPROVED if decision.approved else ChangeOrderStatus.REJECTED
    )
    change_order = await repository.decide_change_order(
        change_order_id,
        decision_status,
        decision.approver,
        datetime.now(timezone.utc),
    )
    if change_order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Change order not found")
    await repository.append_audit(
        change_order.job_id,
        change_order.task_id,
        decision.approver,
        f"change_order.{change_order.status.value}",
        {"change_order_id": change_order_id, "note": decision.note},
    )
    return change_order


@router.get("/jobs/{job_id}/log.pdf")
async def job_log_pdf(job_id: str, _: str = Depends(require_gcagent_auth)) -> Response:
    job = await repository.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    audits = await repository.list_audits(job_id)
    lines = [
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        f"Job: {job.name}",
        "Audit chain:",
        *[
            f"{audit.created_at.isoformat()} {audit.action} task={audit.task_id or '-'} hash={audit.hash[:12]}"
            for audit in audits
        ],
    ]
    return Response(build_minimal_pdf(f"GCagent Job Log {job_id}", lines), media_type="application/pdf")


@router.get("/change-orders/{change_order_id}.pdf")
async def change_order_pdf(
    change_order_id: str,
    _: str = Depends(require_gcagent_auth),
) -> Response:
    change_order = await repository.get_change_order(change_order_id)
    if change_order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Change order not found",
        )
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
    item = await repository.get_retry(retry_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Retry item not found")
    task = await repository.get_task(item.task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    audit = await repository.append_audit(
        task.job_id,
        task.id,
        "retry-worker",
        "retry.n8n.started",
        {"retry_id": retry_id},
    )
    retry = await dispatch_to_n8n(task, audit, retry_id=retry_id)
    current = await repository.get_retry(retry_id)
    return {"status": current.status if current else ("pending" if retry else "completed")}
