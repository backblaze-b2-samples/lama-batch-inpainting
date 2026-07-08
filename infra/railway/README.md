# Railway Deployment

Deploy both services (web + api) on Railway.

## Setup

1. Create a new Railway project
2. Add two services from the same repo:

### Web Service (Next.js)
- **Root Directory**: `apps/web`
- **Build Command**: `pnpm install && pnpm build`
- **Start Command**: `pnpm start`
- **Port**: `3000`

### API Service (FastAPI)
- **Root Directory**: `services/api`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

> Note: `requirements.txt` installs `torch` + `torchvision`, so the API image is
> large (multiple GB) and the build is slow. The `big-lama.pt` checkpoint
> (~200 MB) downloads on first inpaint — pre-bake it and set `LAMA_MODEL` (plus a
> persistent volume) to avoid re-downloading on every cold start. Inference is
> CPU-bound here; provision enough CPU/RAM.

## Environment Variables

Set these on the API service:

| Variable | Value |
|----------|-------|
| `B2_APPLICATION_KEY_ID` | Your B2 key ID |
| `B2_APPLICATION_KEY` | Your B2 application key |
| `B2_BUCKET_NAME` | Your bucket name |
| `B2_REGION` | Your bucket region (e.g. `us-west-004`); the S3 endpoint is derived from it |
| `API_CORS_ORIGINS` | Your web service URL (e.g., `https://web-production-xxx.up.railway.app`) |
| `LAMA_MODEL` | (optional) path to a pre-baked `big-lama.pt` checkpoint |

Set this on the Web service:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | Your API service URL (e.g., `https://api-production-xxx.up.railway.app`) |
