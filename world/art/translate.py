"""Bounded local prompt translation between a claimed description and sd-webui.

The worker applies this local pre-process to a claimed record's
``source_description`` after reading it and before calling the sd-webui client,
for every art subject kind. This module raises bounded failures and never logs:
the worker owns the translation boundary events.
"""

from __future__ import annotations

import importlib
from collections.abc import Sequence
from dataclasses import dataclass

from django.conf import settings

from world.lore.settlements._prose_lang import _is_han

_ERROR_CODES = frozenset({"art_translate_unavailable", "art_translate_error"})


class TranslateError(Exception):
    """One bounded, named prompt-translation failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code if code in _ERROR_CODES else "art_translate_error"


@dataclass(frozen=True)
class TranslationCounts:
    """Translation work performed for one line-preserving description."""

    lines_total: int
    lines_offered: int
    lines_untranslated: int


def needs_translation(line: str) -> bool:
    """Whether ``line`` carries Han text that needs the backend."""
    return any(_is_han(character) for character in line)


def resolve_translate_backend():
    """Instantiate the code-only ``ART_TRANSLATE_BACKEND`` seam."""
    dotted = settings.ART_TRANSLATE_BACKEND
    module_name, separator, class_name = dotted.rpartition(".")
    if not separator or not module_name or not class_name:
        raise TranslateError(
            "art_translate_unavailable",
            f"ART_TRANSLATE_BACKEND {dotted!r} is not a dotted module path",
        )
    try:
        module = importlib.import_module(module_name)
        backend_class = getattr(module, class_name)
        return backend_class()
    except Exception as error:
        raise TranslateError(
            "art_translate_unavailable",
            f"could not resolve ART_TRANSLATE_BACKEND {dotted!r}: {error}",
        ) from error


def translate_description(text: str) -> tuple[str, TranslationCounts]:
    """Translate only Han-bearing lines and preserve the source line structure."""
    try:
        lines = text.split("\n")
        offered_indexes = [
            index for index, line in enumerate(lines) if needs_translation(line)
        ]
    except Exception as error:
        raise TranslateError(
            "art_translate_error", f"could not inspect prompt text: {error}"
        ) from error
    if not offered_indexes:
        return text, TranslationCounts(0, 0, 0)

    backend = resolve_translate_backend()
    offered_lines = tuple(lines[index] for index in offered_indexes)
    try:
        result = backend.translate(offered_lines)
        if isinstance(result, (str, bytes)) or not isinstance(result, Sequence):
            raise TypeError("translation backend returned a non-sequence")
        translated_lines = tuple(result)
        if len(translated_lines) != len(offered_lines):
            raise ValueError(
                "translation backend returned "
                f"{len(translated_lines)} lines for {len(offered_lines)} inputs"
            )
        if any(not isinstance(line, str) for line in translated_lines):
            raise TypeError("translation backend returned a non-string line")
        output_lines = list(lines)
        for index, translated in zip(offered_indexes, translated_lines, strict=True):
            output_lines[index] = translated
        return "\n".join(output_lines), TranslationCounts(
            lines_total=len(lines),
            lines_offered=len(offered_lines),
            lines_untranslated=sum(needs_translation(line) for line in translated_lines),
        )
    except Exception as error:
        if isinstance(error, TranslateError) and error.code == "art_translate_error":
            raise
        raise TranslateError(
            "art_translate_error", f"prompt translation failed: {error}"
        ) from error
