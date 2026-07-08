"""Extra B2 (S3-compatible) object operations used by the inpainting pipeline.

Kept in the repo layer alongside `b2_client` so all boto3 usage stays contained
here. These are the ops beyond the starter's upload/list/delete surface:
byte-level get/put, server-side copy (used by "approve"), batch delete (used to
tear down a job's output prefix), full-bucket pagination for stats, and an
INLINE presigned URL so images actually paint in the review UI.
"""

import io

from botocore.exceptions import ClientError

from app.config import settings
from app.repo.b2_client import get_s3_client


def get_object_bytes(key: str) -> bytes:
    """Read an object's full body into memory. Raises RuntimeError on failure."""
    client = get_s3_client()
    try:
        response = client.get_object(Bucket=settings.b2_bucket_name, Key=key)
        return response["Body"].read()
    except ClientError as e:
        raise RuntimeError(f"B2 get_object failed for '{key}': {e}") from e


def put_object(key: str, data: bytes, content_type: str) -> None:
    """Write bytes to B2. Raises RuntimeError on failure."""
    client = get_s3_client()
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=key,
            Body=io.BytesIO(data),
            ContentType=content_type,
        )
    except ClientError as e:
        raise RuntimeError(f"B2 put_object failed for '{key}': {e}") from e


def copy_object(source_key: str, dest_key: str) -> None:
    """Server-side copy within the bucket (used by 'approve').

    Raises RuntimeError on failure.
    """
    client = get_s3_client()
    try:
        client.copy_object(
            Bucket=settings.b2_bucket_name,
            CopySource={"Bucket": settings.b2_bucket_name, "Key": source_key},
            Key=dest_key,
        )
    except ClientError as e:
        raise RuntimeError(
            f"B2 copy_object failed for '{source_key}' -> '{dest_key}': {e}"
        ) from e


def delete_objects(keys: list[str]) -> None:
    """Batch-delete objects (max 1000 per request; chunked automatically).

    Raises RuntimeError on failure.
    """
    if not keys:
        return
    client = get_s3_client()
    try:
        for i in range(0, len(keys), 1000):
            chunk = keys[i : i + 1000]
            client.delete_objects(
                Bucket=settings.b2_bucket_name,
                Delete={"Objects": [{"Key": k} for k in chunk], "Quiet": True},
            )
    except ClientError as e:
        raise RuntimeError(f"B2 batch delete failed: {e}") from e


def list_all(prefix: str = "") -> list[dict]:
    """Paginate through every object under `prefix`, returning raw fields.

    Returns dicts with `key`, `size`, `last_modified`. Raises RuntimeError on
    failure.
    """
    client = get_s3_client()
    out: list[dict] = []
    kwargs: dict = {"Bucket": settings.b2_bucket_name, "MaxKeys": 1000}
    if prefix:
        kwargs["Prefix"] = prefix
    try:
        while True:
            response = client.list_objects_v2(**kwargs)
            for obj in response.get("Contents", []):
                out.append(
                    {
                        "key": obj["Key"],
                        "size": obj["Size"],
                        "last_modified": obj["LastModified"],
                    }
                )
            if not response.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = response["NextContinuationToken"]
    except ClientError as e:
        raise RuntimeError(f"B2 list failed for prefix '{prefix}': {e}") from e
    return out


def get_inline_url(key: str, expires_in: int = 600) -> str:
    """Presigned GET URL with INLINE disposition so the asset renders in an
    `<img>`/`<a>` tag (the download variant forces `attachment`).

    Raises RuntimeError on failure.
    """
    client = get_s3_client()
    try:
        return client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.b2_bucket_name,
                "Key": key,
                "ResponseContentDisposition": "inline",
            },
            ExpiresIn=expires_in,
        )
    except ClientError as e:
        raise RuntimeError(f"B2 inline presign failed for '{key}': {e}") from e
