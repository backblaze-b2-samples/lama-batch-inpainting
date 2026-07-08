from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Backblaze B2 (S3-compatible API) ---
    # Standardized B2_* env var names. The S3 endpoint is DERIVED from the
    # region so source code never hardcodes a region string.
    b2_application_key_id: str = ""
    b2_application_key: str = ""
    b2_bucket_name: str = ""
    b2_region: str = ""
    # Optional. When set, public object URLs are built from it; otherwise the
    # app renders assets via short-lived presigned URLs, so this is NOT required
    # at startup.
    b2_public_url_base: str = ""

    api_port: int = 8000
    # Explicit allowlist by default — covers Next on :3000 and the
    # fallback :3001 it picks if 3000 is busy. Production deploys should
    # override with the exact frontend origin.
    api_cors_origins: str = "http://localhost:3000,http://localhost:3001"
    # Optional dev-only escape hatch: a regex that matches additional
    # allowed origins. Empty by default — set this to e.g.
    # `^http://localhost:\d+$` to accept any localhost port without
    # listing each one. NEVER ship this to production.
    api_cors_origin_regex: str = ""

    # Upload limits
    max_file_size: int = 100 * 1024 * 1024  # 100MB

    # Small durable counter (downloads). Point at a persistent volume in
    # production if you care about surviving restarts.
    download_count_file: str = "data/download_count.json"

    # Optional path to a local Big-LaMa TorchScript checkpoint (`big-lama.pt`).
    # When empty the engine auto-downloads it on first use (see repo/lama_engine).
    lama_model: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def b2_endpoint(self) -> str:
        """Derive the regional S3 endpoint from B2_REGION.

        Keeping this derived (rather than a raw endpoint env var) means no
        region string is ever hardcoded in source — the single source of truth
        is the B2_REGION value in `.env`.
        """
        return f"https://s3.{self.b2_region}.backblazeb2.com"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",")]


settings = Settings()
