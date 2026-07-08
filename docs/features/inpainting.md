<!-- last_verified: 2026-07-08 -->
# Feature: Batch LaMa Inpainting (marquee)

## Purpose
Remove watermarks, objects, and distractions from images locally with the LaMa
(Large-Mask) model — `$0` per run, no external inference API.

## Used By
- UI: Job detail page ("Run inpainting")
- API: `POST /jobs/{id}/run`
- Engine: `services/api/app/repo/lama_engine.py`

## Core Functions
- `app/repo/lama_engine.py` — `inpaint(image_bytes, mask_bytes) -> png bytes`,
  `_select_device()`, `current_device()`. Lazy cached singleton; torch is
  imported inside functions only.
- `app/service/inpainting.py` — `run_job(job_id)`: reads source + mask from B2,
  calls the engine per pair, writes output PNG + JSON sidecar, flips job status.
- `app/repo/b2_ops.py` — `get_object_bytes`, `put_object`.

## Canonical Files
- Engine adapter: `services/api/app/repo/lama_engine.py`
- Run orchestration: `services/api/app/service/inpainting.py`

## Inputs
- A job's `(source_key, mask_key)` pairs (source under `images/source/`, mask a
  binary PNG under `images/masks/`; white = region to remove).

## Outputs
- `images/output/<job-id>/<name>.png` — inpainted image
- `images/output/<job-id>/<name>.json` — sidecar (model, device, byte sizes)
- Job record flipped to `completed` (or `failed` if every pair failed)

## Device rule (hard)
Auto-detect **CUDA → Apple MPS → CPU**. CPU is the default and always works — no
GPU is required, and there is no unconditional `.cuda()` / `device="cuda"`.
LaMa's Fast-Fourier Convolution uses `torch.fft`, unavailable on some MPS
builds; if the accelerator raises an unsupported-op error (at init or at
inference), the engine transparently rebuilds on CPU and retries once.

## Model / deps
- Model: `advimman/lama` Big-LaMa, via `simple-lama-inpainting` (auto-downloads
  `big-lama.pt` on first use, or set `LAMA_MODEL` to a local checkpoint).
- Pinned in `services/api/requirements.txt`: `torch`, `torchvision`, `numpy<2`,
  `opencv-python-headless`, `simple-lama-inpainting`, `Pillow`.
- The checkpoint is loaded with `torch.jit.load(..., map_location=device)` — the
  upstream `SimpleLama` constructor omits `map_location` and fails on non-CUDA
  hosts, so the adapter loads the module itself while reusing the library's
  preprocessing.

## Edge Cases
- Pair with no matching mask → that pair is marked `failed`, others continue.
- A single pair's inference error → recorded on the pair, job continues.
- Accelerator op unsupported → transparent CPU fallback (see device rule).
- Re-running a completed (immutable) job → `409` — create a new job instead.

## Verification
- Test file: `services/api/tests/test_lama_engine.py` — no-network signature
  guard: asserts the byte-in/byte-out contract and that torch is not imported at
  module scope, using a fake engine (no model download).
- Real end-to-end inference is exercised by the verification pipeline step.
- Quick verify: `pnpm test:api`
- Pass criteria: engine guard tests green; no import-time model load.

## Related Docs
- [Jobs](jobs.md)
- [Review & Approval](review-approval.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
