"""Pure rendering helpers for the observability facade's single-line format.

The line shape is::

    [level] event | mod.func:line | k=v | k2=v2 | tb: Type: msg @ file:line <- ...

Rules (design §3.1): keys sorted; ``int``/``float``/``bool`` verbatim; strings
verbatim, double-quoted when they contain whitespace; all other values
``repr``-truncated to 200 characters; ``None`` keys/values omitted entirely;
the exception chain rendered outermost-first joined by `` <- ``. Rendering
never raises: any per-value failure degrades that value in place.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

VALUE_TRUNCATE_AT = 200
_CHAIN_SEPARATOR = " <- "


def _single_line(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "\\n")


def render_value(value: object) -> str:
    """Render one context value; degrade in place instead of raising."""
    try:
        if isinstance(value, str):
            if any(char.isspace() for char in value):
                return f'"{_single_line(value)}"'
            return value
        if isinstance(value, (bool, int, float)):
            return repr(value)
        text = repr(value)
    except Exception:
        return "<unrenderable>"
    if len(text) > VALUE_TRUNCATE_AT:
        text = text[:VALUE_TRUNCATE_AT]
    return text


def render_context(context: Mapping[str, Any] | None) -> str:
    """Render ``k=v`` pairs with sorted keys; ``None`` keys/values omitted."""
    if not context:
        return ""
    try:
        items = sorted(context.items(), key=lambda pair: str(pair[0]))
    except Exception:
        return ""
    parts: list[str] = []
    for key, value in items:
        if key is None or value is None:
            continue
        try:
            key_text = str(key)
        except Exception:
            key_text = "<unrenderable>"
        parts.append(f"{key_text}={render_value(value)}")
    return " ".join(parts)


def _raise_site(exc: BaseException) -> str:
    """``file:line`` of the frame that last raised this exception, if known."""
    try:
        traceback_obj = exc.__traceback__
        if traceback_obj is None:
            return "unknown:0"
        from traceback import extract_tb

        frames = extract_tb(traceback_obj)
        if not frames:
            return "unknown:0"
        last = frames[-1]
        return f"{last.filename}:{last.lineno}"
    except Exception:
        return "unknown:0"


def _chain(exc: BaseException) -> list[BaseException]:
    """Walk ``__cause__``/``__context__`` outward-in with cycle guard."""
    links: list[BaseException] = []
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        links.append(current)
        if current.__cause__ is not None:
            current = current.__cause__
        elif current.__suppress_context__:
            current = None
        else:
            current = current.__context__
    return links


def format_exception_chain(exc: BaseException) -> str:
    """One-line summary of the exception chain, outermost link first."""
    try:
        segments: list[str] = []
        for link in _chain(exc):
            try:
                message = _single_line(str(link))
            except Exception:
                message = "<unrenderable>"
            segments.append(f"{type(link).__name__}: {message} @ {_raise_site(link)}")
        return _CHAIN_SEPARATOR.join(segments)
    except Exception:
        return "<unrenderable>"


def render_line(
    level: str,
    event: str,
    caller: str,
    context: Mapping[str, Any] | None,
    tb_segment: str | None,
) -> str:
    """Assemble the final single line; every segment stays on one line."""
    parts = [f"[{level}] {_single_line(str(event))}", caller]
    context_text = render_context(context)
    if context_text:
        parts.append(context_text)
    if tb_segment:
        parts.append(f"tb: {_single_line(tb_segment)}")
    return " | ".join(parts)
