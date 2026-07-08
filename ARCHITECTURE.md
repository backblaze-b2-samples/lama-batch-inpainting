<!-- last_verified: 2026-07-08 -->
# Architecture

## Components

- **apps/web/** — Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  - Dashboard with storage-amplification metrics (bytes by prefix, jobs)
  - Jobs: list, create form, and the detail/review UI (source | mask | output)
  - Library: sample-scoped view of `images/source/` + `images/masks/` pairing
  - Destination-aware upload, full-bucket file browser, settings
  - Dark mode via `next-themes`
- **services/api/** — FastAPI backend (layered architecture)
  - REST API for jobs (create/read/run/approve/delete), library, upload, files
  - Local **LaMa** inpainting engine (torch + `simple-lama-inpainting`)
  - B2 S3 integration via boto3 (get/put/copy/delete/list, presigned URLs)
  - Health check endpoint with B2 connectivity verification
  - Structured JSON logging with request tracing; Prometheus-format metrics
- **packages/shared/** — TypeScript type definitions mirroring the Pydantic
  models (Job, JobPair, LibraryItem, InpaintingStats, …)

## Backend Layering

The API follows a strict layered architecture:

```
types/     Pydantic models — no logic, no imports from other layers
  |
config/    Settings (pydantic-settings) — depends only on types
  |
repo/      Data access (boto3 B2 client + LaMa engine) — no business logic
  |
service/   Business logic — calls repo, returns types
  |
runtime/   FastAPI routes — calls service, never repo directly
```

### Layering Rules

1. Dependencies flow downward only: `types` -> `config` -> `repo` -> `service` -> `runtime`
2. No backward imports (e.g., service must not import from runtime)
3. `boto3` **and** the heavy ML imports (`torch`, `simple_lama_inpainting`) live
   only in `repo/`
4. All boundary data uses Pydantic models (no raw dicts across layers)
5. Each file stays under 300 lines

### Directory Structure

```
services/api/
  main.py                  App entrypoint, middleware, router registration
  app/
    types/                 Pydantic models (files, jobs, stats, upload)
    config/                Settings (derives S3 endpoint from B2_REGION)
    repo/                  b2_client.py, b2_ops.py, lama_engine.py
    service/               jobs.py, inpainting.py, files.py, upload.py, metadata.py
    runtime/               FastAPI route handlers (jobs, files, upload, health, metrics)
  tests/                   pytest tests (structural + integration + engine guard)
```

## Data Stores

- **Backblaze B2** — object storage (S3-compatible API), the **sole datastore**
  (no application database):
  - `images/source/` source images, `images/masks/` masks
  - `images/output/<job-id>/` inpainted PNG + JSON sidecar per source
  - `images/approved/` approved outputs (server-side copies)
  - `images/jobs/<id>.json` job records — job state is persisted here as JSON
  - Listing/metadata via S3 `list_objects_v2` / `head_object`

## The LaMa engine (repo/lama_engine.py)

- Loads the Big-LaMa TorchScript checkpoint lazily as a cached singleton — never
  at import time, so `from main import app` and test collection stay light and
  offline.
- Device auto-detect: **CUDA → Apple MPS → CPU**. If the accelerator fails to
  initialize or raises an unsupported-op error at inference (LaMa's FFC uses
  `torch.fft`, unavailable on some MPS builds), it transparently rebuilds on CPU
  and retries. CPU is the default and always works — no GPU required.
- Loads the checkpoint with `torch.jit.load(..., map_location=device)` (the
  upstream `SimpleLama` constructor omits `map_location`, which breaks CPU/MPS
  loads of the CUDA-tagged checkpoint).

## External Services

- **Backblaze B2 S3 API** — storage, retrieval, server-side copy, batch delete,
  presigned URLs.
- No external inference API — the model runs locally.

## Trust Boundaries

See [docs/SECURITY.md](docs/SECURITY.md) for full security documentation.

- **Frontend -> API** — CORS-restricted to configured origins. `CORSMiddleware`
  is registered LAST in `main.py` (outermost) so it wraps **every** response,
  including uncaught-exception 500s.
- **API -> B2** — authenticated via application keys, signature v4. The regional
  endpoint is derived from `B2_REGION`; no region string is hardcoded.
- **Client -> B2** — presigned URLs: `attachment` disposition for downloads,
  `inline` disposition for the review UI so assets paint in the browser.
- **Key validation** — the app's own asset URLs and inpainting writes are gated
  by a prefix allowlist (`service/files.py::ALLOWED_PREFIXES`); `copy_object`
  (approve) and batch `delete_objects` (job teardown) are scoped to a single
  job's own prefix, never another job's.

## Data Flows

- **Upload**: Browser -> `POST /upload` (multipart, with `destination`) -> API
  validates -> `put_object` to `images/source/` or `images/masks/`
- **Create job**: Browser -> `POST /jobs` -> auto-pairs masks by base filename
  -> writes `images/jobs/<id>.json` (status `pending`)
- **Run**: Browser -> `POST /jobs/{id}/run` -> for each pair: `get_object`
  source + mask -> LaMa inpaint -> `put_object` output PNG + sidecar -> flips job
  to `completed`
- **Review/approve**: Browser renders inline presigned URLs; `POST
  /jobs/{id}/approve` -> `copy_object` output(s) into `images/approved/`
- **Delete**: `DELETE /jobs/{id}` -> batch `delete_objects` of
  `images/output/<id>/` + the job record (scoped)

## Observability

- Structured JSON logging on all requests with `request_id`
- Request timing middleware (also the catch-all converting uncaught exceptions
  to a typed JSON 500)
- `/metrics` (Prometheus format) and `/health` (B2 connectivity)

## Canonical Files

- LaMa engine adapter (repo layer): `services/api/app/repo/lama_engine.py`
- Extra B2 object ops (repo layer): `services/api/app/repo/b2_ops.py`
- B2 client + config: `services/api/app/repo/b2_client.py`, `app/config/settings.py`
- Job lifecycle service: `services/api/app/service/jobs.py`
- Inpainting run service: `services/api/app/service/inpainting.py`
- Jobs route handlers: `services/api/app/runtime/jobs.py`
- Pydantic models: `services/api/app/types/` (`jobs.py`, `files.py`, `stats.py`)
- Structural tests: `services/api/tests/test_structure.py`
- Frontend API client / data layer: `apps/web/src/lib/api-client.ts`, `lib/queries.ts`
- Shared TypeScript types: `packages/shared/src/types.ts`

## Core Features

- [Inpainting](docs/features/inpainting.md)
- [Jobs](docs/features/jobs.md)
- [Review & Approval](docs/features/review-approval.md)
- [Library](docs/features/library.md)
- [File Upload](docs/features/file-upload.md)
- [File Browser](docs/features/file-browser.md)
- [Dashboard](docs/features/dashboard.md)

## References

- [docs/SECURITY.md](docs/SECURITY.md) — security principles and implementation
- [docs/RELIABILITY.md](docs/RELIABILITY.md) — reliability expectations
- [AGENTS.md](AGENTS.md) — architectural invariants and agent instructions
