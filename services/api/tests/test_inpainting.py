"""Tests for the inpainting "run" verb: live per-pair progress persistence, the
running-state guard, and the non-blocking run endpoint. All B2 and engine calls
are stubbed — no network, no torch, no model download."""

import asyncio
import time
from datetime import UTC, datetime

import pytest

from app.service import inpainting
from app.types import Job, JobPair, JobStatus, PairStatus


def _job(pairs: int = 2, status: JobStatus = JobStatus.PENDING) -> Job:
    return Job(
        id="job1",
        created_at=datetime.now(UTC),
        status=status,
        pairs=[
            JobPair(
                source_key=f"images/source/{i}.jpg",
                source_filename=f"{i}.jpg",
                mask_key=f"images/masks/{i}.png",
            )
            for i in range(pairs)
        ],
    )


def _stub_engine(monkeypatch):
    monkeypatch.setattr(inpainting, "get_object_bytes", lambda key: b"x")
    monkeypatch.setattr(inpainting, "put_object", lambda *a, **k: None)
    monkeypatch.setattr(inpainting.lama_engine, "inpaint", lambda s, m: b"png")
    monkeypatch.setattr(inpainting.lama_engine, "current_device", lambda: "cpu")


def test_run_job_persists_incremental_running_progress(monkeypatch):
    """The job is marked RUNNING before any pair completes, then progress is
    saved after each pair so a mid-run GET reflects an advancing state."""
    job = _job(pairs=2)
    snapshots: list[Job] = []
    monkeypatch.setattr(inpainting, "get_job", lambda jid: job)
    monkeypatch.setattr(
        inpainting, "save_job", lambda j: snapshots.append(j.model_copy(deep=True))
    )
    _stub_engine(monkeypatch)

    result = inpainting.run_job("job1")

    # First persisted snapshot: RUNNING, nothing done yet.
    assert snapshots[0].status == JobStatus.RUNNING
    assert all(p.status == PairStatus.PENDING for p in snapshots[0].pairs)

    # Every RUNNING snapshot advances the done-count one pair at a time.
    running_done = [
        sum(1 for p in s.pairs if p.status != PairStatus.PENDING)
        for s in snapshots
        if s.status == JobStatus.RUNNING
    ]
    assert running_done == [0, 1, 2]

    # Terminal state is COMPLETED and persisted last.
    assert result.status == JobStatus.COMPLETED
    assert snapshots[-1].status == JobStatus.COMPLETED


def test_run_job_rejects_when_already_running(monkeypatch):
    """Guards against a double-run: a job already RUNNING raises JobStateError."""
    job = _job(pairs=1, status=JobStatus.RUNNING)
    monkeypatch.setattr(inpainting, "get_job", lambda jid: job)
    with pytest.raises(inpainting.JobStateError):
        inpainting.run_job("job1")


def test_run_job_rejects_when_already_completed(monkeypatch):
    job = _job(pairs=1, status=JobStatus.COMPLETED)
    monkeypatch.setattr(inpainting, "get_job", lambda jid: job)
    with pytest.raises(inpainting.JobStateError):
        inpainting.run_job("job1")


def test_run_job_marks_failed_when_no_pair_completes(monkeypatch):
    """A pair with no mask fails; if none succeed the job ends FAILED, and the
    failure is still persisted incrementally."""
    job = Job(
        id="job1",
        created_at=datetime.now(UTC),
        pairs=[JobPair(source_key="images/source/a.jpg", source_filename="a.jpg")],
    )
    snapshots: list[Job] = []
    monkeypatch.setattr(inpainting, "get_job", lambda jid: job)
    monkeypatch.setattr(
        inpainting, "save_job", lambda j: snapshots.append(j.model_copy(deep=True))
    )
    _stub_engine(monkeypatch)

    result = inpainting.run_job("job1")

    assert result.status == JobStatus.FAILED
    assert result.pairs[0].status == PairStatus.FAILED
    assert result.pairs[0].error == "No matching mask"
    assert snapshots[0].status == JobStatus.RUNNING


@pytest.mark.asyncio
async def test_run_endpoint_does_not_block_event_loop(client, monkeypatch):
    """A GET must return promptly while a run occupies a worker thread — proving
    the blocking inference was offloaded off the event loop (Finding B2)."""
    from app.runtime import jobs as jobs_runtime

    def slow_run(job_id: str) -> Job:
        # Stand-in for the blocking torch inference. If this ran on the event
        # loop the concurrent GET below would be starved for the full sleep.
        time.sleep(0.4)
        return Job(
            id=job_id,
            created_at=datetime.now(UTC),
            status=JobStatus.COMPLETED,
            pairs=[],
        )

    monkeypatch.setattr(jobs_runtime, "run_job", slow_run)
    monkeypatch.setattr(jobs_runtime, "list_jobs", lambda: [])

    run_task = asyncio.create_task(client.post("/jobs/job1/run"))
    await asyncio.sleep(0.05)  # let the run grab its worker thread

    loop = asyncio.get_event_loop()
    start = loop.time()
    resp = await client.get("/jobs")
    elapsed = loop.time() - start

    assert resp.status_code == 200
    # Returns well before the 0.4s blocking run finishes.
    assert elapsed < 0.3

    run_resp = await run_task
    assert run_resp.status_code == 200
    assert run_resp.json()["status"] == "completed"
