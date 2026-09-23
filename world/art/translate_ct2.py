"""Local CPU neural-machine-translation backend behind the prompt-translation seam.

This module implements the ``translate(lines) -> tuple[str, ...]`` contract of
``world/art/translate.py`` for the code-only ``ART_TRANSLATE_BACKEND`` seam
(``world.art.translate_ct2.CTranslate2Backend``).

The boundary (design D1/D2/D3 of add-ctranslate2-translate-backend, D1-D7 of
add-translate-model-download-policy):

- A sequence-to-sequence CTranslate2 model executed locally on the CPU. A
  neural MT model cannot refuse a request the way an instruction-tuned chat
  model can, which is the whole reason this engine class exists.
- Model acquisition follows the dual track of
  ``ART_TRANSLATE_DOWNLOAD_ENABLED``. When enabled (the default) and the
  layout check fails on the engine-construction path, the backend fetches the
  Argos Open Tech ``translate-zh_en-1_9`` package once — pinned
  ``https://argos-net.com`` URL, lazily (never at module import or server
  startup), under the construction lock, bounded by request timeouts and a
  streaming size cap, with no retries — into the code-only
  ``ART_TRANSLATE_MODEL_DIR`` volume, verifies the zip and its layout, keeps
  the CC-BY 4.0 README, and lands every required file atomically. Every
  download/verify/unpack/write failure is a bounded ``art_translate_unavailable``
  and degrades through the worker's existing ``art_translate_failed`` warn (the
  authored prompt, the image still produced). When disabled, a missing or
  malformed directory is the bounded ``art_translate_unavailable`` with no
  library import and no outbound request: the supported air-gapped
  configuration (``scripts/fetch-translate-model.sh`` pre-seed).
- The download lifecycle is observable through exactly two backend events:
  ``art_translate_model_download_done`` (info) on success and
  ``art_translate_model_download_failed`` (warn) on the first failure; the
  worker keeps owning the ``art_translate_*`` stage events. This module raises
  ``TranslateError`` and nothing else.
"""

from __future__ import annotations

import io
import os
import shutil
import threading
import time
import uuid
import zipfile
from pathlib import Path
from urllib.request import urlopen

from django.conf import settings

from world.art.translate import TranslateError
from world.observability import log_info, log_warn

# Deterministic decoding width (design D6 of add-ctranslate2-translate-backend):
# fixed beam search, sampling permanently disabled, so the same source text and
# the same model always yield byte-identical output. Nothing else is passed to
# `translate_batch`.
_BEAM_SIZE = 5


# The seeded model layout this backend requires (design D3 and task 5.1 of
# add-ctranslate2-translate-backend), pinned against the actual artifact
# `scripts/fetch-translate-model.sh` produces: an unzipped Argos Open Tech
# `translate-zh_en-1_9.argosmodel` contains, at the package root, `model/` — an
# OpenNMT CTranslate2 model directory holding `config.json`, `model.bin`, and
# `shared_vocabulary.json` — plus `sentencepiece.model`, the SentencePiece
# source model. The archive's `stanza/` entry is the wrapper's
# sentence-boundary data this pipeline deliberately does not use (the seam
# already splits on lines, D1). The `ct2-transformers-converter` route produces
# the same two pieces; an operator lays them out identically. Never guess these
# names, and never require the `model/` directory to contain anything beyond
# the CTranslate2 pair.
_MODEL_DIR = "model"
_SP_MODEL = "sentencepiece.model"


# Dual-track acquisition (add-translate-model-download-policy D1/D4/D5): the
# pinned Argos Open Tech zh->en package. Upstream publishes no digests, so the
# fetch trusts the HTTPS origin, verifies zip integrity and layout, and keeps
# the package README (provenance; the model is CC-BY 4.0) — the same TOFU
# posture as `ART_REMBG_DOWNLOAD_ENABLED=true` fetching ONNX weights; the
# air-gapped track with the seeder script remains the route for operators who
# refuse it.
_PKG = "translate-zh_en-1_9"
_MODEL_URL = "https://argos-net.com/v1/translate-zh_en-1_9.argosmodel"
# Streaming bounds (D4) — generous headroom over the observed 74 MB artifact.
# An oversize Content-Length is rejected before any read; the read loop aborts
# at the cap. Never a post-hoc check after the body was buffered.
_MAX_MODEL_BYTES = 128 * 1024 * 1024
_DOWNLOAD_TIMEOUT_SECONDS = 30
_DOWNLOAD_CHUNK_BYTES = 1 << 20
# The five required entries, mirroring scripts/fetch-translate-model.sh's
# checks plus the package's provenance README, unpacked exactly (never
# `stanza/`).
_REQUIRED_ENTRIES = (
    f"{_PKG}/model/config.json",
    f"{_PKG}/model/model.bin",
    f"{_PKG}/model/shared_vocabulary.json",
    f"{_PKG}/sentencepiece.model",
    f"{_PKG}/README.md",
)

# Per-process failure latch (D4): once a download has failed in this process,
# later calls skip the fetch and fail immediately, so an unreachable network
# cannot make every Han-bearing job re-bill a ~74 MB attempt. Recovery is a
# restart or an operator seed. Per-process GLOBAL, not per-model-dir:
# ART_TRANSLATE_MODEL_DIR is code-only, so a second directory is unreachable
# at run time.
_DOWNLOAD_LATCHED = False


# One engine per configured model directory per process (design D5 of
# add-ctranslate2-translate-backend). The lock guards CONSTRUCTION only —
# check, lock, re-check, (fetch,) build — never the translate call, so a
# future second worker slot would not serialize on model load. Model load is
# seconds; translation is milliseconds; contention is theoretical, but the
# shape mirrors `world/art/cutout.py`'s session cache deliberately.
_ENGINE_LOCK = threading.Lock()
_ENGINES: dict[str, tuple[object, object]] = {}


class CTranslate2Backend:
    """CPU-pinned, refusal-incapable translator behind the translation seam.

    Contract (design D3/D5/D6/D7 of add-ctranslate2-translate-backend and
    D1-D7 of add-translate-model-download-policy, pinned against ctranslate2
    4.8.2 and sentencepiece 0.2.2):

    - The model layout is verified BEFORE any translation library is imported:
      a missing directory, a missing CTranslate2 model directory, or a missing
      SentencePiece model raises ``art_translate_unavailable`` with no import
      and no outbound request on the air-gapped track
      (``ART_TRANSLATE_DOWNLOAD_ENABLED=false``). When downloads are enabled
      and the layout check fails, the backend fetches the pinned
      ``https://argos-net.com`` model package and re-checks the layout, still
      before any library import — the whole check -> fetch -> re-check
      sequence runs under the construction lock, so concurrent callers block
      and then observe the completed layout instead of degrading mid-fetch.
    - ``ctranslate2`` and ``sentencepiece`` are imported LAZILY inside the
      first call that reaches engine construction, never at module import, so
      this module and the settings module stay loadable where the optional
      stack is absent.
    - The engine is built at most once per configured model directory per
      process, under the construction-only lock; a complete layout is NEVER
      re-fetched, refreshed, or upgraded by the server, and a process whose
      download failed never attempts another one (per-process latch) until a
      restart or an operator seed.
    - ``device="cpu"`` is passed explicitly: this process is the Evennia
      server, and a GPU grab would contend with the sd-webui server this
      pipeline feeds. ``ART_TRANSLATE_THREADS`` (non-zero) reaches the
      translator's intra-op thread count; zero leaves the library default.
    - Decoding is fixed-width beam search with sampling disabled.
    - Every escaping failure is bounded: layout, download, load, and
      construction failures map to ``art_translate_unavailable``; encode,
      translate, and decode failures map to ``art_translate_error``. No
      unbounded exception escapes.
    """

    def translate(self, lines: tuple[str, ...]) -> tuple[str, ...]:
        """Translate every offered line, one output string per input line."""
        model_dir = Path(settings.ART_TRANSLATE_MODEL_DIR)
        translator, sp = self._engine(model_dir)
        try:
            source = [sp.encode(line, out_type=str) for line in lines]
            results = translator.translate_batch(source, beam_size=_BEAM_SIZE)
            translated = tuple(
                _detokenize(result.hypotheses[0]) for result in results
            )
        except TranslateError:
            raise
        except Exception as error:  # noqa: BLE001 - bounded mapping (design D3)
            raise TranslateError(
                "art_translate_error", f"prompt translation failed: {error}"
            ) from error
        if len(translated) != len(lines):
            raise TranslateError(
                "art_translate_error",
                "translation returned "
                f"{len(translated)} lines for {len(lines)} inputs",
            )
        return translated

    @staticmethod
    def _check_layout(model_dir: Path) -> None:
        """Verify the seeded layout without importing any translation library.

        ``Path.is_dir()``/``is_file()`` swallow the underlying ``OSError`` for
        unreadable paths, so an unreadable component is treated exactly like a
        missing one — both are ``art_translate_unavailable`` (delta spec:
        "missing or unreadable model component"). A layout check can never
        produce ``art_translate_error``: it runs before any library exists to
        fail, so any surprise is still the unavailable family.
        """
        try:
            ct2_dir = model_dir / _MODEL_DIR
            if not model_dir.is_dir():
                raise TranslateError(
                    "art_translate_unavailable",
                    f"model directory {model_dir} does not exist; seed it "
                    "with scripts/fetch-translate-model.sh and mount it "
                    "at /app/server/.translate in the container",
                )
            required = (
                (ct2_dir / "config.json", f"the CTranslate2 model file "
                 f"{_MODEL_DIR}/config.json"),
                (ct2_dir / "model.bin", f"the CTranslate2 model file "
                 f"{_MODEL_DIR}/model.bin"),
                (model_dir / _SP_MODEL, f"the SentencePiece source model "
                 f"{_SP_MODEL}"),
            )
            for path, description in required:
                if not path.is_file():
                    raise TranslateError(
                        "art_translate_unavailable",
                        f"model directory {model_dir} lacks a CTranslate2 "
                        f"model plus a SentencePiece source model "
                        f"(missing {description})",
                    )
                # A regular file without read permission still satisfies
                # is_file(); probe readability so an unreadable component is
                # detected HERE, before any translation library import
                # (delta spec: "missing or unreadable model component").
                with path.open("rb"):
                    pass
        except TranslateError:
            raise
        except Exception as error:  # noqa: BLE001 - bounded mapping (see above)
            raise TranslateError(
                "art_translate_unavailable",
                f"could not inspect model directory {model_dir}: {error}",
            ) from error

    @staticmethod
    def _engine(model_dir: Path):
        """Return the cached engine for ``model_dir``, building it once.

        Lock-free on the common path; a miss takes the construction lock,
        re-checks the cache, guarantees the seeded layout (check -> fetch ->
        re-check, design D2 of add-translate-model-download-policy), and then
        builds — so two threads racing the first call build exactly one engine
        and concurrent callers block behind a first-use fetch instead of
        degrading mid-fetch.
        """
        key = str(model_dir)
        engine = _ENGINES.get(key)
        if engine is not None:
            return engine
        with _ENGINE_LOCK:
            engine = _ENGINES.get(key)
            if engine is None:
                CTranslate2Backend._ensure_seeded(model_dir)
                engine = CTranslate2Backend._build_engine(model_dir)
                _ENGINES[key] = engine
            return engine

    @staticmethod
    def _ensure_seeded(model_dir: Path) -> None:
        """Guarantee the model layout exists before engine construction begins.

        Runs under ``_ENGINE_LOCK`` (D2). The layout check runs FIRST so an
        operator seed between a failed download and the next call still counts:
        a complete layout is never re-fetched. A failing check with
        ``ART_TRANSLATE_DOWNLOAD_ENABLED=false`` re-raises today's exact
        bounded ``art_translate_unavailable`` before any translation library
        import — structurally no network, because the fetch call site does not
        exist in that branch. A failing check with downloads enabled routes
        through ``_populate`` (fetch + verify + unpack under the lock) and the
        layout is re-checked afterwards; an already-latched process fails
        immediately without a second network attempt.
        """
        try:
            CTranslate2Backend._check_layout(model_dir)
        except TranslateError as error:
            if not bool(settings.ART_TRANSLATE_DOWNLOAD_ENABLED):
                raise
            CTranslate2Backend._populate(model_dir)
            CTranslate2Backend._check_layout(model_dir)

    @staticmethod
    def _populate(model_dir: Path) -> None:
        """Fetch, verify, and unpack the model package into ``model_dir``.

        Runs under ``_ENGINE_LOCK`` (D2) and only when the layout check already
        failed. Every failure — timeout, oversize response, bad zip, unsafe
        member, missing entry, or a write error (``OSError``/ENOSPC on a full
        volume) — raises the bounded ``art_translate_unavailable`` AND trips
        the per-process latch (D4): once a download has failed in this
        process, later calls fail immediately with no further network attempt.
        Recovery is a restart or an operator seed. Exactly two lifecycle
        events are emitted from here: one info on success and one warn on the
        first failure.
        """
        global _DOWNLOAD_LATCHED
        if _DOWNLOAD_LATCHED:
            raise TranslateError(
                "art_translate_unavailable",
                "a previous translation model download failed in this "
                "process; restart the server or seed the model directory "
                "with scripts/fetch-translate-model.sh",
            )
        start = time.monotonic()
        try:
            # Directory creation is part of the landing step and can fail like
            # any write (EROFS/EACCES on a read-only or root-owned volume,
            # ENOSPC) — it must follow the same bounded path: latch, one warn,
            # art_translate_unavailable.
            model_dir.mkdir(parents=True, exist_ok=True)
            body = CTranslate2Backend._download_model()
            CTranslate2Backend._verify_and_unpack(body, model_dir)
        except Exception as error:  # noqa: BLE001 - bounded mapping (D4)
            _DOWNLOAD_LATCHED = True
            log_warn(
                "art_translate_model_download_failed",
                context={"url": _MODEL_URL, "reason": str(error)},
                exc=error,
            )
            raise TranslateError(
                "art_translate_unavailable",
                f"the translation model could not be downloaded: {error}",
            ) from error
        log_info(
            "art_translate_model_download_done",
            context={
                "url": _MODEL_URL,
                "bytes": len(body),
                "duration_ms": int((time.monotonic() - start) * 1000),
            },
        )

    @staticmethod
    def _download_model() -> bytes:
        """Download the pinned model package, streaming under the size cap.

        The cap is enforced as STREAMING bounds (D4): an oversize
        ``Content-Length`` header is rejected before any read, and the read
        loop aborts once the cap is exceeded — never a post-hoc check after
        the body was buffered. The ``timeout`` covers connect and read; there
        are no retries. Any surprise propagates to ``_populate``'s bounded
        mapping.
        """
        with urlopen(_MODEL_URL, timeout=_DOWNLOAD_TIMEOUT_SECONDS) as response:
            declared = response.headers.get("Content-Length")
            if declared is not None:
                try:
                    if int(declared) > _MAX_MODEL_BYTES:
                        raise TranslateError(
                            "art_translate_unavailable",
                            "the model package declares "
                            f"{declared} bytes via Content-Length, over the "
                            f"{_MAX_MODEL_BYTES} byte cap",
                        )
                except TranslateError:
                    raise
                except ValueError:
                    # observability: ignore R2: non-numeric Content-Length falls back to the streaming cap below, which still bounds the response.
                    pass
            body = bytearray()
            while True:
                chunk = response.read(_DOWNLOAD_CHUNK_BYTES)
                if not chunk:
                    break
                body.extend(chunk)
                if len(body) > _MAX_MODEL_BYTES:
                    raise TranslateError(
                        "art_translate_unavailable",
                        "the model package exceeds the "
                        f"{_MAX_MODEL_BYTES} byte cap while streaming",
                    )
            return bytes(body)

    @staticmethod
    def _verify_and_unpack(body: bytes, model_dir: Path) -> None:
        """Verify the archive and land exactly the required pieces atomically.

        Enforces the same verification rules as
        ``scripts/fetch-translate-model.sh``: zip integrity, every member
        inside the package directory with no absolute or ``..`` path segments,
        the five required entries present, and unpacking exactly those pieces
        (never ``stanza/``). Each piece is written to a temp file INSIDE
        ``model_dir`` (never ``/tmp`` — ``os.replace`` never crosses a
        filesystem) and atomically renamed onto its final name, so an
        interrupted fetch leaves a directory that simply fails the layout
        check again and is repaired by the next attempt. Every remaining temp
        is deleted on failure (including ``OSError``/ENOSPC mid-write). The
        backend never deletes existing content except by replacing exactly the
        required filenames — fetch runs only when the layout is already
        invalid, so a valid seed is never in flight while being destroyed.
        """
        temps: list[Path] = []
        try:
            with zipfile.ZipFile(io.BytesIO(body)) as archive:
                bad = archive.testzip()
                if bad is not None:
                    raise TranslateError(
                        "art_translate_unavailable",
                        "the model package failed zip integrity at "
                        f"{bad}",
                    )
                members = archive.namelist()
                for member in members:
                    if not member.startswith(f"{_PKG}/"):
                        raise TranslateError(
                            "art_translate_unavailable",
                            "the model package contains an entry outside "
                            f"the package directory: {member}",
                        )
                    if any(part == ".." for part in member.split("/")):
                        raise TranslateError(
                            "art_translate_unavailable",
                            "the model package contains an unsafe entry "
                            f"path: {member}",
                        )
                for entry in _REQUIRED_ENTRIES:
                    if entry not in members:
                        raise TranslateError(
                            "art_translate_unavailable",
                            "the model package is missing the required "
                            f"entry {entry}",
                        )
                for entry in _REQUIRED_ENTRIES:
                    relative = entry.removeprefix(f"{_PKG}/")
                    dest = model_dir / relative
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    tmp = model_dir / f".{dest.name}.tmp-{uuid.uuid4().hex}"
                    temps.append(tmp)
                    with archive.open(entry) as source:
                        with tmp.open("wb") as out:
                            shutil.copyfileobj(source, out)
                    os.replace(tmp, dest)
                    temps.remove(tmp)
        except Exception as error:
            for tmp in temps:
                tmp.unlink(missing_ok=True)
            if isinstance(error, TranslateError):
                raise
            raise TranslateError(
                "art_translate_unavailable",
                f"the model package could not be unpacked: {error}",
            ) from error

    @staticmethod
    def _build_engine(model_dir: Path) -> tuple[object, object]:
        """Import the optional stack and construct one CPU-pinned engine.

        Runs under ``_ENGINE_LOCK``. Import failure, SentencePiece load
        failure, and translator construction failure are all
        ``art_translate_unavailable`` — the deployment is missing its engine,
        and there is nothing a caller can retry for a moment.
        """
        try:
            # Lazy optional stack: importing ctranslate2 pulls in numpy/pyyaml
            # and sentencepiece; neither is importable on a checkout without
            # the dependencies, and that must never break settings load.
            from ctranslate2 import Translator  # noqa: PLC0415
            import sentencepiece  # noqa: PLC0415
        except Exception as error:  # noqa: BLE001 - bounded mapping (design D3)
            raise TranslateError(
                "art_translate_unavailable",
                f"the translation libraries could not be imported: {error}",
            ) from error
        try:
            sp = sentencepiece.SentencePieceProcessor(
                model_file=str(model_dir / _SP_MODEL)
            )
            kwargs = {"device": "cpu"}  # design D7: pinned, never auto-selected
            threads = int(settings.ART_TRANSLATE_THREADS)
            if threads > 0:
                kwargs["intra_threads"] = threads
            translator = Translator(str(model_dir / _MODEL_DIR), **kwargs)
        except Exception as error:  # noqa: BLE001 - bounded mapping (design D3)
            raise TranslateError(
                "art_translate_unavailable",
                f"the translation engine could not be built: {error}",
            ) from error
        return translator, sp


def _detokenize(pieces: list[str]) -> str:
    """Join SentencePiece pieces back into surface text.

    sentencepiece encodes spaces as U+2581 ('▁'); the decoder must undo that
    mapping itself because ``SentencePieceProcessor.decode`` on raw piece
    strings joins them without converting the marker (verified against the
    shipped zh→en model). Piece strings from a hypothesis always start with
    the marker after the first token, so lstrip the single injected space.
    """
    return "".join(pieces).replace("\u2581", " ").strip()