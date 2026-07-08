"""Inpainting job lifecycle — create, read, delete, approve — plus the Library
listing and storage-amplification stats.

State lives entirely in B2 (no database): each job is `images/jobs/<id>.json`,
outputs land under `images/output/<id>/`, approvals are server-side copies into
`images/approved/`.
"""

import logging
import uuid
from datetime import UTC, datetime

from app.repo import (
    copy_object,
    delete_objects,
    get_object_bytes,
    list_all,
    put_object,
)
from app.types import (
    ApproveRequest,
    InpaintingStats,
    Job,
    JobCreateRequest,
    JobPair,
    JobStatus,
    LibraryItem,
    PairStatus,
    PrefixBytes,
)
from app.types.formatting import humanize_bytes

logger = logging.getLogger(__name__)

SOURCE_PREFIX = "images/source/"
MASK_PREFIX = "images/masks/"
OUTPUT_PREFIX = "images/output/"
APPROVED_PREFIX = "images/approved/"
JOBS_PREFIX = "images/jobs/"


class JobNotFound(Exception):
    def __init__(self, job_id: str):
        self.detail = f"Job '{job_id}' not found"
        super().__init__(self.detail)


class JobValidationError(Exception):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class JobStateError(Exception):
    """Raised for an operation illegal in the job's current state (e.g. running
    an already-completed, immutable job)."""

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


def _filename(key: str) -> str:
    return key.rsplit("/", 1)[-1]


def _stem(filename: str) -> str:
    return filename.rsplit(".", 1)[0] if "." in filename else filename


def _mask_index() -> dict[str, str]:
    """Map source-image stem -> mask key, for auto-pairing by base filename."""
    index: dict[str, str] = {}
    for obj in list_all(MASK_PREFIX):
        name = _filename(obj["key"])
        if name:
            index[_stem(name)] = obj["key"]
    return index


# --- Library -------------------------------------------------------------


def list_library() -> list[LibraryItem]:
    """List every source image with its pairing status (matched mask present?)."""
    masks = _mask_index()
    items: list[LibraryItem] = []
    for obj in list_all(SOURCE_PREFIX):
        name = _filename(obj["key"])
        if not name:  # skip the folder placeholder key itself
            continue
        mask_key = masks.get(_stem(name))
        items.append(
            LibraryItem(
                source_key=obj["key"],
                source_filename=name,
                size_bytes=obj["size"],
                size_human=humanize_bytes(obj["size"]),
                uploaded_at=obj["last_modified"],
                has_mask=mask_key is not None,
                mask_key=mask_key,
            )
        )
    items.sort(key=lambda i: i.uploaded_at, reverse=True)
    return items


# --- Job CRUD ------------------------------------------------------------


def _job_key(job_id: str) -> str:
    return f"{JOBS_PREFIX}{job_id}.json"


def save_job(job: Job) -> None:
    put_object(
        _job_key(job.id),
        job.model_dump_json().encode("utf-8"),
        "application/json",
    )


def create_job(req: JobCreateRequest) -> Job:
    if not req.source_keys:
        raise JobValidationError("Select at least one source image")

    masks = _mask_index()
    pairs: list[JobPair] = []
    unmatched: list[str] = []
    for source_key in req.source_keys:
        if not source_key.startswith(SOURCE_PREFIX):
            raise JobValidationError(
                f"'{source_key}' is not a source image under {SOURCE_PREFIX}"
            )
        name = _filename(source_key)
        mask_key = masks.get(_stem(name))
        if mask_key is None:
            unmatched.append(name)
            continue
        pairs.append(
            JobPair(source_key=source_key, source_filename=name, mask_key=mask_key)
        )

    if unmatched:
        raise JobValidationError(
            "These sources have no matching mask in "
            f"{MASK_PREFIX}: {', '.join(unmatched)}"
        )

    job = Job(
        id=uuid.uuid4().hex,
        label=req.label or None,
        status=JobStatus.PENDING,
        created_at=datetime.now(UTC),
        pairs=pairs,
    )
    save_job(job)
    logger.info("Job created: id=%s pairs=%d", job.id, len(pairs))
    return job


def get_job(job_id: str) -> Job:
    try:
        raw = get_object_bytes(_job_key(job_id))
    except RuntimeError as e:
        logger.info("Job read failed for %s: %s", job_id, e)
        raise JobNotFound(job_id) from None
    return Job.model_validate_json(raw)


def list_jobs() -> list[Job]:
    jobs: list[Job] = []
    for obj in list_all(JOBS_PREFIX):
        if not obj["key"].endswith(".json"):
            continue
        try:
            jobs.append(Job.model_validate_json(get_object_bytes(obj["key"])))
        except Exception:  # skip a single corrupt record, keep listing the rest
            logger.warning("Skipping unreadable job record: %s", obj["key"])
    jobs.sort(key=lambda j: j.created_at, reverse=True)
    return jobs


def delete_job(job_id: str) -> None:
    """Delete a job record and ONLY its own output prefix. Never touches other
    jobs or prefixes."""
    job = get_job(job_id)  # 404s if missing
    output_keys = [obj["key"] for obj in list_all(f"{OUTPUT_PREFIX}{job.id}/")]
    delete_objects(output_keys)
    delete_objects([_job_key(job.id)])
    logger.info("Job deleted: id=%s removed_outputs=%d", job.id, len(output_keys))


def approve(job_id: str, req: ApproveRequest) -> Job:
    """Copy completed outputs into images/approved/ (server-side copy)."""
    job = get_job(job_id)
    completed = {
        p.output_key: p
        for p in job.pairs
        if p.status == PairStatus.COMPLETED and p.output_key
    }
    targets = req.output_keys or list(completed.keys())
    approved = 0
    for output_key in targets:
        if output_key not in completed:
            raise JobValidationError(
                f"'{output_key}' is not a completed output of this job"
            )
        copy_object(output_key, f"{APPROVED_PREFIX}{_filename(output_key)}")
        approved += 1
    logger.info("Job approved: id=%s approved_outputs=%d", job.id, approved)
    return job


# --- Dashboard stats -----------------------------------------------------


def get_inpainting_stats() -> InpaintingStats:
    """Aggregate bytes-by-prefix to tell the storage-amplification (~3x) story."""
    objects = list_all("")

    def _sum(prefix: str, images_only: bool = False) -> tuple[int, int]:
        total, count = 0, 0
        for obj in objects:
            key = obj["key"]
            if not key.startswith(prefix) or key == prefix:
                continue
            if images_only and key.endswith(".json"):
                continue
            total += obj["size"]
            count += 1
        return total, count

    source_bytes, _ = _sum(SOURCE_PREFIX)
    mask_bytes, _ = _sum(MASK_PREFIX)
    output_bytes, images_inpainted = _sum(OUTPUT_PREFIX, images_only=True)
    approved_bytes, approved_count = _sum(APPROVED_PREFIX)

    total_jobs = sum(
        1
        for obj in objects
        if obj["key"].startswith(JOBS_PREFIX) and obj["key"].endswith(".json")
    )
    completed_jobs = len(
        {
            obj["key"][len(OUTPUT_PREFIX) :].split("/", 1)[0]
            for obj in objects
            if obj["key"].startswith(OUTPUT_PREFIX)
            and "/" in obj["key"][len(OUTPUT_PREFIX) :]
        }
    )
    ratio = (output_bytes + mask_bytes) / source_bytes if source_bytes else 0.0

    return InpaintingStats(
        total_jobs=total_jobs,
        completed_jobs=completed_jobs,
        images_inpainted=images_inpainted,
        approved_count=approved_count,
        source_bytes=source_bytes,
        mask_bytes=mask_bytes,
        output_bytes=output_bytes,
        approved_bytes=approved_bytes,
        amplification_ratio=round(ratio, 2),
        by_prefix=[
            PrefixBytes(prefix="source", bytes=source_bytes, count=_sum(SOURCE_PREFIX)[1]),
            PrefixBytes(prefix="masks", bytes=mask_bytes, count=_sum(MASK_PREFIX)[1]),
            PrefixBytes(prefix="output", bytes=output_bytes, count=images_inpainted),
            PrefixBytes(prefix="approved", bytes=approved_bytes, count=approved_count),
        ],
    )
