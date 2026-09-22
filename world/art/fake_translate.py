"""Deterministic prompt-translation test double; no engine or network access."""

from __future__ import annotations

from collections.abc import Callable

from world.art.translate import TranslateError


class FakeTranslator:
    """Replay double implementing ``translate(lines) -> sequence[str]``."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []
        self._failures: list[
            tuple[Callable[[tuple[str, ...]], bool] | None, TranslateError]
        ] = []

    def fail_every_call(self, error: TranslateError) -> None:
        """Script every subsequent ``translate`` call to raise ``error``."""
        self._failures.append((None, error))

    def add_failure(
        self, matcher: Callable[[tuple[str, ...]], bool], error: TranslateError
    ) -> None:
        """Raise ``error`` for calls whose offered lines satisfy ``matcher``."""
        self._failures.append((matcher, error))

    def translate(self, lines: tuple[str, ...]) -> tuple[str, ...]:
        """Record offered lines and return a visibly non-pass-through result."""
        self.calls.append(lines)
        for matcher, error in self._failures:
            if matcher is None or matcher(lines):
                raise error
        return tuple("[fake-translation]" for _line in lines)
