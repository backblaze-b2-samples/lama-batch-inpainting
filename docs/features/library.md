<!-- last_verified: 2026-07-08 -->
# Feature: Library

## Purpose
A read-only, sample-scoped explorer of this app's own folders —
`images/source/` and `images/masks/` — showing each source's pairing status
(does it have a matching mask?). Distinct from the full-bucket File Browser.

## Used By
- UI: `/library` page
- API: `GET /library`

## Core Functions
- `apps/web/src/components/library/library-view.tsx` — grid of source thumbnails
  with "Mask paired" / "No mask" badges
- `app/service/jobs.py::list_library` — lists sources + masks, pairs by base
  filename stem
- `app/runtime/jobs.py::library_endpoint`

## Inputs
- None (lists the two scoped prefixes).

## Outputs
- `LibraryItem[]`: `source_key`, `source_filename`, `size_human`, `uploaded_at`,
  `has_mask`, `mask_key`

## Pairing rule
A mask pairs with a source when they share the same base filename (extension
ignored): `images/source/photo.jpg` ↔ `images/masks/photo.png`.

## Edge Cases
- Source with no mask → shown with a "No mask" badge; not selectable in New Job.
- Empty library → upload prompt.

## UX States
- Loading: skeleton grid
- Empty: upload prompt
- Loaded: source cards with thumbnails + pairing badges; "New job" CTA

## Relationship to the File Browser
The Library is scoped to this sample's folders and is read-only. The full-bucket
File Browser (`/files`) — part of the starter contract — still browses,
previews, downloads, and deletes everything in the bucket.

## Verification
- Test file: `services/api/tests/test_jobs.py::test_list_library_reports_pairing_status`
- Quick verify: `pnpm test:api`

## Related Docs
- [File Browser](file-browser.md)
- [Jobs](jobs.md)
