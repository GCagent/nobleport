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
