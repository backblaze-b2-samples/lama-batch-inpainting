<!-- last_verified: 2026-07-08 -->
# Feature: Review & Approval

## Purpose
Let a human compare each inpainted output against its source and mask, then
approve the good ones — the quality gate of the remediation workflow.

## Used By
- UI: `/jobs/[id]` detail page
- API: `GET /assets/preview?key=...` (inline URL), `POST /jobs/{id}/approve`,
  `GET /jobs/{id}/approvals` (persistent approved state)

## Core Functions
- `apps/web/src/components/jobs/job-detail.tsx` — per-pair `source | mask |
  output` triptych, run/approve/delete actions, and a persistent per-pair
  "Approved" badge + an `N/total approved` count in the job header
- `apps/web/src/components/inpainting/asset-image.tsx` — renders a B2 object via
  an inline presigned URL
- `apps/web/src/lib/queries.ts` — `useApproveJob` (invalidates approvals on
  success), `useJobApprovals` (reads persistent approved state)
- `app/service/jobs.py::approve` — `copy_object` output(s) into `images/approved/`
- `app/service/jobs.py::get_job_approvals` — lists `images/approved/` and returns
  which of the job's output_keys already have an approved copy
- `app/service/files.py::get_asset_url` — inline presigned URL (prefix-allowlisted)
- `app/repo/b2_ops.py::get_inline_url`, `copy_object`, `list_all`

## Inputs
- Approve: `{ output_keys?: string[] | null }` (null/empty = approve all
  completed outputs of the job)

## Outputs
- Approved outputs copied to `images/approved/<filename>` (server-side copy).
- `GET /jobs/{id}/approvals` → `JobApprovals { job_id, approved_output_keys[] }`
  — the output_keys of this job whose approved copy exists (keyed by output
  filename). Drives the persistent "Approved" badge and header count.
- Assets rendered via inline presigned URLs (10-min expiry).

## Persistent approved state
Approval used to be visible only transiently (a toast) — a returning user
couldn't tell which outputs were approved. The job page now derives persistent
state from `GET /jobs/{id}/approvals`: each approved pair card shows an
"Approved" badge and its per-pair button switches to a disabled "Approved"
state, and the header shows `N/total approved`. `useApproveJob` invalidates the
approvals query on success, so the badge appears without a manual reload.

## Why inline URLs
The download URL forces `attachment` disposition. The review UI uses a separate
`inline` presigned URL so the source, mask, and output actually paint in
`<img>` tags.

## Edge Cases
- Approving a key that isn't a completed output of the job → `400`.
- Asset key outside the app's allowed prefixes → `400`.
- Output not yet produced (pending/failed pair) → the output column shows a
  placeholder.

## UX States
- Pending job: "Run inpainting" button; output columns empty.
- Completed: outputs rendered; per-pair "Approve" + "Approve all".
- Approved: per-pair "Approved" badge + disabled "Approved" button; header shows
  `N/total approved`. Survives reload/return.
- Failed pair: red per-pair status with the error message.

## Verification
- Test file: `services/api/tests/test_jobs.py::test_approve_rejects_non_completed_output`,
  `services/api/tests/test_jobs.py::test_get_job_approvals_reflects_approved_copies`
- Quick verify: `pnpm test:api`

## Related Docs
- [Jobs](jobs.md)
- [Inpainting](inpainting.md)
