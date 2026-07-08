<!-- last_verified: 2026-04-22 -->
# Security

Security principles and implementation for LaMa Batch Inpainting.

## Trust Boundaries

- **Frontend -> API**: CORS-restricted to configured origins, scoped to `GET/POST/DELETE/OPTIONS`
- **API -> B2**: Authenticated via `B2_APPLICATION_KEY_ID` + `B2_APPLICATION_KEY`, signature v4. The regional S3 endpoint is derived from `B2_REGION` — no region string is hardcoded.
- **Client -> B2**: Presigned URLs — `attachment` disposition for downloads, `inline` disposition (review UI) so assets paint; both 10-min expiry

## Upload Validation

- Filename sanitization: path traversal, null bytes, unsafe chars stripped
- MIME/extension consistency check against allowlist
- Chunked streaming with size enforcement (100MB default)
- Content-type allowlist (images, text, archives, audio/video)
- Upload destination is a fixed enum (`source` / `mask`) → validated prefix
- Empty file rejection

## File Key Validation

- Empty keys rejected
- Path traversal patterns rejected (`../`, `%2e%2e`, backslashes, null bytes)
- **Prefix allowlist**: the app's own asset URLs and inpainting writes are gated
  by `services/api/app/service/files.py::ALLOWED_PREFIXES` (via `validate_prefix`)
  so a crafted key can't point the pipeline at an arbitrary object
- **Scoped destructive ops**: job deletion batch-deletes only that job's
  `images/output/<id>/` prefix + its record; approve copies only completed
  outputs — never another job's data

## Download Safety

- Download presigned URLs force `Content-Disposition: attachment`
- The review UI uses a separate `inline` presigned URL only for app-owned assets
  under the allowed prefixes

## Secrets Management

- All secrets loaded via environment variables (pydantic-settings)
- Never committed to source control
- `.env.example` documents required variables without values

## Agent Security Rules

- Never commit `.env`, credentials, or API keys
- Never weaken validation without explicit instruction
- Never bypass CORS, auth, or input sanitization
- Always validate at system boundaries
