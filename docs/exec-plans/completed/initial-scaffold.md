# Scaffold plan — `lama-batch-inpainting`

Source of truth (Phase 0 clone): `.claude/scratch/vcsk-c1194003-740b-43d1-b5da-61938dbfaf3d/`.
Build target: `./lama-batch-inpainting`. Parent standards: `../CLAUDE.md`.

---

## 1. Purpose

`lama-batch-inpainting` is a B2 sample for media agencies, real-estate photo
editors, and digital-asset managers who need to clean up large image
collections — remove watermarks, unwanted objects, or distracting elements — at
scale, with no cloud-inference API cost. It runs **LaMa** (Large-Mask
inpainting, `advimman/lama`) **locally** over `(source image, binary mask)`
pairs, writes the inpainted output back to Backblaze B2, and gives a
side-by-side review UI to approve results. The storyline the sample sells is
**storage amplification**: every source image keeps its matched mask and gains a
full-resolution inpainted output, so a remediation project stores ~3× its input
volume — exactly the data-heavy, B2-native workload the program targets. B2 is
the **sole datastore** (no database), reached only through the **S3-compatible
API** with a custom user-agent and standardized `B2_*` env vars.

## 2. Architecture delta from `vibe-coding-starter-kit`

The starter kit is the ceiling — strip what this app doesn't need, keep the
reusable B2 scaffolding, add the inpainting-specific surface.

### KEEP (as-is — starter contract, do not strip/rename/replace)
- **UI kit / design system** — `apps/web/src/components/ui/`, design tokens in
  `apps/web/src/app/globals.css`, the `/design` page. Build every new screen
  from these primitives; restyle only via tokens.
- **Bucket explorer (full-bucket browse)** — `/files` route + `app/files/` +
  `components/files/`. **Non-negotiable keep** (never removable). Its sidebar
  entry stays.
- **Upload** — `/upload` route + `app/upload/` + `components/upload/`, sidebar
  entry stays. (Adapted below — a destination selector — but the page stays.)
- **Settings** page + sidebar entry. `settings-form.tsx` is the in-repo form-UX
  exemplar (selectors for finite fields + create-form default hints) — mirror it.
- The layered FastAPI backend (`types → config → repo → service → runtime`),
  structural tests, JSON logging, `/health`, `/metrics`, TanStack-Query data
  layer, single-root-`.env` config, doctor preflight, CORS-on-errors ordering.

### TRIM (remove / neutralize — not needed here)
- **PDF metadata path** — drop `PyPDF2` from requirements and the PDF branch of
  `service/metadata.py`; this app handles images only. Keep the Pillow
  image-dimension/EXIF path (still useful for source images). Remove
  `application/pdf` from the upload allowlist. *(Low-risk trim; if unwiring the
  PDF branch is noisy, leaving it inert is acceptable — do not let it block.)*
- **Default dashboard content** — the generic stats-cards / upload-chart /
  recent-uploads-table are illustrative; replace their *content* with
  inpainting metrics (§4.5). Keep the components/layout pattern and the
  runtime→service→repo→query wiring.

### ADD (new for `lama-batch-inpainting`)
- **Jobs** — the primary entity. `/jobs` list + `/jobs/new` create form +
  `/jobs/[id]` detail/review. Sidebar entry "Jobs". (§4.3)
- **Library** — the mandated *sample-specific asset explorer scoped to this
  sample's own folders*: a read-only view of `images/source/` and
  `images/masks/` with pairing status (does each source have a matching mask?).
  `/library` route + sidebar entry. This is **in addition to** the kept
  full-bucket explorer at `/files`, not a replacement.
- **Backend**: `repo/lama_engine.py` (LaMa adapter — heavy `torch`/model import
  isolated here, mirroring the boto3-in-repo containment discipline), new repo
  B2 ops (`get_object` bytes, `copy_object`, batch delete, **inline** presign),
  `service/inpainting.py` + `service/jobs.py`, `runtime/jobs.py`, new Pydantic
  types (`Job`, `JobPair`, `JobStatus`, `InpaintingStats`), new TanStack hooks.
- Pinned ML deps in `requirements.txt` (§4.1) and a no-network signature-guard
  test for the engine.

> **Bucket-explorer tension note:** none. The full-bucket explorer stays at
> `/files`; the scoped Library is an added, distinct view. No conflict.

## 3. B2 surface (S3-compatible API only — no b2-native)

All operations go through `boto3` in `repo/` with `user_agent_extra` set. New
ops beyond what the starter uses are marked ★.

| Operation | Used for |
|-----------|----------|
| `put_object` | upload source/mask (via Upload page → prefix), write output PNGs, write per-image JSON sidecars, write job record `job.json` |
| `list_objects_v2` | Library (source/mask), Jobs list, output listing, dashboard stats (paginated) |
| `get_object` ★ | read source + mask bytes to feed LaMa; read output bytes if needed |
| `head_object` | object metadata |
| `copy_object` ★ | **approve** = server-side copy `output/<job>/<img>` → `approved/<img>` (then optional delete-original = "move") |
| `delete_object` / `delete_objects` ★ | delete a job's `output/<job-id>/` prefix (scoped, batch) |
| `generate_presigned_url` | signed URLs for the review UI to render `<img>`/download. **Add an inline variant** (no `attachment` content-disposition) so source/mask/output actually paint in the browser; keep the existing attachment variant for downloads |

No b2-native API anywhere. `copy_object` and `delete_objects` are standard S3.
**Prefix allowlist:** `service/files.py` validates keys against an allowlist —
extend it to permit `images/source/`, `images/masks/`, `images/output/`,
`images/approved/`, `images/jobs/` (and keep `uploads/` if still referenced).

## 4. Key features

### 4.1 Batch LaMa inpainting (marquee) — `deployment: local`
- **Provider:** none external. **Engine:** `simple-lama-inpainting` (pip-installable
  wrapper around `advimman/lama`'s Big-LaMa JIT model). Chosen over cloning the
  raw research repo because the sample must be **reproducible from a fresh clone**
  — `advimman/lama` needs hydra configs + a manual checkpoint download + heavy
  research deps; `simple-lama-inpainting` installs from PyPI, auto-downloads
  `big-lama.pt` on first use, exposes `SimpleLama()(image, mask) -> PIL.Image`,
  and runs on CPU. Cite `advimman/lama` as the upstream model in the README.
- **Cost for one demo run:** $0 (local inference, no API key).
- **Env var for a key:** none.
- **Device rule (hard):** auto-detect **CUDA → MPS → CPU**. LaMa's
  Fast-Fourier-Convolution uses `torch.fft`, which some MPS builds don't
  implement — **guard the accelerator path so an unsupported-op error at warmup
  transparently falls back to CPU** (on Apple Silicon this typically means CPU).
  CPU is the default and always works.
- **Pinned deps in `requirements.txt`** (unpinned ML = false green; pin a working
  window and smoke-test the import during build): `torch` (CPU, e.g.
  `>=2.2,<2.9`), `numpy<2`, `opencv-python-headless`, `simple-lama-inpainting`
  (pin the installed version), `Pillow`. Resolve exact transitive pins by
  actually installing in the build venv; if `torchvision` is required by the
  import, pin it too. Support a `LAMA_MODEL` env override pointing at a local
  `big-lama.pt` for offline/pre-baked runs (optional).
- **Lazy load, no import-time side effects:** the model must load lazily
  (cached singleton), never at module import, so `from main import app` and test
  collection never download or load weights. Tests must not run real inference
  (mock the engine or guard behind a network/marker) — ship a **no-network
  signature-guard test** asserting the engine wrapper's shape without loading
  the model.

### 4.2 Source/mask Library + destination-aware Upload
- **Library** (`/library`): scoped explorer of `images/source/` and
  `images/masks/`, showing per-source pairing status (matched mask present?).
  Read-only; links a source into "New Job".
- **Upload** (`/upload`, kept): add a **destination selector** — a `Select` /
  `RadioGroup` (finite values → selector, never free text): "Source image" →
  `images/source/`, "Mask (binary PNG)" → `images/masks/`. `process_upload`
  gains a validated `destination` param that maps to the prefix (replaces the
  hardcoded `uploads/`). CREATE-form default hint (guidance, not autofill):
  "Upload the source first, then its mask as a black-and-white PNG with the same
  base filename."

### 4.3 Primary entity — **Inpainting Job** (`job`) lifecycle
One entity, CRUD + run. A **Job** is an immutable record of one inpainting run
over one or more `(source, mask)` pairs the user selected; it produces one
output PNG + JSON sidecar per pair under `images/output/<job-id>/`. Job state
lives in B2 (`images/jobs/<job-id>.json`) — **no database**, consistent with the
starter's "B2 is the sole datastore."

| Verb | In UI? | How |
|------|--------|-----|
| **create** | ✅ | `/jobs/new` — select source image(s) from the Library (selector over the finite set present in `images/source/`, never free text); masks auto-paired by base filename against `images/masks/`; optional free-text job label. Creates a `pending` job record. Default hints as `FormDescription`. |
| **run** | ✅ | "Run inpainting" button on a `pending` job → LaMa over each pair → writes outputs + sidecars, flips status to `completed`. Kept distinct from create so a job can be assembled then executed (batch), and demonstrates the "run" verb explicitly. |
| **read** | ✅ | `/jobs` list (status, pair count, created_at) + `/jobs/[id]` detail = the **Review UI**: per-pair source \| mask \| output side-by-side via inline signed URLs. |
| **delete** | ✅ | Delete a job → scoped batch-delete of `images/output/<job-id>/` + its `images/jobs/<job-id>.json`. **Never** touches other prefixes/jobs. |
| **edit** | ❌ omitted | **UX justification:** a job is an immutable record of one inpainting run (its source, mask, model version, timestamp). Changing inputs yields a different result, which is modeled as *creating a new job*, not editing an existing one — so an edit form would misrepresent the entity. Record in `omitted_ui_verbs`. |

- **Domain action (beyond CRUD): approve** ✅ — on the review page, approve a
  single output or all outputs → `copy_object` to `images/approved/`. This is the
  described "Review" step; build it. (Not one of the mandated CRUD+run verbs, so
  not gated, but it's core to the use case.)

### 4.4 Form UX conventions
- **Selectors for finite fields (create + edit):** New Job source/mask
  selection = a list/`Select` over the files actually present, never free text.
  Upload destination = `Select`/`RadioGroup`. Job label = genuine free text
  (fine as `Input`).
- **Create-form default hints (create only):** `FormDescription`/placeholder
  guidance (e.g. "Pick a source that has a matching mask", "Masks are binary
  PNGs — white = remove"), never a button that autofills the form. Mirror
  `apps/web/src/components/settings/settings-form.tsx`.

### 4.5 Storage-amplification dashboard
Replace default dashboard content with inpainting metrics that tell the 3×
story: total jobs, images inpainted, approved count, and **bytes by prefix**
(`source` / `masks` / `output` / `approved`) with the amplification ratio
(output+mask relative to source). Recent-jobs table replaces recent-uploads.
All aggregations flow through `runtime → service → repo` and a TanStack hook —
no bare `useEffect + fetch`.

### 4.6 Provider orchestration via Genblaze
**Not applicable** — the description names no Genblaze / suggested stack, and the
only heavy workload (LaMa) is local. Use the standard `sample-builder` from
`vibe-coding-starter-kit`; do **not** route through the Genblaze SDK.

## 5. Doc transforms

- **README.md** — full rewrite for `lama-batch-inpainting`: purpose, feature
  list (§4), quickstart with the extra ML step (`pip install -r requirements.txt`
  pulls torch + LaMa; note first-run `big-lama.pt` download + optional
  `LAMA_MODEL`), the storage-amplification pitch, upstream credit to
  `advimman/lama`. Screenshots left to the later pipeline step (do not create
  binary assets).
- **ARCHITECTURE.md** — update components, data stores (add job records +
  image prefixes), data flows (ingest → inpaint → store → review/approve), and
  the new `repo/lama_engine.py` adapter + `copy_object` trust boundary.
- **AGENTS.md** — update repo map / canonical files for the new modules; keep
  the invariants.
- **docs/features/** — keep + adapt `file-upload.md` (destination selector),
  `file-browser.md` (Library vs full explorer). Rewrite `dashboard.md`
  (storage-amplification). **Delete** `metadata-extraction.md` if the PDF path is
  trimmed and image-metadata is folded into upload docs (else adapt). **Add**
  stubs: `inpainting.md`, `jobs.md` (lifecycle), `review-approval.md`,
  `library.md`.
- **docs/app-workflows.md / dev-workflows.md** — update user journeys (create →
  run → review → approve) and the ML setup/testing note.
- **.env.example** — rewrite to Standard #3 names (§6), mark
  `B2_PUBLIC_URL_BASE` optional.

## 6. Rename + standards-alignment table

Every identifier from `vibe-coding-starter-kit` → `lama-batch-inpainting`:

| From | To |
|------|----|
| `vibe-coding-starter-kit` (dir, `package.json` name, pnpm `--filter @vibe-coding-starter-kit/web`, `test:e2e` playwright-install cmd, lockfile pkg refs) | `lama-batch-inpainting` / `@lama-batch-inpainting/web` |
| `APP_NAME = "OSS Starter Kit"` (`lib/app-config.ts`) | `"LaMa Batch Inpainting"` |
| `APP_DESCRIPTION` | `"Batch image inpainting with LaMa, stored on Backblaze B2"` |
| FastAPI `title="OSS Starter Kit API"` (`main.py`) | `"LaMa Batch Inpainting API"` |
| `user_agent_extra="b2ai-oss-start"` (`repo/b2_client.py`) | `"b2ai-lama-batch-inpainting"` |
| README/sidebar UTM `utm_content=b2ai-oss-start` | `utm_content=b2ai-lama-batch-inpainting` |
| `infra/railway/README.md` refs | `lama-batch-inpainting` (note torch image weight; low priority) |

### Standard #3 env-var rename (MANDATORY — starter deviates)
The starter uses `B2_KEY_ID` and `B2_ENDPOINT` and `b2_public_url`. Rename to the
program-standard names in `config/settings.py`, `main.py` (REQUIRED list +
PLACEHOLDER set), `repo/b2_client.py`, `.env.example`, and all docs:

| Starter | Standard #3 (required) |
|---------|------------------------|
| `B2_KEY_ID` | `B2_APPLICATION_KEY_ID` |
| `B2_APPLICATION_KEY` | `B2_APPLICATION_KEY` (unchanged) |
| `B2_BUCKET_NAME` | `B2_BUCKET_NAME` (unchanged) |
| `B2_ENDPOINT` (full URL) | `B2_REGION` (e.g. `us-west-004`) → derive endpoint `https://s3.{B2_REGION}.backblazeb2.com` |
| `b2_public_url` | `B2_PUBLIC_URL_BASE` (**optional** — app works without it via presigned URLs; do NOT require at startup) |

Startup validation (`main.py` lifespan) requires only
`B2_APPLICATION_KEY_ID`, `B2_APPLICATION_KEY`, `B2_BUCKET_NAME`, `B2_REGION`.

### Other must-fix carried from known starter defects
- **Header branding leak** (`components/layout/header.tsx`): the starter
  hardcodes the app name and a "Page" fallback for unlisted routes. Fix so the
  title derives from `APP_NAME` + the pathname, and every new route
  (`/jobs`, `/jobs/new`, `/jobs/[id]`, `/library`) shows a correct title.

## 7. Build order (guidance for the builder)
1. Copy tree, strip `.git`, rename identifiers (§6), fix header, app-config,
   sidebar nav (add Jobs + Library).
2. Backend: settings env rename → b2_client (env + new S3 ops + inline presign)
   → lama_engine → types → service (jobs, inpainting, files-allowlist, upload
   destination, stats) → runtime (jobs router, upload/files/dashboard tweaks).
   Keep every file < 300 lines; keep `boto3` only in `repo/`.
3. Frontend: api-client + queries hooks → Jobs pages (list/new/detail-review) →
   Library → Upload destination selector → dashboard rewrite.
4. Docs (§5), `.env.example`, requirements (§4.1).
5. Run `pnpm lint && pnpm lint:api && pnpm test:api && pnpm check:structure`
   and `pnpm build`; install the ML deps in the venv and smoke-test
   `from simple_lama_inpainting import SimpleLama`.

## 8. omitted_ui_verbs (for build-result.json)
- `{ entity: "job", operation: "edit", justification: "A job is an immutable record of one inpainting run (source, mask, model version, timestamp); changing inputs is modeled as creating a new job, so an edit form would misrepresent the entity." }`
