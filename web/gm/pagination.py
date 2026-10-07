"""Opaque cursor pagination for the runtime state lists.

The S1 envelope reserves ``{"items": [...], "next_cursor": <opaque|null>}`` and
defines no cursor format (its first consumer is S3). The cursor is a base64url
JSON document carrying the offset of the next page plus the filter fingerprint
it was issued under, so a cursor replayed against different filters is refused
instead of silently skipping rows. Ordering itself stays deterministic per
kind: every list orders by an indexed column and a unique tie-breaker.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
from typing import Any, Iterable

DEFAULT_LIMIT = 50
MAX_LIMIT = 200
CURSOR_VERSION = 1


class PaginationError(ValueError):
    """A limit or cursor the caller supplied is not usable."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def parse_limit(raw: Any) -> int:
    """``limit`` with the S3 default (50) and maximum (200)."""
    if raw is None or raw == "":
        return DEFAULT_LIMIT
    text = str(raw).strip()
    if not text.isdigit():
        raise PaginationError("invalid_limit", "每頁筆數必須是正整數（1–200）。")
    value = int(text)
    if value < 1 or value > MAX_LIMIT:
        raise PaginationError("invalid_limit", "每頁筆數必須介於 1 與 200 之間。")
    return value


def fingerprint(filters: dict[str, Any]) -> str:
    """A stable digest of the filter set a cursor belongs to."""
    payload = json.dumps(filters, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def encode_cursor(offset: int, filters: dict[str, Any]) -> str:
    document = {"v": CURSOR_VERSION, "o": int(offset), "f": fingerprint(filters)}
    raw = json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(raw: Any, filters: dict[str, Any]) -> int:
    """Return the offset a cursor names, refusing a foreign or broken one."""
    text = str(raw or "").strip()
    if not text:
        return 0
    padded = text + "=" * (-len(text) % 4)
    try:
        document = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
    except (ValueError, UnicodeDecodeError, binascii.Error) as error:
        raise PaginationError("invalid_cursor", "分頁游標格式不正確。") from error
    if (
        not isinstance(document, dict)
        or document.get("v") != CURSOR_VERSION
        or not isinstance(document.get("o"), int)
        or document["o"] < 0
        or document.get("f") != fingerprint(filters)
    ):
        raise PaginationError("invalid_cursor", "分頁游標與目前的查詢條件不符。")
    return int(document["o"])


def page(rows: Iterable[Any], *, offset: int, limit: int) -> tuple[list[Any], str | None]:
    """Slice ``rows`` for one page and build its ``next_cursor``."""
    items = list(rows)
    window = items[offset : offset + limit]
    next_offset = offset + len(window)
    has_more = next_offset < len(items)
    return window, (str(next_offset) if has_more else None)


def envelope(items: list[Any], offset: int, limit: int, filters: dict[str, Any]) -> dict[str, Any]:
    """The list payload: summary items plus the opaque next cursor."""
    window, marker = page(items, offset=offset, limit=limit)
    next_cursor = encode_cursor(int(marker), filters) if marker is not None else None
    return {"items": window, "next_cursor": next_cursor}


__all__ = [
    "CURSOR_VERSION",
    "DEFAULT_LIMIT",
    "MAX_LIMIT",
    "PaginationError",
    "decode_cursor",
    "encode_cursor",
    "envelope",
    "fingerprint",
    "page",
    "parse_limit",
]
