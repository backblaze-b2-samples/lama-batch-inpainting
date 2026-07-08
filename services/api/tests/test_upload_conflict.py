"""Unit tests for upload filename handling and destination routing."""

import pytest

from app.service import upload as upload_service
from app.types import FileUploadResponse


def _stub_repo(monkeypatch):
    monkeypatch.setattr(
        upload_service,
        "upload_file",
        lambda file_data, key, content_type: FileUploadResponse(
            key=key,
            filename=key.rsplit("/", 1)[-1],
            size_bytes=len(file_data),
            size_human="5 B",
            content_type=content_type,
            uploaded_at="2026-02-14T00:00:00Z",
            url=None,
            metadata=None,
        ),
    )
    monkeypatch.setattr(
        upload_service,
        "extract_metadata",
        lambda file_data, filename, content_type: None,
    )


def test_upload_defaults_to_source_prefix(monkeypatch):
    """Default destination routes uploads to images/source/."""
    _stub_repo(monkeypatch)
    result = upload_service.process_upload(
        file_data=b"hello",
        filename="photo.png",
        content_type="image/png",
        content_length=5,
    )
    assert result.key == "images/source/photo.png"


def test_upload_mask_destination_uses_masks_prefix(monkeypatch):
    """The 'mask' destination routes uploads to images/masks/."""
    _stub_repo(monkeypatch)
    result = upload_service.process_upload(
        file_data=b"hello",
        filename="photo.png",
        content_type="image/png",
        content_length=5,
        destination="mask",
    )
    assert result.key == "images/masks/photo.png"


def test_upload_allows_duplicate_filename(monkeypatch):
    """B2 is always versioned — re-uploading the same name creates a new version."""
    _stub_repo(monkeypatch)
    result = upload_service.process_upload(
        file_data=b"hello",
        filename="photo.png",
        content_type="image/png",
        content_length=5,
    )
    assert result.key == "images/source/photo.png"


def test_upload_rejects_unknown_destination(monkeypatch):
    """An unknown destination is rejected before any B2 call."""
    _stub_repo(monkeypatch)
    with pytest.raises(upload_service.UploadError):
        upload_service.process_upload(
            file_data=b"hello",
            filename="photo.png",
            content_type="image/png",
            content_length=5,
            destination="somewhere-else",
        )
