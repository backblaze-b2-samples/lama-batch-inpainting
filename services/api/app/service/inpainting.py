"""Run the LaMa inpainting engine over a job's (source, mask) pairs.

Kept separate from `service/jobs.py` so the "run" verb — the heavy,
model-invoking step — is explicit and isolated from plain CRUD. Reads source +
mask bytes from B2, calls the engine, writes one output PNG + JSON sidecar per
pair back to B2, and flips the job to completed.
"""

import json
import logging
from datetime import UTC, datetime

from app.repo import get_object_bytes, lama_engine, put_object
from app.service.jobs import (
    OUTPUT_PREFIX,
    JobStateError,
    get_job,
    save_job,
)
from app.types import Job, JobStatus, PairStatus

logger = logging.getLogger(__name__)


def _stem(filename: str) -> str:
    return filename.rsplit(".", 1)[0] if "." in filename else filename


def run_job(job_id: str) -> Job:
    """Execute inpainting for every paired image in the job. Raises JobNotFound
    if missing, JobStateError if the job is already completed or running.

    This is a synchronous, CPU/GPU-bound call — the runtime layer hands it to a
    worker thread so it never blocks the event loop. Per-pair progress is
    persisted to B2 as each pair finishes, so a client polling GET /jobs/{id}
    mid-run sees a live, advancing state (state lives in B2, no DB)."""
    job = get_job(job_id)
    if job.status == JobStatus.COMPLETED:
        raise JobStateError("Job already completed — create a new job to re-run")
    if job.status == JobStatus.RUNNING:
        raise JobStateError("Job is already running")

    # Flip to RUNNING and persist immediately so a concurrent poll sees a
    # distinct in-progress state before the first pair completes.
    job.status = JobStatus.RUNNING
    save_job(job)

    completed = 0
    for pair in job.pairs:
        if not pair.mask_key:
            pair.status = PairStatus.FAILED
            pair.error = "No matching mask"
        else:
            try:
                source = get_object_bytes(pair.source_key)
                mask = get_object_bytes(pair.mask_key)
                output_png = lama_engine.inpaint(source, mask)
                stem = _stem(pair.source_filename)
                output_key = f"{OUTPUT_PREFIX}{job.id}/{stem}.png"
                put_object(output_key, output_png, "image/png")

                sidecar = {
                    "job_id": job.id,
                    "source_key": pair.source_key,
                    "mask_key": pair.mask_key,
                    "output_key": output_key,
                    "model": job.model,
                    "device": lama_engine.current_device(),
                    "created_at": datetime.now(UTC).isoformat(),
                    "source_bytes": len(source),
                    "output_bytes": len(output_png),
                }
                put_object(
                    f"{OUTPUT_PREFIX}{job.id}/{stem}.json",
                    json.dumps(sidecar).encode("utf-8"),
                    "application/json",
                )

                pair.output_key = output_key
                pair.status = PairStatus.COMPLETED
                pair.error = None
                completed += 1
            except Exception as e:  # record per-pair failure, keep processing rest
                logger.exception("Inpaint failed for %s", pair.source_key)
                pair.status = PairStatus.FAILED
                pair.error = str(e)
        # Persist after every pair so mid-run progress is visible to pollers.
        save_job(job)

    job.device = lama_engine.current_device()
    job.completed_at = datetime.now(UTC)
    job.status = JobStatus.COMPLETED if completed > 0 else JobStatus.FAILED
    save_job(job)
    logger.info(
        "Job run complete: id=%s completed=%d/%d device=%s",
        job.id,
        completed,
        len(job.pairs),
        job.device,
    )
    return job
