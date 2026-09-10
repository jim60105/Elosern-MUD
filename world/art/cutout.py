"""Local CPU background-removal seam for portrait art (art-portrait-cutout).

Boundary: this module is a local post-process on the TRANSPORT PNG bytes the
sd-webui client returned, applied by ``world/art/worker.py::_settle_one``
between ``client.generate(...)`` and ``world/art/formats.py::encode(...)`` for
portrait subject kinds only (``CUTOUT_SUBJECT_KINDS``). It carries no
persistence, no store path, and no observability logging — it RAISES bounded
``CutoutError`` codes and the worker owns every boundary event, so a stage
outcome is never reported twice.

The backend is an injectable seam exactly like ``ART_SD_CLIENT``:
``resolve_cutout_backend()`` instantiates the ``ART_REMBG_BACKEND`` dotted-path
class, and the real ``RembgCutoutBackend`` wraps the optional ``rembg`` stack.
``rembg``/``onnxruntime`` are imported LAZILY inside the first backend call —
never at module import — so this module stays importable (and the settings
module stays loadable) on a checkout where the optional stack is absent or
broken. Every escaping exception is mapped to exactly one of two bounded
codes; nothing unbounded may leave :func:`remove_background`.
"""

from __future__ import annotations

import importlib
import os
import threading
from pathlib import Path

from django.conf import settings

from world.art.subjects import ArtSubjectKind

# The transport contract is a PNG container (the same 8-byte signature
# ``world/art/sd_worker.py`` and ``world/art/formats.py`` enforce).
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

# PIL modes whose pixels carry an alpha channel. The seam requires the
# backend's return value to satisfy the stage's own postcondition — "PNG bytes
# carrying an alpha channel" — so a passthrough of the original opaque
# portrait can never be stored as a successful cutout (design D5).
_ALPHA_MODES = frozenset({"RGBA", "LA", "PA"})


class CutoutError(Exception):
    """One bounded, named background-removal failure.

    ``code`` is the settle error code: ``art_cutout_unavailable`` (the backend
    or its model could not be made ready) or ``art_cutout_error`` (the backend
    was ready and the removal itself failed). Mirrors
    ``world/art/sd_worker.py::SDError``.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


# The explicit subject-kind allowlist (design D3). Membership test, NEVER the
# negation of ``ArtSubjectKind.SCENE``: a subject kind added later must be
# classified deliberately instead of silently inheriting a cutout. The gate
# covers both publication paths (classic records and gallery jobs) because
# both record shapes carry the same ``kind``.
CUTOUT_SUBJECT_KINDS = frozenset(
    {ArtSubjectKind.CHARACTER, ArtSubjectKind.MONSTER}
)


def applies_to(kind: ArtSubjectKind) -> bool:
    """True when the subject kind is inside the cutout allowlist."""
    return kind in CUTOUT_SUBJECT_KINDS


def resolve_cutout_backend():
    """Instantiate the ``ART_REMBG_BACKEND`` dotted-path class (the seam).

    Mirrors ``world/art/sd_worker.py::resolve_sd_client``. Every resolution
    failure — a non-dotted path, an import error, a missing attribute, or a
    constructor failure — is the bounded ``art_cutout_unavailable`` code, so a
    broken backend path fails only the portrait records that reach it and
    never escapes as an unbounded exception.
    """
    dotted = settings.ART_REMBG_BACKEND
    module_name, separator, class_name = dotted.rpartition(".")
    if not separator:
        raise CutoutError(
            "art_cutout_unavailable",
            f"ART_REMBG_BACKEND {dotted!r} is not a dotted module path",
        )
    try:
        module = importlib.import_module(module_name)
        backend_class = getattr(module, class_name)
        return backend_class()
    except CutoutError:
        raise
    except Exception as error:
        raise CutoutError(
            "art_cutout_unavailable",
            f"could not resolve ART_REMBG_BACKEND {dotted!r}: {error}",
        ) from error


def remove_background(png_bytes: bytes) -> bytes:
    """Remove the background from transport PNG bytes (the module entry point).

    Resolves the configured backend per record (a broken backend then fails
    only the portrait records, while scene batch-mates in the same drain still
    succeed), delegates, and validates the result. Every escaping exception is
    mapped to a bounded ``CutoutError``:

    - resolution/import/session/model problems -> ``art_cutout_unavailable``
    - removal problems, or a return value that fails validation
      (non-``bytes``, empty, missing the PNG magic, or bytes that do not
      decode as an alpha-carrying PNG) -> ``art_cutout_error``

    The validation is decode-only: the validated bytes are returned untouched,
    so ``encode`` receives exactly the backend's output (no re-encode).
    """
    backend = resolve_cutout_backend()
    try:
        result = backend.remove_background(png_bytes)
    except CutoutError:
        raise
    except Exception as error:
        raise CutoutError(
            "art_cutout_error", f"background removal failed: {error}"
        ) from error
    _validate_cutout_bytes(result)
    return result


def _validate_cutout_bytes(result: object) -> None:
    """Reject anything that could not be the alpha cutout the stage promises.

    Beyond the PNG-container check (which keeps a misbehaving backend from
    pushing a bad value into ``encode``, where it would surface as
    ``sd_format_error`` and blame the format stage), the result must decode as
    a PNG whose mode carries an alpha channel: an opaque passthrough stored as
    a "cutout" is the exact silent-degradation outcome the capability forbids.
    """
    import io

    if not isinstance(result, bytes) or not result:
        raise CutoutError(
            "art_cutout_error",
            "backend returned no bytes for the cutout",
        )
    if not result.startswith(_PNG_MAGIC):
        raise CutoutError(
            "art_cutout_error",
            "backend returned bytes that are not a PNG container",
        )
    from PIL import Image

    try:
        with Image.open(io.BytesIO(result)) as opened:
            opened.load()
            mode = opened.mode
    except Exception as error:
        raise CutoutError(
            "art_cutout_error",
            f"backend returned an undecodable PNG: {error}",
        ) from error
    if mode not in _ALPHA_MODES:
        raise CutoutError(
            "art_cutout_error",
            f"backend returned a PNG without an alpha channel (mode {mode!r})",
        )


# One inference session per configured model per process (design D7). The lock
# guards CONSTRUCTION only — check, lock, re-check — never the inference call,
# so a future second worker slot would not serialize on the ~3 s pass.
_session_lock = threading.Lock()
_sessions: dict[str, object] = {}


class RembgCutoutBackend:
    """The real CPU-only backend wrapping the optional ``rembg`` stack.

    Contract (design D7 / D8 / D10, pinned against the locked rembg 2.0.84):

    - ``rembg`` is imported lazily inside the first call, never at module
      import.
    - ``U2NET_HOME`` and ``REMBG_HOME`` are BOTH set to
      ``ART_REMBG_MODEL_DIR`` immediately before the lazy import. rembg
      2.0.84's home resolution reads ``REMBG_HOME`` and lets ``U2NET_HOME``
      win when set, so setting both keeps the same volume across a lock bump
      (intentional belt-and-braces, noted here against the pinned version).
    - ``ART_REMBG_THREADS`` (non-zero) reaches the session as
      ``OMP_NUM_THREADS``: rembg 2.0.84's ``new_session()`` constructs its own
      ``ort.SessionOptions`` and applies ``OMP_NUM_THREADS`` to BOTH the
      inter- and intra-op counts when present (a caller-supplied ``sess_opts``
      parameter exists on that entry point, but the environment path stays the
      mechanism used here). Zero leaves the variable
      untouched and ONNX Runtime's own default stands. Setting the variable is
      a deliberate PROCESS-GLOBAL mutation (it happens once, under the
      construction lock, with deployment settings restart-bound).
    - ``ART_REMBG_DOWNLOAD_ENABLED=false`` verifies the model artifact under
      the model directory BEFORE importing rembg: absent -> an immediate
      ``art_cutout_unavailable`` with no import, no network, and no unbounded
      wait. 2.0.84 writes the per-model layout
      (``<home>/models/<model>/<model>.onnx``); the flat layout
      (``<home>/<model>.onnx``) of older releases is also accepted, so both
      locations are checked.
    - The session requests exactly ``["CPUExecutionProvider"]``; no GPU
      execution provider is ever requested.
    """

    def remove_background(self, png_bytes: bytes) -> bytes:
        """Remove the background through the cached per-model session."""
        session = self._session()
        from rembg import remove  # noqa: PLC0415 - lazy optional stack (design D7)

        return remove(png_bytes, session=session)

    def _session(self) -> object:
        """Return the cached session for the configured model, building once.

        The cache read is lock-free (the common path after the first build);
        a miss takes the lock and re-checks before constructing (design D7's
        check, lock, re-check), so construction and its process-global
        environment setup are serialized while the ~10 s inference call never
        runs under the lock.
        """
        model = str(settings.ART_REMBG_MODEL)
        session = _sessions.get(model)
        if session is not None:
            return session
        with _session_lock:
            session = _sessions.get(model)
            if session is None:
                session = self._build_session(model)
                _sessions[model] = session
            return session

    def _build_session(self, model: str) -> object:
        """Build one CPU-only session; every failure is ``art_cutout_unavailable``.

        Runs under ``_session_lock``. The environment setup is deliberately
        process-global and one-time: the model home variables point rembg at
        the persistent cache directory, and the thread cap (when set) reaches
        rembg's session factory through ``OMP_NUM_THREADS`` — the mechanism
        the locked 2.0.69 supports (see the class docstring).
        """
        model_dir = Path(settings.ART_REMBG_MODEL_DIR)
        model_dir.mkdir(parents=True, exist_ok=True)
        os.environ["U2NET_HOME"] = str(model_dir)
        os.environ["REMBG_HOME"] = str(model_dir)
        threads = int(settings.ART_REMBG_THREADS)
        if threads > 0:
            os.environ["OMP_NUM_THREADS"] = str(threads)

        if not bool(settings.ART_REMBG_DOWNLOAD_ENABLED):
            for candidate in (
                model_dir / f"{model}.onnx",
                model_dir / "models" / model / f"{model}.onnx",
            ):
                if candidate.is_file():
                    break
            else:
                raise CutoutError(
                    "art_cutout_unavailable",
                    f"ART_REMBG_DOWNLOAD_ENABLED=false and no cached "
                    f"{model!r} model artifact under {model_dir}",
                )

        try:
            # Lazy optional stack: importing rembg pulls onnxruntime, cv2, and
            # pymatting. rembg's own module import calls sys.exit(1) when the
            # onnxruntime backend is missing, so SystemExit is mapped here too.
            from rembg import new_session  # noqa: PLC0415
        except (Exception, SystemExit) as error:  # noqa: BLE001 - bounded mapping (SystemExit included by design, see above)
            raise CutoutError(
                "art_cutout_unavailable",
                f"the rembg stack could not be imported: {error}",
            ) from error
        try:
            return new_session(model, providers=["CPUExecutionProvider"])
        except Exception as error:
            raise CutoutError(
                "art_cutout_unavailable",
                f"the {model!r} inference session could not be built: {error}",
            ) from error
