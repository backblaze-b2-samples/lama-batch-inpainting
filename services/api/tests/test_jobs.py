"""Unit tests for the job service: mask auto-pairing, create validation, and
scoped deletion. Repo (B2) calls are stubbed — no network."""

from datetime import UTC, datetime

import pytest

from app.service import jobs as jobs_service
from app.types import ApproveRequest, JobCreateRequest


def _obj(key: str, size: int = 100):
    return {"key": key, "size": size, "last_modified": datetime.now(UTC)}


def _fake_list_all(mapping):
    """Return a list_all(prefix) stub backed by an explicit prefix->objects map."""

    def _inner(prefix: str = ""):
        return mapping.get(prefix, [])

    return _inner


def test_list_library_reports_pairing_status(monkeypatch):
    monkeypatch.setattr(
        jobs_service,
        "list_all",
        _fake_list_all(
            {
                "images/source/": [
                    _obj("images/source/a.jpg"),
                    _obj("images/source/b.jpg"),
                ],
                "images/masks/": [_obj("images/masks/a.png")],
            }
        ),
    )
    library = {item.source_filename: item for item in jobs_service.list_library()}
    assert library["a.jpg"].has_mask is True
    assert library["a.jpg"].mask_key == "images/masks/a.png"
    assert library["b.jpg"].has_mask is False
    assert library["b.jpg"].mask_key is None


def test_create_job_rejects_source_without_mask(monkeypatch):
    monkeypatch.setattr(
        jobs_service,
        "list_all",
        _fake_list_all({"images/masks/": []}),
    )
    with pytest.raises(jobs_service.JobValidationError):
        jobs_service.create_job(
            JobCreateRequest(source_keys=["images/source/lonely.jpg"])
        )


def test_create_job_builds_paired_job(monkeypatch):
    saved = {}
    monkeypatch.setattr(
        jobs_service,
        "list_all",
        _fake_list_all({"images/masks/": [_obj("images/masks/a.png")]}),
    )
    monkeypatch.setattr(jobs_service, "save_job", lambda job: saved.setdefault("job", job))

    job = jobs_service.create_job(
        JobCreateRequest(label="cleanup", source_keys=["images/source/a.jpg"])
    )
    assert job.status.value == "pending"
    assert job.label == "cleanup"
    assert len(job.pairs) == 1
    assert job.pairs[0].mask_key == "images/masks/a.png"
    assert saved["job"].id == job.id


def test_delete_job_only_touches_its_own_prefix(monkeypatch):
    job_id = "abc123"
    monkeypatch.setattr(
        jobs_service,
        "get_job",
        lambda jid: jobs_service.Job(id=job_id, created_at=datetime.now(UTC), pairs=[]),
    )
    monkeypatch.setattr(
        jobs_service,
        "list_all",
        _fake_list_all(
            {f"images/output/{job_id}/": [_obj(f"images/output/{job_id}/a.png")]}
        ),
    )
    deleted_batches = []
    monkeypatch.setattr(
        jobs_service, "delete_objects", lambda keys: deleted_batches.append(list(keys))
    )

    jobs_service.delete_job(job_id)

    flat = [k for batch in deleted_batches for k in batch]
    # Only this job's output prefix + its record — nothing else.
    assert f"images/output/{job_id}/a.png" in flat
    assert f"images/jobs/{job_id}.json" in flat
    assert all(job_id in k for k in flat)


def test_approve_rejects_non_completed_output(monkeypatch):
    job_id = "job1"
    monkeypatch.setattr(
        jobs_service,
        "get_job",
        lambda jid: jobs_service.Job(id=job_id, created_at=datetime.now(UTC), pairs=[]),
    )
    with pytest.raises(jobs_service.JobValidationError):
        jobs_service.approve(
            job_id, ApproveRequest(output_keys=["images/output/job1/x.png"])
        )
