"""Pure contracts for the bounded art prompt-translation seam."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
import unittest
from unittest.mock import patch

from django.test import override_settings

from world.art.fake_translate import FakeTranslator
from world.art.translate import (
    TranslateError,
    TranslationCounts,
    resolve_translate_backend,
    translate_description,
)
import world.art.translate as translate


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

    def test_an_arbitrary_backend_exception_becomes_art_translate_error(self):
        with self.assertRaises(TranslateError) as caught:
            self._translate_with(_StubBackend(error=RuntimeError("engine exploded")))
        self.assertEqual(caught.exception.code, "art_translate_error")
        self.assertIsInstance(caught.exception.__cause__, RuntimeError)

    def test_scripted_bounded_backend_error_remains_art_translate_error(self):
        with self.assertRaises(TranslateError) as caught:
            self._translate_with(
                _StubBackend(error=TranslateError("art_translate_error", "scripted"))
            )
        self.assertEqual(caught.exception.code, "art_translate_error")

    def test_unknown_backend_error_code_is_normalized(self):
        with self.assertRaises(TranslateError) as caught:
            self._translate_with(_StubBackend(error=TranslateError("unexpected", "bad")))
        self.assertEqual(caught.exception.code, "art_translate_error")

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

    def test_mixed_lines_are_batched_reassembled_and_count_untranslated(self):
        backend = _StubBackend(result=("translated", "專名"))
        text = "Latin\n漢字第一行\nuntouched\n漢字第二行"
        actual, counts = self._translate_with(backend, text)
        self.assertEqual(backend.calls, [("漢字第一行", "漢字第二行")])
        self.assertEqual(actual, "Latin\ntranslated\nuntouched\n專名")
        self.assertEqual(counts, TranslationCounts(4, 2, 1))

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

    def test_translate_module_has_no_observability_dependency(self):
        source = Path(translate.__file__).read_text(encoding="utf-8")
        self.assertNotIn("world.observability", source)


class FakeTranslatorTests(unittest.TestCase):
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
