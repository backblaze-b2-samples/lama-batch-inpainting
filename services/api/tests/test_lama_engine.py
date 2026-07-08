"""No-network signature guard for the LaMa engine adapter.

Verifies the byte-in / byte-out contract and the device API WITHOUT loading the
~200 MB Big-LaMa checkpoint or importing torch — so this runs in CI and on a
fresh clone with no model download. Real inference is exercised by the end-to-end
verification step, not here.
"""

import io

from PIL import Image

from app.repo import lama_engine


def _png(size=(8, 8), color=(120, 120, 120)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def _mask_png(size=(8, 8)) -> bytes:
    buf = io.BytesIO()
    Image.new("L", size, 0).save(buf, format="PNG")
    return buf.getvalue()


def test_engine_exposes_expected_api():
    assert callable(lama_engine.inpaint)
    assert callable(lama_engine.current_device)
    assert callable(lama_engine._select_device)


def test_no_heavy_imports_at_module_scope():
    """torch / SimpleLama must NOT be imported at module load (lazy singleton)."""
    assert not hasattr(lama_engine, "torch")
    assert not hasattr(lama_engine, "SimpleLama")


def test_current_device_defaults_to_cpu_without_loading():
    # Nothing loaded yet -> reports a safe default, no model, no network.
    assert lama_engine.current_device() in {"cpu", "cuda", "mps"}


def test_inpaint_contract_with_fake_engine(monkeypatch):
    """inpaint() decodes bytes, calls the engine, and returns PNG bytes — proven
    with a fake engine so no real model is loaded."""

    class FakeEngine:
        def __call__(self, image, mask):
            # Mirror SimpleLama's contract: takes PIL images, returns a PIL image.
            assert isinstance(image, Image.Image)
            assert isinstance(mask, Image.Image)
            return Image.new("RGB", image.size, (10, 20, 30))

    monkeypatch.setattr(lama_engine, "_get_engine", lambda: FakeEngine())

    out = lama_engine.inpaint(_png(), _mask_png())
    assert isinstance(out, bytes)
    # PNG magic number — the output is a real PNG.
    assert out[:8] == b"\x89PNG\r\n\x1a\n"
    assert Image.open(io.BytesIO(out)).size == (8, 8)
