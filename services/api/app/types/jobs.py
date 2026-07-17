from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PairStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class JobPair(BaseModel):
    """One (source image, binary mask) pair inside a job."""

    source_key: str
    source_filename: str
    mask_key: str | None = None
    output_key: str | None = None
    status: PairStatus = PairStatus.PENDING
    error: str | None = None


class Job(BaseModel):
    """An immutable record of one inpainting run over one or more pairs.

    Persisted as `images/jobs/<id>.json` in B2 — there is no database.
    """

    id: str
    label: str | None = None
    status: JobStatus = JobStatus.PENDING
    created_at: datetime
    completed_at: datetime | None = None
    model: str = "big-lama"
    device: str | None = None
    pairs: list[JobPair] = []

    @property
    def pair_count(self) -> int:
        return len(self.pairs)


class JobCreateRequest(BaseModel):
    label: str | None = None
    source_keys: list[str]


class ApproveRequest(BaseModel):
    # None / empty => approve every completed output in the job.
    output_keys: list[str] | None = None


class LibraryItem(BaseModel):
    """A source image in `images/source/` plus its pairing status."""

    source_key: str
    source_filename: str
    size_bytes: int
    size_human: str
    uploaded_at: datetime
    has_mask: bool
    mask_key: str | None = None


class PrefixBytes(BaseModel):
    prefix: str
    bytes: int
    count: int


class InpaintingStats(BaseModel):
    """Storage-amplification dashboard metrics (the ~3x story)."""

    total_jobs: int
    completed_jobs: int
    images_inpainted: int
    approved_count: int
    source_bytes: int
    mask_bytes: int
    output_bytes: int
    approved_bytes: int
    # Object-count amplification: stored artifact objects per source
    # (source + mask + output). This is the metric behind the "~3x" story —
    # every source retains its mask AND gains an inpainted output = 3 objects.
    # It can structurally reach 3x; the byte ratio below never can.
    object_amplification: float
    # (output + mask) bytes relative to source bytes — the byte amplification
    # factor. Kept as a secondary detail (masks are ~KB, so this stays near 1x).
    amplification_ratio: float
    by_prefix: list[PrefixBytes]


class JobApprovals(BaseModel):
    """Which of a job's completed outputs have an approved copy in
    `images/approved/` (approvals are keyed by output filename)."""

    job_id: str
    approved_output_keys: list[str]
