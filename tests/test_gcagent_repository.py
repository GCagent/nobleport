import asyncio

from api.gcagent import (
    ChangeOrder,
    ChangeOrderStatus,
    GCTask,
    InMemoryGCRepository,
    RetryQueueItem,
    TaskCategory,
    TaskStatus,
)


def test_repository_contract_preserves_canonical_job_ids_and_audit_chain() -> None:
    async def exercise() -> None:
        repository = InMemoryGCRepository()
        job = await repository.ensure_job("NP-GLORIA-2026-001", "12 Gloria Road")
        task = await repository.create_task(
            GCTask(
                job_id=job.id,
                source="test",
                category=TaskCategory.CHANGE_ORDER,
                title="Document added scope",
                transcript="Extra work requires a change order.",
            )
        )
        first = await repository.append_audit(
            job.id,
            task.id,
            "michael",
            "task.created",
            {"project_id": job.id},
        )
        second = await repository.append_audit(
            job.id,
            task.id,
            "michael",
            "task.routed",
            {"route": "ChangeOrderHandler"},
        )

        assert job.id == "NP-GLORIA-2026-001"
        assert second.previous_hash == first.hash
        assert len(await repository.list_audits(job.id)) == 2

    asyncio.run(exercise())


def test_repository_contract_tracks_change_order_and_retry_state() -> None:
    async def exercise() -> None:
        repository = InMemoryGCRepository()
        await repository.ensure_job("NP-GLORIA-2026-001")
        task = await repository.create_task(
            GCTask(
                job_id="NP-GLORIA-2026-001",
                source="test",
                category=TaskCategory.JOBSITE_LOG,
                title="Field note",
                transcript="Baseboard complete.",
            )
        )
        change_order = await repository.create_change_order(
            ChangeOrder(
                job_id=task.job_id,
                task_id=task.id,
                title="Additional finish work",
                description="Add paint and trim scope.",
                cost_delta=5000,
                requested_by="michael",
            )
        )
        decided = await repository.decide_change_order(
            change_order.id,
            ChangeOrderStatus.APPROVED,
            "michael",
            change_order.created_at,
        )
        retry = await repository.enqueue_retry(
            RetryQueueItem(task_id=task.id, target="n8n", payload={"task_id": task.id})
        )
        await repository.mark_retry_failed(retry.id, "n8n unavailable")
        await repository.mark_retry_completed(retry.id)

        assert decided is not None
        assert decided.status == ChangeOrderStatus.APPROVED
        assert (await repository.get_retry(retry.id)).status == "completed"
        assert (await repository.get_task(task.id)).status == TaskStatus.QUEUED

    asyncio.run(exercise())
