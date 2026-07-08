<!-- last_verified: 2026-07-08 -->
# App Workflows

User journeys inside the application.

## Upload sources and masks

- User navigates to `/upload`
- Picks a destination: **Source image** (`images/source/`) or **Mask**
  (`images/masks/`) via the selector
- Drops or selects files; client validates size (max 100MB) and type
- Progress bar per file; toast on success/failure
- Tip: upload the source first, then a black-and-white mask PNG with the **same
  base filename** so they auto-pair
- See: [File Upload](features/file-upload.md)

## Review the Library

- User navigates to `/library`
- Sees every source image under `images/source/` with a thumbnail
- Each source shows "Mask paired" or "No mask"
- "New job" CTA jumps to job creation
- See: [Library](features/library.md)

## Create → Run → Review → Approve a job

- **Create**: `/jobs/new` → select one or more paired sources (a selector over
  the sources actually present) → optional label → creates a `pending` job
- **Run**: on `/jobs/[id]`, click **Run inpainting** → LaMa runs locally over
  each `(source, mask)` pair → outputs written to `images/output/<job>/` → job
  flips to `completed`
- **Review**: the detail page shows each pair as `source | mask | inpainted
  output`, side by side, via inline presigned URLs
- **Approve**: approve a single output or all → server-side copy into
  `images/approved/`
- **Delete**: removes the job record and only its own output prefix
- See: [Jobs](features/jobs.md), [Inpainting](features/inpainting.md),
  [Review & Approval](features/review-approval.md)

## Browse and manage all files

- User navigates to `/files` (the full-bucket explorer, kept from the starter)
- Tree view with preview / download / delete for anything in the bucket
- See: [File Browser](features/file-browser.md)

## View the dashboard

- User navigates to `/`
- Stat cards: total jobs, images inpainted, approved, storage amplification (×)
- Bytes-by-prefix chart tells the ~3× storage-amplification story
- Recent jobs table with status
- See: [Dashboard](features/dashboard.md)
