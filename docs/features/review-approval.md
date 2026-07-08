<!-- last_verified: 2026-07-08 -->
# Feature: Review & Approval

## Purpose
Let a human compare each inpainted output against its source and mask, then
approve the good ones — the quality gate of the remediation workflow.

## Used By
- UI: `/jobs/[id]` detail page
- API: `GET /assets/preview?key=...` (inline URL), `POST /jobs/{id}/approve`

## Core Functions
- `apps/web/src/components/jobs/job-detail.tsx` — per-pair `source | mask |
  output` triptych, run/approve/delete actions
- `apps/web/src/components/inpainting/asset-image.tsx` — renders a B2 object via
  an inline presigned URL
- `app/service/jobs.py::approve` — `copy_object` output(s) into `images/approved/`
- `app/service/files.py::get_asset_url` — inline presigned URL (prefix-allowlisted)
- `app/repo/b2_ops.py::get_inline_url`, `copy_object`

## Inputs
- Approve: `{ output_keys?: string[] | null }` (null/empty = approve all
  completed outputs of the job)

## Outputs
- Approved outputs copied to `images/approved/<filename>` (server-side copy).
- Assets rendered via inline presigned URLs (10-min expiry).

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
- Failed pair: red per-pair status with the error message.

## Verification
- Test file: `services/api/tests/test_jobs.py::test_approve_rejects_non_completed_output`
- Quick verify: `pnpm test:api`

## Related Docs
- [Jobs](jobs.md)
- [Inpainting](inpainting.md)
