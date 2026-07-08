<!-- last_verified: 2026-07-08 -->
# Feature: Inpainting Jobs (primary entity)

## Purpose
A **Job** is an immutable record of one inpainting run over one or more
`(source, mask)` pairs. It is the primary entity — created, run, reviewed, and
deleted. State lives in B2 as `images/jobs/<id>.json` (no database).

## Used By
- UI: `/jobs` (list), `/jobs/new` (create), `/jobs/[id]` (detail/review)
- API: `GET /jobs`, `POST /jobs`, `GET /jobs/{id}`, `POST /jobs/{id}/run`,
  `POST /jobs/{id}/approve`, `DELETE /jobs/{id}`, `GET /jobs/stats`

## Core Functions
- `app/service/jobs.py` — `create_job`, `get_job`, `list_jobs`, `delete_job`,
  `approve`, `get_inpainting_stats`, `save_job`
- `app/service/inpainting.py` — `run_job`
- `app/runtime/jobs.py` — route handlers
- `apps/web/src/components/jobs/` — list, create form, detail/review
- `apps/web/src/lib/queries.ts` — `useJobs`, `useJob`, `useCreateJob`,
  `useRunJob`, `useApproveJob`, `useDeleteJob`

## CRUD + run verbs
| Verb | In UI? | How |
|------|--------|-----|
| create | ✅ | `/jobs/new` — select paired sources (selector over the finite set present, never free text); masks auto-pair by base filename; optional label. |
| run | ✅ | "Run inpainting" on a pending job → LaMa over each pair → outputs + sidecars → status `completed`. Kept distinct from create so a job is assembled then executed. |
| read | ✅ | `/jobs` list + `/jobs/[id]` detail (the Review UI). |
| delete | ✅ | Scoped batch delete of `images/output/<id>/` + the job record. Never touches other prefixes/jobs. |
| edit | ❌ | **Omitted** — a job is an immutable record of one run (source, mask, model, timestamp). Changing inputs is modeled as creating a new job, so an edit form would misrepresent the entity. Recorded in `omitted_ui_verbs`. |

Domain action beyond CRUD: **approve** (see [review-approval.md](review-approval.md)).

## Inputs
- create: `{ label?: string, source_keys: string[] }` (each under `images/source/`)

## Outputs
- `Job` model: `id`, `label`, `status`, `created_at`, `completed_at`, `model`,
  `device`, `pairs[]` (each with source/mask/output keys + per-pair status)

## Edge Cases
- Selecting a source without a matching mask → `400` (create rejects it).
- Deleting a job → only its own `images/output/<id>/` + record removed.
- Reading a missing job → `404`.

## Verification
- Test file: `services/api/tests/test_jobs.py` — pairing, create validation,
  scoped deletion, approve validation (repo stubbed, no network).
- Quick verify: `pnpm test:api`

## Related Docs
- [Inpainting](inpainting.md)
- [Review & Approval](review-approval.md)
- [App Workflows](../app-workflows.md)
