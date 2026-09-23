"""Local CPU neural-machine-translation backend behind the prompt-translation seam.

This module implements the ``translate(lines) -> tuple[str, ...]`` contract of
``world/art/translate.py`` for the code-only ``ART_TRANSLATE_BACKEND`` seam
(``world.art.translate_ct2.CTranslate2Backend``).

The boundary, deliberately narrow (design D1/D2/D3):

- A sequence-to-sequence CTranslate2 model executed locally on the CPU. A
  neural MT model cannot refuse a request the way an instruction-tuned chat
  model can, which is the whole reason this engine class exists.
- No network access of any kind: the game server never downloads, fetches, or
  otherwise populates the model directory. A missing or malformed directory is
  the bounded ``art_translate_unavailable``, and the degraded path
  (one ``art_translate_failed`` warn, the authored prompt, the image still
  produced) belongs to the worker.
- No observability call: the worker owns the ``art_translate_*`` boundary
  events. This module raises ``TranslateError`` and nothing else.
"""

from __future__ import annotations

import threading
from pathlib import Path

from django.conf import settings

from world.art.translate import TranslateError

# Deterministic decoding width (design D6): fixed beam search, sampling
# permanently disabled, so the same source text and the same model always
# yield byte-identical output. Nothing else is passed to `translate_batch`.
_BEAM_SIZE = 5


# The seeded model layout this backend requires (design D3, task 5.1), pinned
# against the actual artifact `scripts/fetch-translate-model.sh` produces:
# an unzipped Argos Open Tech `translate-zh_en-1_9.argosmodel` contains, at
# the package root, `model/` — an OpenNMT CTranslate2 model directory holding
# `config.json`, `model.bin`, and `shared_vocabulary.json` — plus
# `sentencepiece.model`, the SentencePiece source model. The archive's
# `stanza/` entry is the wrapper's sentence-boundary data this pipeline
# deliberately does not use (the seam already splits on lines, D1). The
# `ct2-transformers-converter` route produces the same two pieces; an operator
# lays them out identically. Never guess these names, and never require the
# `model/` directory to contain anything beyond the CTranslate2 pair.
_MODEL_DIR = "model"
_SP_MODEL = "sentencepiece.model"


# One engine per configured model directory per process (design D5). The lock
# guards CONSTRUCTION only — check, lock, re-check — never the translate call,
# so a future second worker slot would not serialize on model load. Model load
# is seconds; translation is milliseconds; contention is theoretical, but the
# shape mirrors `world/art/cutout.py`'s session cache deliberately.
_ENGINE_LOCK = threading.Lock()
_ENGINES: dict[str, tuple[object, object]] = {}


class CTranslate2Backend:
    """CPU-pinned, refusal-incapable translator behind the translation seam.

    Contract (design D3/D5/D6/D7, pinned against ctranslate2 4.8.2 and
    sentencepiece 0.2.2):

    - The model layout is verified BEFORE any translation library is imported:
      a missing directory, a missing CTranslate2 model directory, or a missing
      SentencePiece model raises ``art_translate_unavailable`` with no import
      and no outbound request.
    - ``ctranslate2`` and ``sentencepiece`` are imported LAZILY inside the
      first call that reaches engine construction, never at module import, so
      this module and the settings module stay loadable where the optional
      stack is absent.
    - The engine is built at most once per configured model directory per
      process, under the construction-only lock.
    - ``device="cpu"`` is passed explicitly: this process is the Evennia
      server, and a GPU grab would contend with the sd-webui server this
      pipeline feeds. ``ART_TRANSLATE_THREADS`` (non-zero) reaches the
      translator's intra-op thread count; zero leaves the library default.
    - Decoding is fixed-width beam search with sampling disabled.
    - Every escaping failure is bounded: load and construction failures map to
      ``art_translate_unavailable``; encode, translate, and decode failures map
      to ``art_translate_error``. No unbounded exception escapes.
    """

    def translate(self, lines: tuple[str, ...]) -> tuple[str, ...]:
        """Translate every offered line, one output string per input line."""
        model_dir = Path(settings.ART_TRANSLATE_MODEL_DIR)
        self._check_layout(model_dir)
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

        Lock-free on the common path; a miss takes the construction lock and
        re-checks before building (design D5's check, lock, re-check), so two
        threads racing the first call build exactly one engine.
        """
        key = str(model_dir)
        engine = _ENGINES.get(key)
        if engine is not None:
            return engine
        with _ENGINE_LOCK:
            engine = _ENGINES.get(key)
            if engine is None:
                engine = CTranslate2Backend._build_engine(model_dir)
                _ENGINES[key] = engine
            return engine

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