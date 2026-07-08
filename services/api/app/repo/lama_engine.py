"""LaMa (Large-Mask inpainting) adapter — the marquee local-inference engine.

All heavy imports (`torch`, `simple_lama_inpainting`) live INSIDE functions, not
at module scope, so `from main import app` and pytest collection never load
torch or download the ~200 MB `big-lama.pt` checkpoint. The model is a cached
singleton, built lazily on first real inpaint call.

Device rule (hard): auto-detect CUDA -> Apple MPS -> CPU. LaMa's Fast-Fourier
Convolution relies on `torch.fft`, which some Apple MPS builds don't implement;
if the accelerator raises an unsupported-op error we transparently rebuild on
CPU and retry once. CPU is the default and always works — no GPU is required.

Deviation note: we use `simple-lama-inpainting`'s published Big-LaMa checkpoint
and its `prepare_img_and_mask` preprocessing, but load the TorchScript module
ourselves with `torch.jit.load(..., map_location=device)`. The library's
`SimpleLama.__init__` omits `map_location`, and its checkpoint is CUDA-tagged, so
`SimpleLama()` raises on any non-CUDA host (CPU or MPS). Passing map_location is
the minimal fix that keeps the sample reproducible from a fresh clone.

Upstream model: `advimman/lama` (Big-LaMa). Wrapper: `simple-lama-inpainting`.
"""

import io
import logging
import threading

logger = logging.getLogger(__name__)

_engine = None
_device: str | None = None
_force_cpu = False
_lock = threading.Lock()


def _select_device() -> str:
    """First available of CUDA -> Apple MPS -> CPU. Never raises."""
    import torch

    if torch.cuda.is_available():
        return "cuda"
    mps = getattr(torch.backends, "mps", None)
    if mps is not None and mps.is_available():
        return "mps"
    return "cpu"


class _LamaRunner:
    """Thin callable around the Big-LaMa TorchScript module.

    Mirrors `simple_lama_inpainting.SimpleLama.__call__`: takes PIL
    (image, mask), returns a PIL image.
    """

    def __init__(self, model, device) -> None:
        self.model = model
        self.device = device

    def __call__(self, image, mask):
        import numpy as np
        import torch
        from PIL import Image
        from simple_lama_inpainting.utils import prepare_img_and_mask

        image_t, mask_t = prepare_img_and_mask(image, mask, self.device)
        with torch.inference_mode():
            inpainted = self.model(image_t, mask_t)
            cur = inpainted[0].permute(1, 2, 0).detach().cpu().numpy()
            cur = np.clip(cur * 255, 0, 255).astype(np.uint8)
            return Image.fromarray(cur)


def _resolve_model_path() -> str:
    import os

    from simple_lama_inpainting.models.model import LAMA_MODEL_URL
    from simple_lama_inpainting.utils import download_model

    from app.config import settings

    if settings.lama_model:
        if not os.path.exists(settings.lama_model):
            raise FileNotFoundError(
                f"LAMA_MODEL points at a missing checkpoint: {settings.lama_model}"
            )
        return settings.lama_model
    # Auto-downloads big-lama.pt into the torch hub cache on first use.
    return download_model(LAMA_MODEL_URL)


def _build(device_str: str) -> _LamaRunner:
    import torch

    device = torch.device(device_str)
    # map_location is REQUIRED: the checkpoint is CUDA-tagged, so loading it on a
    # CPU/MPS host without remapping raises NotImplementedError.
    model = torch.jit.load(_resolve_model_path(), map_location=device)
    model.eval()
    return _LamaRunner(model, device)


def _get_engine() -> _LamaRunner:
    """Return the cached engine, building it on first use.

    Falls back to CPU if the auto-selected accelerator fails to initialize.
    """
    global _engine, _device
    with _lock:
        if _engine is None:
            device_str = "cpu" if _force_cpu else _select_device()
            try:
                _engine = _build(device_str)
                _device = device_str
                logger.info("LaMa engine loaded on device=%s", device_str)
            except Exception as e:  # accelerator init can fail many ways
                if device_str != "cpu":
                    logger.warning(
                        "LaMa init on %s failed (%s); falling back to CPU",
                        device_str,
                        e,
                    )
                    _engine = _build("cpu")
                    _device = "cpu"
                else:
                    raise
        return _engine


def _downgrade_to_cpu() -> None:
    global _engine, _device, _force_cpu
    with _lock:
        _force_cpu = True
        _engine = None
        _device = None


def current_device() -> str:
    """Device the engine is (or would be) running on. Loads nothing."""
    return _device or "cpu"


def inpaint(image_bytes: bytes, mask_bytes: bytes) -> bytes:
    """Run LaMa over one (image, mask) pair and return PNG-encoded output bytes.

    `mask_bytes` is a binary mask (white = region to remove). Guards the
    accelerator path: an unsupported-op error on GPU/MPS transparently falls
    back to CPU.
    """
    from PIL import Image

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    mask = Image.open(io.BytesIO(mask_bytes)).convert("L")

    engine = _get_engine()
    try:
        result = engine(image, mask)
    except (NotImplementedError, RuntimeError) as e:
        if current_device() != "cpu":
            logger.warning(
                "Inpaint on %s failed (%s); retrying on CPU", current_device(), e
            )
            _downgrade_to_cpu()
            engine = _get_engine()
            result = engine(image, mask)
        else:
            raise

    buf = io.BytesIO()
    result.save(buf, format="PNG")
    return buf.getvalue()
