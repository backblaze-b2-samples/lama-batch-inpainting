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
  images inpainted, approved count, and the object-count amplification headline
- `apps/web/src/components/dashboard/prefix-bytes-chart.tsx` — bytes by prefix
  (source / masks / output / approved) as proportional bars, with both the
  object-count and byte amplification ratios in the footer
- `apps/web/src/components/dashboard/recent-jobs-table.tsx` — most recent jobs
- `apps/web/src/lib/queries.ts` — `useInpaintingStats()`, `useJobs()`
- `services/api/app/service/jobs.py::get_inpainting_stats` — aggregates
  bytes-by-prefix and the amplification ratio from a single paginated list

## Inputs
- None (loads automatically).

## Outputs
- `GET /jobs/stats` → `InpaintingStats` (total_jobs, completed_jobs,
  images_inpainted, approved_count, source/mask/output/approved bytes,
  object_amplification, amplification_ratio, by_prefix[])
- `GET /jobs` → `Job[]` for the recent-jobs table

## Amplification metrics
The marquee "why B2" story is that **every source retains its mask AND gains a
full-resolution output — ~3 stored objects per source**. Two ratios express it:

- **`object_amplification`** (the headline): `(source_count + mask_count +
  output_count) / source_count`. This is the honest ~3× metric — it reaches
  3.0× exactly when every source has both a mask and an output. This is what the
  "Storage Amplification" card shows.
- **`amplification_ratio`** (byte ratio, secondary detail): `(output_bytes +
  mask_bytes) / source_bytes`. Masks are ~KB and the retained source bytes are
  excluded, so this stays near 1×; it can **never** approach 3× and is therefore
  a poor proxy for the story. Kept in the chart footer, explicitly labeled
  "Byte amplification", so both numbers are unambiguous.

Both are `0` when there are no sources yet.

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
