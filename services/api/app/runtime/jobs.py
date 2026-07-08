import logging

from fastapi import APIRouter, HTTPException

from app.service.files import FileKeyError, get_asset_url
from app.service.inpainting import run_job
from app.service.jobs import (
    JobNotFound,
    JobStateError,
    JobValidationError,
    approve,
    create_job,
    delete_job,
    get_inpainting_stats,
    get_job,
    list_jobs,
    list_library,
)
from app.types import (
    ApproveRequest,
    InpaintingStats,
    Job,
    JobCreateRequest,
    LibraryItem,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Library + inline assets (static paths first) ---


@router.get("/library", response_model=list[LibraryItem])
async def library_endpoint():
    return list_library()


@router.get("/assets/preview")
async def asset_preview_endpoint(key: str):
    """Inline presigned URL so a source/mask/output/approved asset paints in the
    browser."""
    try:
        return {"url": get_asset_url(key)}
    except FileKeyError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None


# --- Jobs ---


@router.get("/jobs", response_model=list[Job])
async def list_jobs_endpoint():
    return list_jobs()


@router.get("/jobs/stats", response_model=InpaintingStats)
async def jobs_stats_endpoint():
    return get_inpainting_stats()


@router.post("/jobs", response_model=Job)
async def create_job_endpoint(req: JobCreateRequest):
    try:
        return create_job(req)
    except JobValidationError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None


@router.get("/jobs/{job_id}", response_model=Job)
async def get_job_endpoint(job_id: str):
    try:
        return get_job(job_id)
    except JobNotFound as e:
        raise HTTPException(status_code=404, detail=e.detail) from None


@router.post("/jobs/{job_id}/run", response_model=Job)
async def run_job_endpoint(job_id: str):
    try:
        return run_job(job_id)
    except JobNotFound as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    except JobStateError as e:
        raise HTTPException(status_code=409, detail=e.detail) from None


@router.post("/jobs/{job_id}/approve", response_model=Job)
async def approve_job_endpoint(job_id: str, req: ApproveRequest):
    try:
        return approve(job_id, req)
    except JobNotFound as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    except JobValidationError as e:
        raise HTTPException(status_code=400, detail=e.detail) from None


@router.delete("/jobs/{job_id}")
async def delete_job_endpoint(job_id: str):
    try:
        delete_job(job_id)
    except JobNotFound as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    logger.info("Job deleted: id=%s", job_id)
    return {"deleted": True, "id": job_id}
