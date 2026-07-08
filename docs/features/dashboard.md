<!-- last_verified: 2026-07-08 -->
# Feature: Dashboard (storage amplification)

## Purpose
Tell the storage-amplification (~3×) story at a glance: how much a remediation
project stores relative to its input, plus recent job activity.

## Used By
- UI: `/` page (dashboard home)
- API: `GET /jobs/stats`, `GET /jobs`

## Core Functions
- `apps/web/src/components/dashboard/inpainting-stats-cards.tsx` — total jobs,
  images inpainted, approved count, amplification ratio
- `apps/web/src/components/dashboard/prefix-bytes-chart.tsx` — bytes by prefix
  (source / masks / output / approved) as proportional bars
- `apps/web/src/components/dashboard/recent-jobs-table.tsx` — most recent jobs
- `apps/web/src/lib/queries.ts` — `useInpaintingStats()`, `useJobs()`
- `services/api/app/service/jobs.py::get_inpainting_stats` — aggregates
  bytes-by-prefix and the amplification ratio from a single paginated list

## Inputs
- None (loads automatically).

## Outputs
- `GET /jobs/stats` → `InpaintingStats` (total_jobs, completed_jobs,
  images_inpainted, approved_count, source/mask/output/approved bytes,
  amplification_ratio, by_prefix[])
- `GET /jobs` → `Job[]` for the recent-jobs table

## Amplification ratio
`(output_bytes + mask_bytes) / source_bytes` — how much the project has grown
beyond its source inputs. `0` when there are no sources yet.

## Edge Cases
- API unavailable → inline error states with retry.
- No data yet → empty states on cards, chart, and table.
- Large bucket → stats paginate through all objects (`ContinuationToken`).

## UX States
- Loading: skeletons for cards, chart, table
- Empty: "No storage yet" / "No jobs yet"
- Loaded: populated metrics

## Verification
- Test file: `services/api/tests/test_jobs.py`
- Quick verify: `pnpm test:api`

## Related Docs
- [Jobs](jobs.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
