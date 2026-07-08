<!-- last_verified: 2026-07-08 -->
# LaMa Batch Inpainting

Clean up large image collections at scale — remove watermarks, unwanted objects,
and distracting elements — with **zero cloud-inference cost**. This sample runs
[**LaMa** (Large-Mask inpainting, `advimman/lama`)](https://github.com/advimman/lama)
**locally** over `(source image, binary mask)` pairs, writes the inpainted output
back to **[Backblaze B2](https://www.backblaze.com/cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-lama-batch-inpainting)**,
and gives you a side-by-side review UI to approve results.

It is built for media agencies, real-estate photo editors, and digital-asset
managers who need repeatable, auditable batch remediation without paying per
image.

## Why B2 — the storage-amplification story

Every source image keeps its matched mask **and** gains a full-resolution
inpainted output, so a remediation project stores roughly **3× its input
volume**. That is exactly the data-heavy, storage-native workload B2 is built
for. B2 is the **sole datastore** here — there is no database. Job records,
source images, masks, outputs, and approved copies all live in one bucket,
reached only through the **S3-compatible API** with a custom user agent and the
standardized `B2_*` env vars.

Object layout in the bucket:

```
images/source/       uploaded source images
images/masks/         binary masks (white = remove), paired by base filename
images/output/<job>/  inpainted PNG + JSON sidecar per source
images/approved/      approved outputs (server-side copies)
images/jobs/<id>.json job records (state lives in B2, not a database)
```

## Features

- **Batch LaMa inpainting (marquee, local).** Runs the Big-LaMa model on your
  machine via `simple-lama-inpainting`. `$0` per run, no API key. Device is
  auto-detected: **CUDA → Apple MPS → CPU**, with a transparent CPU fallback if
  an accelerator op is unsupported. CPU always works.
- **Jobs.** The primary entity — an immutable record of one inpainting run over
  the pairs you selected. Create → run → review → approve → delete.
- **Review UI.** Per-pair `source | mask | inpainted output`, side by side, via
  inline presigned URLs. Approve a single output or all of them.
- **Library.** A read-only, sample-scoped explorer of `images/source/` and
  `images/masks/` that shows each source's pairing status.
- **Destination-aware Upload.** Upload a *source image* or a *mask* — a selector
  routes each to the right prefix.
- **Storage-amplification dashboard.** Total jobs, images inpainted, approved
  count, bytes-by-prefix, and the amplification ratio.
- **Full-bucket explorer** (`/files`), **Settings**, **Design System** — the
  reusable starter-kit scaffolding, kept intact.

## Quick Start

You need: Node.js >= 20, pnpm >= 9, Python >= 3.11, and a free
**[Backblaze B2 account](https://www.backblaze.com/cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-lama-batch-inpainting)**.

**1. Install frontend dependencies**

```bash
pnpm install
```

**2. Set up the backend (installs torch + LaMa)**

```bash
cd services/api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd ../..
```

> `requirements.txt` pulls `torch`, `torchvision`, `opencv-python-headless`, and
> `simple-lama-inpainting`. The first inpainting run downloads the ~200 MB
> `big-lama.pt` checkpoint into the Torch hub cache automatically. To run fully
> offline, pre-download it and point `LAMA_MODEL` at the local file.

**3. Add your B2 credentials**

```bash
cp .env.example .env
```

Then, in the
[Backblaze B2 dashboard](https://secure.backblaze.com/b2_buckets.htm?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=b2ai-lama-batch-inpainting):

1. **Create a bucket** → paste its **Unique Name** into `B2_BUCKET_NAME`, and its
   **region** (e.g. `us-west-004`) into `B2_REGION`. The S3 endpoint is derived
   as `https://s3.<region>.backblazeb2.com` — no endpoint URL to paste.
2. **Create an application key** with read/write/delete → paste **keyID** into
   `B2_APPLICATION_KEY_ID` and **applicationKey** into `B2_APPLICATION_KEY`.

`B2_PUBLIC_URL_BASE` is optional — the app renders every asset via short-lived
presigned URLs, so it works without it.

**4. Run it**

```bash
pnpm dev
```

Frontend at `localhost:3000`, API at `localhost:8000`. Upload a source image and
a matching mask, create a job, run it, and review the result.

`pnpm dev` runs `pnpm doctor` first — a preflight check for the common setup
gotchas (wrong Node/Python version, missing venv, missing or placeholder `.env`,
busy ports).

## Typical workflow

1. **Upload** a source image (destination: *Source image*), then a mask
   (destination: *Mask*) — a black-and-white PNG with the **same base filename**
   so they auto-pair.
2. **Library** shows the source with a "Mask paired" badge.
3. **New Job** → select one or more paired sources → creates a `pending` job.
4. On the job page, click **Run inpainting** → LaMa processes each pair and
   writes outputs to `images/output/<job>/`.
5. **Review** the `source | mask | output` triptych and **Approve** the good
   ones (server-side copy into `images/approved/`).

## Commands

| Command | What it does |
|---------|-------------|
| `pnpm dev` | Start frontend + backend |
| `pnpm dev:web` | Frontend only |
| `pnpm dev:api` | Backend only |
| `pnpm build` | Build frontend |
| `pnpm lint` | Lint frontend |
| `pnpm lint:api` | Lint backend (ruff) |
| `pnpm test:api` | Run backend tests |
| `pnpm check:structure` | Verify layering rules |
| `pnpm test:e2e` | Playwright e2e tests (run `pnpm --filter @lama-batch-inpainting/web exec playwright install chromium` once first) |

## Tech Stack

- TypeScript, Next.js 16, React 19, Tailwind v4, shadcn/ui, TanStack Query
- Python 3.11+, FastAPI, boto3, Pydantic v2, Pillow
- **LaMa** via `simple-lama-inpainting` (PyTorch), local CPU/GPU inference
- Backblaze B2 (S3-compatible object storage) — the sole datastore
- pnpm workspaces (monorepo)

## Credits

- Inpainting model: [`advimman/lama`](https://github.com/advimman/lama) (Big-LaMa),
  wrapped by [`simple-lama-inpainting`](https://github.com/enesmsahin/simple-lama-inpainting).
- Scaffolded from the Backblaze vibe-coding starter kit.

## Documentation Map

| Doc | Purpose |
|-----|---------|
| [AGENTS.md](AGENTS.md) | Agent table of contents — start here |
| [ARCHITECTURE.md](ARCHITECTURE.md) | System layout, layering, data flows |
| [docs/features/](docs/features/) | Feature docs (inpainting, jobs, review, library, upload, browser, dashboard) |
| [docs/app-workflows.md](docs/app-workflows.md) | User journeys |
| [docs/dev-workflows.md](docs/dev-workflows.md) | Engineering workflows and testing |
| [docs/SECURITY.md](docs/SECURITY.md) | Security principles |
| [docs/RELIABILITY.md](docs/RELIABILITY.md) | Reliability expectations |

## License

MIT License - see [LICENSE](LICENSE) for details.
