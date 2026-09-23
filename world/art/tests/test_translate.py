"""Pure contracts for the bounded art prompt-translation seam."""

from __future__ import annotations

import ast
import builtins
from collections.abc import Sequence
from contextlib import contextmanager
import importlib.util
import io
import os
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest import mock
from unittest.mock import patch
import zipfile

from django.test import override_settings

from tools.spec_traceability import covers_requirement
from world.art.fake_translate import FakeTranslator
from world.art.translate import (
    TranslateError,
    TranslationCounts,
    resolve_translate_backend,
    translate_description,
)
import world.art.translate as translate
import world.art.translate_ct2 as translate_ct2


class _StubBackend:
    def __init__(self, result=None, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.calls: list[tuple[str, ...]] = []

    def translate(self, lines: tuple[str, ...]):
        self.calls.append(lines)
        if self.error is not None:
            raise self.error
        return self.result


class _ConstructorFails:
    def __init__(self) -> None:
        raise TranslateError("art_translate_unavailable", "engine not installed")


class _BrokenSequence(Sequence[str]):
    def __len__(self) -> int:
        raise RuntimeError("length exploded")

    def __getitem__(self, index: int) -> str:
        raise RuntimeError("iteration exploded")


class _InfiniteIterationSequence(Sequence[str]):
    """Looks sized, but its iterator must never be trusted."""

    def __len__(self) -> int:
        return 1

    def __getitem__(self, index: int) -> str:
        raise RuntimeError("indexed extraction exploded")

    def __iter__(self):
        while True:
            yield "would-never-stop"


class BackendResolutionTests(unittest.TestCase):
    @covers_requirement(
        "art-prompt-translation::the-translation-backend-is-an-injectable-seam-whose-output-is-validated"
    )
    def test_resolution_failures_all_raise_art_translate_unavailable(self):
        paths = (
            "not-a-dotted-path",
            "world.art.no_such_module.Backend",
            "world.art.fake_translate.NoSuchBackend",
            "world.art.tests.test_translate._ConstructorFails",
        )
        for path in paths:
            with self.subTest(path=path):
                with override_settings(ART_TRANSLATE_BACKEND=path):
                    with self.assertRaises(TranslateError) as caught:
                        resolve_translate_backend()
                self.assertEqual(caught.exception.code, "art_translate_unavailable")

    @covers_requirement(
        "art-prompt-translation::the-translation-backend-is-an-injectable-seam-whose-output-is-validated"
    )
    def test_non_string_setting_values_raise_art_translate_unavailable(self):
        for value in (None, 7):
            with self.subTest(value=value):
                with override_settings(ART_TRANSLATE_BACKEND=value):
                    with self.assertRaises(TranslateError) as caught:
                        resolve_translate_backend()
                self.assertEqual(caught.exception.code, "art_translate_unavailable")


class TranslationBoundaryTests(unittest.TestCase):
    def _translate_with(self, backend: _StubBackend, text: str = "漢字"):
        with patch.object(translate, "resolve_translate_backend", return_value=backend):
            return translate_description(text)

    @covers_requirement(
        "art-prompt-translation::the-translation-backend-is-an-injectable-seam-whose-output-is-validated"
    )
    def test_an_arbitrary_backend_exception_becomes_art_translate_error(self):
        with self.assertRaises(TranslateError) as caught:
            self._translate_with(_StubBackend(error=RuntimeError("engine exploded")))
        self.assertEqual(caught.exception.code, "art_translate_error")
        self.assertIsInstance(caught.exception.__cause__, RuntimeError)

    @covers_requirement(
        "art-prompt-translation::the-translation-backend-is-an-injectable-seam-whose-output-is-validated"
    )
    def test_scripted_bounded_backend_error_remains_art_translate_error(self):
        with self.assertRaises(TranslateError) as caught:
            self._translate_with(
                _StubBackend(error=TranslateError("art_translate_error", "scripted"))
            )
        self.assertEqual(caught.exception.code, "art_translate_error")

    @covers_requirement(
        "art-prompt-translation::the-translation-backend-is-an-injectable-seam-whose-output-is-validated"
    )
    def test_unknown_backend_error_code_is_normalized(self):
        with self.assertRaises(TranslateError) as caught:
            self._translate_with(_StubBackend(error=TranslateError("unexpected", "bad")))
        self.assertEqual(caught.exception.code, "art_translate_error")

    @covers_requirement(
        "art-prompt-translation::the-translation-backend-is-an-injectable-seam-whose-output-is-validated"
    )
    def test_invalid_backend_results_are_bounded(self):
        cases = {
            "non-sequence": "not lines",
            "short": (),
            "long": ("one", "two"),
            "non-string": (1,),
            "pathological-sequence": _BrokenSequence(),
            "infinite-iterator": _InfiniteIterationSequence(),
        }
        for name, result in cases.items():
            with self.subTest(result=name):
                with self.assertRaises(TranslateError) as caught:
                    self._translate_with(_StubBackend(result=result))
                self.assertEqual(caught.exception.code, "art_translate_error")

    @covers_requirement(
        "art-prompt-translation::a-per-line-language-gate-skips-text-that-needs-no-translation"
    )
    def test_all_latin_short_circuits_before_backend_resolution(self):
        text = "prompt tags\nblue hair"
        with patch.object(
            translate,
            "resolve_translate_backend",
            side_effect=AssertionError("must not resolve"),
        ):
            actual, counts = translate_description(text)
        self.assertEqual(actual, text)
        self.assertEqual(counts, TranslationCounts(0, 0, 0))

    @covers_requirement(
        "art-prompt-translation::a-per-line-language-gate-skips-text-that-needs-no-translation"
    )
    @covers_requirement(
        "art-prompt-translation::the-translation-backend-is-an-injectable-seam-whose-output-is-validated"
    )
    def test_mixed_lines_are_batched_reassembled_and_count_untranslated(self):
        backend = _StubBackend(result=("translated", "專名"))
        text = "Latin\n漢字第一行\nuntouched\n漢字第二行"
        actual, counts = self._translate_with(backend, text)
        self.assertEqual(backend.calls, [("漢字第一行", "漢字第二行")])
        self.assertEqual(actual, "Latin\ntranslated\nuntouched\n專名")
        self.assertEqual(counts, TranslationCounts(4, 2, 1))

    @covers_requirement(
        "art-prompt-translation::a-per-line-language-gate-skips-text-that-needs-no-translation"
    )
    def test_empty_and_whitespace_only_descriptions_are_noops(self):
        for text in ("", " \t "):
            with self.subTest(text=repr(text)):
                with patch.object(
                    translate,
                    "resolve_translate_backend",
                    side_effect=AssertionError("must not resolve"),
                ):
                    actual, counts = translate_description(text)
                self.assertEqual(actual, text)
                self.assertEqual(counts, TranslationCounts(0, 0, 0))

    @covers_requirement(
        "art-prompt-translation::the-translation-backend-is-an-injectable-seam-whose-output-is-validated"
    )
    def test_translate_module_has_no_observability_dependency(self):
        source = Path(translate.__file__).read_text(encoding="utf-8")
        self.assertNotIn("world.observability", source)


class FakeTranslatorTests(unittest.TestCase):
    @covers_requirement(
        "art-prompt-translation::the-translation-backend-is-injectable-and-tests-never-load-a-translation-library"
    )
    def test_fake_records_calls_changes_each_line_and_replays_failures(self):
        fake = FakeTranslator()
        self.assertEqual(
            fake.translate(("漢字",)),
            ("[fake-translation]",),
        )
        self.assertEqual(fake.calls, [("漢字",)])
        fake.add_failure(
            lambda lines: lines == ("失敗",),
            TranslateError("art_translate_error", "scripted"),
        )
        with self.assertRaises(TranslateError) as caught:
            fake.translate(("失敗",))
        self.assertEqual(caught.exception.code, "art_translate_error")


class _ScriptedStack:
    """Synthetic ``ctranslate2``/``sentencepiece`` stack recording every call.

    Installed into ``sys.modules`` under the REAL package names so the
    backend's lazy ``import ctranslate2`` / ``import sentencepiece`` bind to
    these fakes — the real libraries are never imported by a test (the
    ``_CT2BackendCase`` base pops them for the duration and restores them
    afterwards, mirroring ``test_cutout.py``'s laziness technique).
    """

    def __init__(self):
        self.processor_calls: list[dict] = []
        self.translator_calls: list[tuple[str, dict]] = []
        self.encode_calls: list[tuple[str, str]] = []
        self.batch_calls: list[tuple[list, dict]] = []
        self.processor_error: Exception | None = None
        self.translator_error: Exception | None = None
        self.translator_kwargs_error: Exception | None = None
        self.encode_error: Exception | None = None
        self.batch_error: Exception | None = None
        # SentencePiece surface markers: the decoder joins pieces and maps
        # U+2581 back to spaces, so these render as "out0 out1".
        self.hypothesis_pieces: list[str] = ["\u2581out0", "\u2581out1"]
        self.hold_construction: threading.Event | None = None


class _CT2BackendCase(unittest.TestCase):
    """Shared isolation for the CTranslate2Backend tests (libraries fake)."""

    def setUp(self):
        super().setUp()
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.model_dir = Path(self.tempdir.name) / "model-root"
        # The engine cache is keyed by directory only — valid under
        # restart-bound production settings; tests must clear it so overrides
        # never reuse an engine built for a previous configuration.
        self._cache_snapshot = dict(translate_ct2._ENGINES)
        translate_ct2._ENGINES.clear()
        # The per-process download latch is module-global by design; snapshot
        # and clear it so download-track tests never leak a latched module
        # into later tests, and restore it afterwards.
        self._latch_snapshot = translate_ct2._DOWNLOAD_LATCHED
        translate_ct2._DOWNLOAD_LATCHED = False
        # Pop any cached real translation libraries so every test starts
        # library-free and the fakes below can never shadow a real import.
        self._modules_snapshot = {
            name: module
            for name, module in sys.modules.items()
            if name == "ctranslate2"
            or name.startswith("ctranslate2.")
            or name == "sentencepiece"
            or name.startswith("sentencepiece.")
        }
        for name in self._modules_snapshot:
            sys.modules.pop(name, None)
        self.addCleanup(self._restore)

    def _restore(self):
        translate_ct2._ENGINES.clear()
        translate_ct2._ENGINES.update(self._cache_snapshot)
        translate_ct2._DOWNLOAD_LATCHED = self._latch_snapshot
        for name in list(sys.modules):
            if (
                name == "ctranslate2"
                or name.startswith("ctranslate2.")
                or name == "sentencepiece"
                or name.startswith("sentencepiece.")
            ):
                sys.modules.pop(name, None)
        sys.modules.update(self._modules_snapshot)

    def _backend(self, **overrides):
        kwargs = {
            "ART_TRANSLATE_MODEL_DIR": str(self.model_dir),
            "ART_TRANSLATE_THREADS": 0,
        }
        kwargs.update(overrides)
        settings_override = override_settings(**kwargs)
        settings_override.enable()
        self.addCleanup(settings_override.disable)
        return translate_ct2.CTranslate2Backend()

    def _seed(self, *, model_files=("config.json", "model.bin"), sp=True):
        """Create the seeded layout the fetch script produces."""
        (self.model_dir / "model").mkdir(parents=True, exist_ok=True)
        for name in model_files:
            (self.model_dir / "model" / name).write_text(
                "{}" if name.endswith(".json") else "weights"
            )
        if sp:
            (self.model_dir / "sentencepiece.model").write_bytes(b"sp-model")

    def _install_stack(self, stack: _ScriptedStack) -> _ScriptedStack:
        """Install fake libraries; the backend sees them as the real names."""
        ct2 = types.ModuleType("ctranslate2")
        sp = types.ModuleType("sentencepiece")

        class _Processor:
            def __init__(self, **kwargs):
                stack.processor_calls.append(kwargs)
                if stack.processor_error is not None:
                    raise stack.processor_error

            def encode(self, line, out_type=None):
                stack.encode_calls.append((line, out_type))
                if stack.encode_error is not None:
                    raise stack.encode_error
                return ["in0", "in1"]

        class _Translator:
            def __init__(self, model_path, **kwargs):
                stack.translator_calls.append((model_path, kwargs))
                if stack.translator_kwargs_error is not None:
                    raise stack.translator_kwargs_error
                if stack.translator_error is not None:
                    raise stack.translator_error
                if stack.hold_construction is not None:
                    stack.hold_construction.wait(5)

            def translate_batch(self, source, **kwargs):
                stack.batch_calls.append((source, kwargs))
                if stack.batch_error is not None:
                    raise stack.batch_error
                return [_Result() for _ in source]

        class _Result:
            def __init__(self):
                self.hypotheses = [list(stack.hypothesis_pieces)]

        ct2.Translator = _Translator
        sp.SentencePieceProcessor = _Processor
        sys.modules["ctranslate2"] = ct2
        sys.modules["sentencepiece"] = sp
        return stack

    @contextmanager
    def _raising_import_for_optional_stack(self):
        """Make the lazy `import ctranslate2` / `import sentencepiece` fail."""
        real_import = builtins.__import__

        def _raising_import(name, *args, **kwargs):
            if (
                name == "ctranslate2"
                or name.startswith("ctranslate2.")
                or name == "sentencepiece"
                or name.startswith("sentencepiece.")
            ):
                raise ImportError("translation stack is absent")
            return real_import(name, *args, **kwargs)

        with mock.patch("builtins.__import__", side_effect=_raising_import):
            yield

    @contextmanager
    def _no_network(self):
        """Any socket-opening during the block is an immediate test failure."""
        with mock.patch(
            "socket.socket", side_effect=AssertionError("no network access")
        ):
            yield


_PKG = "translate-zh_en-1_9"


def _package_members() -> dict[str, bytes]:
    """The five-entry Argos package layout the download verifies and lands."""
    return {
        f"{_PKG}/model/config.json": b"{}",
        f"{_PKG}/model/model.bin": b"weights",
        f"{_PKG}/model/shared_vocabulary.json": b"{}",
        f"{_PKG}/sentencepiece.model": b"sp-model",
        f"{_PKG}/README.md": b"CC-BY 4.0 provenance",
    }


def _zip_bytes(members: dict[str, bytes]) -> bytes:
    """Build a zip archive from member name -> content bytes."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in members.items():
            archive.writestr(name, data)
    return buffer.getvalue()


def _package_bytes() -> bytes:
    """The default (valid) package body used by download-test stubs."""
    return _zip_bytes(_package_members())


class _FakeResponse:
    """Minimal ``urlopen`` response double: headers.get + streaming read."""

    def __init__(
        self,
        body: bytes,
        *,
        content_length: int | None = None,
        read_error: Exception | None = None,
    ):
        self._body = body
        self._offset = 0
        self._read_error = read_error
        headers: dict[str, str] = {}
        if content_length is not None:
            headers["Content-Length"] = str(content_length)
        self.headers = headers

    def read(self, size: int = -1):
        if self._read_error is not None:
            raise self._read_error
        if size is None or size < 0:
            chunk = self._body[self._offset :]
        else:
            chunk = self._body[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


class CTranslate2BackendLayoutTests(_CT2BackendCase):
    """The pre-import layout check (6.1): unseeded -> unavailable, no import."""

    @covers_requirement(
        "art-prompt-translation::the-model-artifact-is-operator-seeded-and-its-absence-is-bounded"
    )
    def test_missing_directory_raises_unavailable_without_import_or_network(self):
        backend = self._backend()
        with self._raising_import_for_optional_stack():
            with self._no_network():
                with self.assertRaises(TranslateError) as caught:
                    backend.translate(("漢字",))
        self.assertEqual(caught.exception.code, "art_translate_unavailable")
        self.assertNotIn("ctranslate2", sys.modules)
        self.assertNotIn("sentencepiece", sys.modules)

    @covers_requirement(
        "art-prompt-translation::the-model-artifact-is-operator-seeded-and-its-absence-is-bounded"
    )
    def test_missing_ct2_model_raises_unavailable_without_import(self):
        for model_files in ((), ("config.json",), ("model.bin",)):
            with self.subTest(model_files=model_files):
                shutil.rmtree(self.model_dir, ignore_errors=True)
                self._seed(model_files=model_files)
                backend = self._backend()
                with self._raising_import_for_optional_stack():
                    with self._no_network():
                        with self.assertRaises(TranslateError) as caught:
                            backend.translate(("漢字",))
                self.assertEqual(
                    caught.exception.code, "art_translate_unavailable"
                )
                self.assertNotIn("ctranslate2", sys.modules)
                self.assertNotIn("sentencepiece", sys.modules)

    @covers_requirement(
        "art-prompt-translation::the-model-artifact-is-operator-seeded-and-its-absence-is-bounded"
    )
    def test_missing_sentencepiece_model_raises_unavailable_without_import(self):
        self._seed(sp=False)
        backend = self._backend()
        with self._raising_import_for_optional_stack():
            with self._no_network():
                with self.assertRaises(TranslateError) as caught:
                    backend.translate(("漢字",))
        self.assertEqual(caught.exception.code, "art_translate_unavailable")
        self.assertNotIn("ctranslate2", sys.modules)
        self.assertNotIn("sentencepiece", sys.modules)

    @covers_requirement(
        "art-prompt-translation::the-model-artifact-is-operator-seeded-and-its-absence-is-bounded"
    )
    @unittest.skipIf(os.geteuid() == 0, "permission bits do not bind root")
    def test_an_unreadable_component_raises_unavailable_without_import(self):
        self._seed()
        (self.model_dir / "model" / "model.bin").chmod(0)
        backend = self._backend()
        with self._raising_import_for_optional_stack():
            with self._no_network():
                with self.assertRaises(TranslateError) as caught:
                    backend.translate(("漢字",))
        self.assertEqual(caught.exception.code, "art_translate_unavailable")
        self.assertNotIn("ctranslate2", sys.modules)
        self.assertNotIn("sentencepiece", sys.modules)
        (self.model_dir / "model" / "model.bin").chmod(0o644)

    @covers_requirement(
        "art-prompt-translation::the-model-artifact-is-operator-seeded-and-its-absence-is-bounded"
    )
    def test_a_complete_layout_passes_the_pre_import_check(self):
        self._seed()
        stack = self._install_stack(_ScriptedStack())
        backend = self._backend()
        with self._no_network():
            backend.translate(("漢字",))
        self.assertEqual(
            stack.translator_calls,
            [(f"{self.model_dir}/model", {"device": "cpu"})],
        )
        self.assertEqual(
            stack.processor_calls,
            [{"model_file": f"{self.model_dir}/sentencepiece.model"}],
        )


class CTranslate2BackendFailureTests(_CT2BackendCase):
    """Bounded failure mapping (6.2): load/ctor -> unavailable, calls -> error."""

    @covers_requirement(
        "art-prompt-translation::the-model-artifact-is-operator-seeded-and-its-absence-is-bounded"
    )
    def test_a_processor_load_failure_is_art_translate_unavailable(self):
        self._seed()
        stack = self._install_stack(_ScriptedStack())
        stack.processor_error = RuntimeError("sp broken")
        backend = self._backend()
        with self.assertRaises(TranslateError) as caught:
            backend.translate(("漢字",))
        self.assertEqual(caught.exception.code, "art_translate_unavailable")
        self.assertIsInstance(caught.exception.__cause__, RuntimeError)

    @covers_requirement(
        "art-prompt-translation::the-model-artifact-is-operator-seeded-and-its-absence-is-bounded"
    )
    def test_a_translator_constructor_failure_is_art_translate_unavailable(self):
        self._seed()
        stack = self._install_stack(_ScriptedStack())
        stack.translator_kwargs_error = ValueError("bad model dir")
        backend = self._backend()
        with self.assertRaises(TranslateError) as caught:
            backend.translate(("漢字",))
        self.assertEqual(caught.exception.code, "art_translate_unavailable")

    @covers_requirement(
        "art-prompt-translation::the-model-artifact-is-operator-seeded-and-its-absence-is-bounded"
    )
    def test_an_encode_failure_is_art_translate_error(self):
        self._seed()
        stack = self._install_stack(_ScriptedStack())
        stack.encode_error = RuntimeError("sp encode exploded")
        backend = self._backend()
        with self.assertRaises(TranslateError) as caught:
            backend.translate(("漢字",))
        self.assertEqual(caught.exception.code, "art_translate_error")
        self.assertIsInstance(caught.exception.__cause__, RuntimeError)

    @covers_requirement(
        "art-prompt-translation::the-model-artifact-is-operator-seeded-and-its-absence-is-bounded"
    )
    def test_a_translate_failure_is_art_translate_error(self):
        self._seed()
        stack = self._install_stack(_ScriptedStack())
        stack.batch_error = RuntimeError("inference exploded")
        backend = self._backend()
        with self.assertRaises(TranslateError) as caught:
            backend.translate(("漢字",))
        self.assertEqual(caught.exception.code, "art_translate_error")

    @covers_requirement(
        "art-prompt-translation::the-model-artifact-is-operator-seeded-and-its-absence-is-bounded"
    )
    def test_a_decode_failure_is_art_translate_error(self):
        self._seed()
        stack = self._install_stack(_ScriptedStack())
        stack.hypothesis_pieces = ["ok", 7]  # non-string piece breaks _detokenize
        backend = self._backend()
        with self.assertRaises(TranslateError) as caught:
            backend.translate(("漢字",))
        self.assertEqual(caught.exception.code, "art_translate_error")

    @covers_requirement(
        "art-prompt-translation::the-model-artifact-is-operator-seeded-and-its-absence-is-bounded"
    )
    def test_an_arbitrary_exception_is_bounded_not_escaping(self):
        self._seed()
        stack = self._install_stack(_ScriptedStack())
        stack.batch_error = RuntimeError("unexpected")
        backend = self._backend()
        with self.assertRaises(TranslateError) as caught:
            backend.translate(("漢字",))
        self.assertEqual(caught.exception.code, "art_translate_error")


class CTranslate2BackendEngineTests(_CT2BackendCase):
    """One engine per directory, CPU-pinned, threads cap (6.3)."""

    @covers_requirement(
        "art-prompt-translation::the-translator-is-built-once-per-process-and-decodes-deterministically-on-the-cpu"
    )
    def test_three_consecutive_calls_build_exactly_one_cpu_engine(self):
        self._seed()
        stack = self._install_stack(_ScriptedStack())
        backend = self._backend()
        first = backend.translate(("漢字一",))
        second = backend.translate(("漢字二",))
        third = backend.translate(("漢字三",))
        self.assertEqual(first, ("out0 out1",))
        self.assertEqual(second, first)
        self.assertEqual(third, first)
        self.assertEqual(len(stack.translator_calls), 1, "one engine per dir")
        self.assertEqual(len(stack.processor_calls), 1)
        model_path, kwargs = stack.translator_calls[0]
        self.assertEqual(model_path, f"{self.model_dir}/model")
        self.assertEqual(kwargs, {"device": "cpu"})
        self.assertEqual(
            stack.processor_calls[0],
            {"model_file": f"{self.model_dir}/sentencepiece.model"},
        )
        self.assertIn(
            f"{self.model_dir}",
            translate_ct2._ENGINES,
            "the built engine is cached under its directory key",
        )

    @covers_requirement(
        "art-prompt-translation::the-translator-is-built-once-per-process-and-decodes-deterministically-on-the-cpu"
    )
    def test_a_non_zero_thread_cap_reaches_the_intra_op_count(self):
        self._seed()
        stack = self._install_stack(_ScriptedStack())
        backend = self._backend(ART_TRANSLATE_THREADS=4)
        backend.translate(("漢字",))
        self.assertEqual(
            stack.translator_calls[0][1],
            {"device": "cpu", "intra_threads": 4},
        )

    @covers_requirement(
        "art-prompt-translation::the-translator-is-built-once-per-process-and-decodes-deterministically-on-the-cpu"
    )
    def test_a_zero_thread_cap_leaves_the_library_default(self):
        self._seed()
        stack = self._install_stack(_ScriptedStack())
        backend = self._backend(ART_TRANSLATE_THREADS=0)
        backend.translate(("漢字",))
        self.assertEqual(stack.translator_calls[0][1], {"device": "cpu"})

    @covers_requirement(
        "art-prompt-translation::the-translator-is-built-once-per-process-and-decodes-deterministically-on-the-cpu"
    )
    def test_success_returns_an_ordered_tuple_one_string_per_input_line(self):
        self._seed()
        stack = self._install_stack(_ScriptedStack())
        backend = self._backend()
        with self._no_network():
            result = backend.translate(("第一行", "第二行"))
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        self.assertEqual(result, ("out0 out1", "out0 out1"))
        self.assertEqual(
            stack.encode_calls, [("第一行", str), ("第二行", str)]
        )
        self.assertEqual(len(stack.batch_calls), 1)
        source, kwargs = stack.batch_calls[0]
        self.assertEqual(source, [["in0", "in1"], ["in0", "in1"]])
        self.assertEqual(kwargs, {"beam_size": 5})

    @covers_requirement(
        "art-prompt-translation::the-translator-is-built-once-per-process-and-decodes-deterministically-on-the-cpu"
    )
    def test_inference_never_acquires_the_construction_lock(self):
        # design D5: the lock guards CONSTRUCTION only. Holding the lock
        # ourselves while a translate completes proves the call never takes
        # it: a lock-taking translate would deadlock against the held lock,
        # and the join timeout turns that deadlock into a clean failure.
        self._seed()
        self._install_stack(_ScriptedStack())
        backend = self._backend()
        backend.translate(("建好引擎",))
        done: list = []

        def locked_translate():
            try:
                done.append(backend.translate(("鎖下推論",)))
            except Exception as error:  # noqa: BLE001 - captured for assertion
                done.append(error)

        try:
            translate_ct2._ENGINE_LOCK.acquire()
            thread = threading.Thread(target=locked_translate)
            thread.start()
            thread.join(timeout=3)
            self.assertFalse(
                thread.is_alive(),
                "translate must never take the construction lock (deadlock)",
            )
        finally:
            translate_ct2._ENGINE_LOCK.release()
        self.assertEqual(done, [("out0 out1",)])

    @covers_requirement(
        "art-prompt-translation::the-translator-is-built-once-per-process-and-decodes-deterministically-on-the-cpu"
    )
    def test_concurrent_first_calls_build_exactly_one_engine(self):
        self._seed()
        stack = self._install_stack(_ScriptedStack())
        stack.hold_construction = threading.Event()
        backend = self._backend()
        results: list = []

        def worker():
            try:
                results.append(backend.translate(("並發",)))
            except Exception as error:  # noqa: BLE001 - captured for assertion
                results.append(f"{type(error).__name__}: {error}")

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        # Wait until the first construction is blocked in progress, then give
        # the second thread time to miss the lock-free read and block on the
        # construction lock.
        deadline = 0
        while not stack.translator_calls and deadline < 100:
            time.sleep(0.01)
            deadline += 1
        time.sleep(0.1)
        if stack.translator_calls:
            # While the first construction is still blocked, the second thread
            # cannot have started a duplicate build (the lock is held).
            self.assertEqual(len(stack.translator_calls), 1, "no duplicate build")
        stack.hold_construction.set()
        for thread in threads:
            thread.join(timeout=5)
        self.assertEqual(len(stack.translator_calls), 1)
        self.assertEqual(len(results), 2)
        self.assertEqual(sorted(results), [("out0 out1",), ("out0 out1",)])


class CTranslate2BackendLazinessTests(_CT2BackendCase):
    """The optional stack is lazy: import-time absence and broken first use."""

    @covers_requirement(
        "art-prompt-translation::the-translator-is-built-once-per-process-and-decodes-deterministically-on-the-cpu"
    )
    def test_importing_translate_ct2_loads_no_translation_library(self):
        # Order-independent proof (a bare "not in sys.modules" would false-fail
        # after another test imported the libraries, and a reload of the live
        # module would rebind its classes under every other test): pop any
        # cached ctranslate2*/sentencepiece* modules, execute the module body
        # FRESH under a probe name, and assert they stay absent.
        probe_name = "world.art.translate_ct2._laziness_probe"
        saved = {
            name: module
            for name, module in sys.modules.items()
            if name.startswith(("ctranslate2", "sentencepiece"))
        }
        try:
            for name in saved:
                sys.modules.pop(name, None)
            spec = importlib.util.spec_from_file_location(
                probe_name, Path(translate_ct2.__file__)
            )
            probe = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(probe)
            self.assertTrue(hasattr(probe, "CTranslate2Backend"))
            self.assertNotIn("ctranslate2", sys.modules)
            self.assertNotIn("sentencepiece", sys.modules)
        finally:
            sys.modules.update(saved)

    @covers_requirement(
        "art-prompt-translation::the-model-artifact-is-operator-seeded-and-its-absence-is-bounded"
    )
    def test_a_broken_first_use_raises_art_translate_unavailable(self):
        self._seed()
        backend = self._backend()
        with self._raising_import_for_optional_stack():
            with self.assertRaises(TranslateError) as caught:
                backend.translate(("漢字",))
        self.assertEqual(caught.exception.code, "art_translate_unavailable")
        self.assertIsInstance(caught.exception.__cause__, ImportError)


class CTranslate2BackendDownloadTests(_CT2BackendCase):
    """The dual-track first-use fetch (add-translate-model-download-policy).

    The fetch stub stands in for ``world.art.translate_ct2.urlopen`` (the
    module's single network entry point); every test stays socket-free.
    """

    def _fetch_patch(self, body=None, *, content_length=None, error=None):
        if error is not None:
            return patch("world.art.translate_ct2.urlopen", side_effect=error)
        response = _FakeResponse(
            body if body is not None else _package_bytes(),
            content_length=content_length,
        )
        return patch("world.art.translate_ct2.urlopen", return_value=response)

    def test_a_complete_layout_never_fetches_on_the_download_track(self):
        # Scenario: a complete layout never triggers a fetch — even with the
        # flag explicitly on, the check passes and zero network is attempted.
        self._seed()
        self._install_stack(_ScriptedStack())
        backend = self._backend(ART_TRANSLATE_DOWNLOAD_ENABLED=True)
        with self._fetch_patch() as fetch:
            with self._no_network():
                result = backend.translate(("漢字",))
        self.assertEqual(result, ("out0 out1",))
        fetch.assert_not_called()

    def test_missing_layout_with_downloads_enabled_fetches_unpacks_and_translates(self):
        # Scenario: an unseeded volume with downloads enabled fetches once —
        # the same call populates, verifies, unpacks, emits exactly one
        # download-done info event, and translates with the built engine.
        stack = self._install_stack(_ScriptedStack())
        backend = self._backend(ART_TRANSLATE_DOWNLOAD_ENABLED=True)
        with self._fetch_patch() as fetch:
            with patch("world.art.translate_ct2.log_info") as info:
                result = backend.translate(("漢字",))
        self.assertEqual(result, ("out0 out1",))
        fetch.assert_called_once()
        for relative in (
            "model/config.json",
            "model/model.bin",
            "model/shared_vocabulary.json",
            "sentencepiece.model",
            "README.md",
        ):
            self.assertTrue(
                (self.model_dir / relative).is_file(), msg=relative
            )
        # The same call then built the engine from the landed layout.
        self.assertEqual(
            stack.translator_calls,
            [(f"{self.model_dir}/model", {"device": "cpu"})],
        )
        self.assertEqual(
            stack.processor_calls,
            [{"model_file": f"{self.model_dir}/sentencepiece.model"}],
        )
        info.assert_called_once()
        args, kwargs = info.call_args
        self.assertEqual(args, ("art_translate_model_download_done",))
        self.assertEqual(kwargs["context"]["url"], translate_ct2._MODEL_URL)
        self.assertEqual(kwargs["context"]["bytes"], len(_package_bytes()))
        self.assertIsInstance(kwargs["context"]["duration_ms"], int)

    def test_fetch_failure_is_bounded_emits_one_warn_and_latches(self):
        # Scenario: a fetch failure degrades and latches — bounded
        # art_translate_unavailable, no library import, exactly one
        # download-failed warn, and every later call fails immediately without
        # a second network attempt.
        backend = self._backend(ART_TRANSLATE_DOWNLOAD_ENABLED=True)
        error = OSError("connection refused")
        with self._fetch_patch(error=error) as fetch:
            with patch("world.art.translate_ct2.log_warn") as warn:
                with self.assertRaises(TranslateError) as caught:
                    backend.translate(("漢字",))
        self.assertEqual(caught.exception.code, "art_translate_unavailable")
        self.assertNotIn("ctranslate2", sys.modules)
        self.assertNotIn("sentencepiece", sys.modules)
        warn.assert_called_once()
        args, kwargs = warn.call_args
        self.assertEqual(args, ("art_translate_model_download_failed",))
        self.assertEqual(kwargs["context"]["url"], translate_ct2._MODEL_URL)
        self.assertIn("reason", kwargs["context"])
        self.assertIs(kwargs["exc"], error)
        fetch.assert_called_once()
        # Second attempt in the same process: latched, zero new network.
        with self._fetch_patch(error=error) as later:
            with patch("world.art.translate_ct2.log_warn") as later_warn:
                with self.assertRaises(TranslateError) as second:
                    backend.translate(("漢字",))
        self.assertEqual(second.exception.code, "art_translate_unavailable")
        later.assert_not_called()
        later_warn.assert_not_called()

    def test_mkdir_failure_is_bounded_emits_one_warn_and_latches(self):
        # A write failure at directory creation (EROFS/EACCES/ENOSPC on a
        # read-only or full volume) must follow the same bounded path as any
        # other download failure: art_translate_unavailable, exactly one
        # download-failed warn, and the per-process latch so later calls skip
        # the attempt (delta spec: "including OSError/ENOSPC on a full
        # volume").
        backend = self._backend(ART_TRANSLATE_DOWNLOAD_ENABLED=True)
        with mock.patch.object(
            Path, "mkdir", side_effect=OSError("read-only volume")
        ):
            with patch("world.art.translate_ct2.log_warn") as warn:
                with self.assertRaises(TranslateError) as caught:
                    backend.translate(("漢字",))
        self.assertEqual(caught.exception.code, "art_translate_unavailable")
        warn.assert_called_once()
        args, kwargs = warn.call_args
        self.assertEqual(args, ("art_translate_model_download_failed",))
        self.assertIsInstance(kwargs["exc"], OSError)
        with patch("world.art.translate_ct2.log_warn") as later_warn:
            with self.assertRaises(TranslateError) as second:
                backend.translate(("漢字",))
        self.assertEqual(second.exception.code, "art_translate_unavailable")
        later_warn.assert_not_called()

    def test_an_oversize_content_length_is_rejected_before_reading(self):
        backend = self._backend(ART_TRANSLATE_DOWNLOAD_ENABLED=True)
        with mock.patch.object(translate_ct2, "_MAX_MODEL_BYTES", 1024):
            response = _FakeResponse(
                b"x" * 2048,
                content_length=2048,
                read_error=AssertionError("body must never be read"),
            )
            with patch(
                "world.art.translate_ct2.urlopen", return_value=response
            ) as fetch:
                with self.assertRaises(TranslateError) as caught:
                    backend.translate(("漢字",))
        self.assertEqual(caught.exception.code, "art_translate_unavailable")
        fetch.assert_called_once()

    def test_a_body_over_the_cap_aborts_while_streaming(self):
        backend = self._backend(ART_TRANSLATE_DOWNLOAD_ENABLED=True)
        with mock.patch.object(translate_ct2, "_MAX_MODEL_BYTES", 1024):
            with self._fetch_patch(body=b"x" * 2048) as fetch:
                with self.assertRaises(TranslateError) as caught:
                    backend.translate(("漢字",))
        self.assertEqual(caught.exception.code, "art_translate_unavailable")
        fetch.assert_called_once()

    def test_a_bad_zip_fails_bounded_and_lands_nothing(self):
        backend = self._backend(ART_TRANSLATE_DOWNLOAD_ENABLED=True)
        with self._fetch_patch(body=b"definitely not a zip archive"):
            with patch("world.art.translate_ct2.log_warn") as warn:
                with self.assertRaises(TranslateError) as caught:
                    backend.translate(("漢字",))
        self.assertEqual(caught.exception.code, "art_translate_unavailable")
        warn.assert_called_once()
        self.assertEqual(list(self.model_dir.iterdir()), [])

    def test_a_package_missing_a_required_entry_fails_bounded(self):
        members = _package_members()
        del members[f"{_PKG}/README.md"]
        backend = self._backend(ART_TRANSLATE_DOWNLOAD_ENABLED=True)
        with self._fetch_patch(body=_zip_bytes(members)):
            with self.assertRaises(TranslateError) as caught:
                backend.translate(("漢字",))
        self.assertEqual(caught.exception.code, "art_translate_unavailable")
        self.assertFalse((self.model_dir / "README.md").exists())

    def test_an_unsafe_or_out_of_package_member_fails_bounded(self):
        for name in (f"{_PKG}/../../evil", "evil.txt", "/etc/passwd"):
            with self.subTest(member=name):
                # The latch is per-process, not per-model-dir; each member
                # shape must be checked by the real verification code, so
                # reset it before every iteration (the rmtree below would
                # otherwise let a later member hide behind an earlier latch).
                translate_ct2._DOWNLOAD_LATCHED = False
                shutil.rmtree(self.model_dir, ignore_errors=True)
                members = _package_members()
                members[name] = b"x"
                backend = self._backend(ART_TRANSLATE_DOWNLOAD_ENABLED=True)
                with self._fetch_patch(body=_zip_bytes(members)):
                    with self.assertRaises(TranslateError) as caught:
                        backend.translate(("漢字",))
                self.assertEqual(
                    caught.exception.code, "art_translate_unavailable"
                )

    def test_a_landed_layout_is_never_refetched_after_a_restart(self):
        # Task 6.2 phase pair in one process: land the layout with a fetch,
        # then simulate a restart (latch AND engine cache reset) and observe
        # zero further fetches — proving "complete layout => no fetch", not a
        # latched module.
        self._install_stack(_ScriptedStack())
        backend = self._backend(ART_TRANSLATE_DOWNLOAD_ENABLED=True)
        with self._fetch_patch() as fetch:
            backend.translate(("第一階段",))
        self.assertEqual(fetch.call_count, 1)
        translate_ct2._DOWNLOAD_LATCHED = False
        translate_ct2._ENGINES.clear()
        with self._fetch_patch(error=AssertionError("must not fetch")) as later:
            result = backend.translate(("第二階段",))
        self.assertEqual(result, ("out0 out1",))
        later.assert_not_called()


class CTranslate2BackendAirGappedTests(_CT2BackendCase):
    """The flag-false track reproduces today's seed-only behavior (3.2)."""

    @covers_requirement(
        "art-prompt-translation::the-model-artifact-is-operator-seeded-and-its-absence-is-bounded"
    )
    def test_download_disabled_against_absent_dir_is_todays_exact_behavior(self):
        # Scenario: an unseeded model directory degrades without a fetch —
        # immediate art_translate_unavailable, no library import, zero network
        # attempts (the fetch call site does not exist in this branch).
        backend = self._backend(ART_TRANSLATE_DOWNLOAD_ENABLED=False)
        with self._raising_import_for_optional_stack():
            with self._no_network():
                with patch("world.art.translate_ct2.urlopen") as fetch:
                    with self.assertRaises(TranslateError) as caught:
                        backend.translate(("漢字",))
        self.assertEqual(caught.exception.code, "art_translate_unavailable")
        self.assertNotIn("ctranslate2", sys.modules)
        self.assertNotIn("sentencepiece", sys.modules)
        fetch.assert_not_called()


class CTranslate2BackendReachabilityTests(_CT2BackendCase):
    """No generative layer or general-purpose transport is reachable (6.5).

    Re-scoped by add-translate-model-download-policy: the ban covers
    ``world.ai``/``requests``/``http`` imports and ``LLM_*`` reads; the pinned
    ``urllib.request`` fetch and the ``world.observability`` lifecycle events
    are permitted for the acquisition path.
    """

    _BANNED_IMPORT_PREFIXES = (
        "world.ai",
        "http",
        "requests",
    )
    _BANNED_SUBSTRINGS = (
        "LLM_",
        "requests",
    )

    @covers_requirement(
        "art-prompt-translation::the-shipped-backend-is-a-neural-machine-translator-never-a-chat-model"
    )
    def test_the_module_imports_no_generative_or_network_transport(self):
        source = Path(translate_ct2.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        for name in imported:
            self.assertFalse(
                any(
                    name == banned or name.startswith(banned + ".")
                    for banned in self._BANNED_IMPORT_PREFIXES
                ),
                msg=f"module imports forbidden transport {name}",
            )
        for substring in self._BANNED_SUBSTRINGS:
            self.assertNotIn(substring, source)

    @covers_requirement(
        "art-prompt-translation::the-shipped-backend-is-a-neural-machine-translator-never-a-chat-model"
    )
    def test_the_module_never_reads_an_llm_setting(self):
        tree = ast.parse(
            Path(translate_ct2.__file__).read_text(encoding="utf-8")
        )
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "settings"
            ):
                self.assertFalse(
                    node.attr.startswith("LLM_"), msg=node.attr
                )

    @covers_requirement(
        "art-prompt-translation::the-shipped-backend-is-a-neural-machine-translator-never-a-chat-model"
    )
    def test_the_only_url_literal_is_the_pinned_model_url(self):
        # Scenario: the acquisition transport is the pinned model URL only —
        # exactly one https:// literal exists in the module and it is the
        # pinned argos-net.com model URL (the outbound-request ban's scope).
        tree = ast.parse(
            Path(translate_ct2.__file__).read_text(encoding="utf-8")
        )
        urls = [
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value.startswith("https://")
        ]
        self.assertEqual(urls, [translate_ct2._MODEL_URL])

    @covers_requirement(
        "art-prompt-translation::the-shipped-backend-is-a-neural-machine-translator-never-a-chat-model"
    )
    def test_the_seeded_success_path_makes_no_network_call(self):
        self._seed()
        self._install_stack(_ScriptedStack())
        backend = self._backend()
        with self._no_network():
            result = backend.translate(("成功路徑",))
        self.assertEqual(result, ("out0 out1",))


class CTranslate2BackendDeterminismTests(_CT2BackendCase):
    """Beam search, no sampling, byte-identical repeats (6.6)."""

    @covers_requirement(
        "art-prompt-translation::the-translator-is-built-once-per-process-and-decodes-deterministically-on-the-cpu"
    )
    def test_decoding_is_fixed_beam_search_with_no_sampling(self):
        self._seed()
        stack = self._install_stack(_ScriptedStack())
        backend = self._backend()
        first = backend.translate(("同一句",))
        second = backend.translate(("同一句",))
        # The decoding call carries EXACTLY the fixed beam width and nothing
        # else — no sampling control of any kind can accompany it.
        for _source, kwargs in stack.batch_calls:
            self.assertEqual(kwargs, {"beam_size": 5})
        # Rebuild the engine and translate again: output stays byte-identical.
        translate_ct2._ENGINES.clear()
        third = backend.translate(("同一句",))
        self.assertEqual(first, second)
        self.assertEqual(second, third)
        self.assertEqual(len(stack.translator_calls), 2, "rebuilt once")
