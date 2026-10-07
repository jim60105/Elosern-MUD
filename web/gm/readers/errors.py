"""Lookup and filter errors the runtime readers raise for the transport.

The transport maps these onto the S3 error matrix (design §7): an absent object
is ``object_not_found``, an object that exists but is not the kind the route
names is ``kind_mismatch``, and a filter the projection cannot use is
``invalid_filter``. The S4 world-data readers add ``registry_not_found``,
``entry_not_found`` and ``source_not_found`` (all 404).
"""

from __future__ import annotations


class ReaderError(Exception):
    """A reader failure with the stable code the transport reports."""

    code = "source_unavailable"
    status = 400

    def __init__(self, message: str, *, code: str | None = None, status: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status is not None:
            self.status = status


class ObjectNotFound(ReaderError):
    code = "object_not_found"
    status = 404

    def __init__(self) -> None:
        super().__init__("找不到指定的物件。")


class KindMismatch(ReaderError):
    code = "kind_mismatch"
    status = 404

    def __init__(self) -> None:
        super().__init__("此物件的種類與請求的路徑不符。")


class UnsupportedKind(ReaderError):
    code = "unsupported_kind"
    status = 404

    def __init__(self, kind: str) -> None:
        super().__init__(f"不支援的狀態種類：{kind}。", code="unsupported_kind", status=404)


class InvalidFilter(ReaderError):
    code = "invalid_filter"
    status = 400

    def __init__(self, message: str = "查詢條件不正確。") -> None:
        super().__init__(message, code="invalid_filter", status=400)


class QueryTooLong(ReaderError):
    code = "query_too_long"
    status = 400

    def __init__(self) -> None:
        super().__init__("查詢文字超過 2000 字元上限。", code="query_too_long", status=400)


class InvalidQuery(ReaderError):
    code = "invalid_query"
    status = 400

    def __init__(self, message: str = "查詢文字不正確。") -> None:
        super().__init__(message, code="invalid_query", status=400)


class RegistryNotFound(ReaderError):
    code = "registry_not_found"
    status = 404

    def __init__(self) -> None:
        super().__init__("找不到指定的登錄表。", code="registry_not_found", status=404)


class EntryNotFound(ReaderError):
    code = "entry_not_found"
    status = 404

    def __init__(self) -> None:
        super().__init__("此登錄表中沒有這個條目。", code="entry_not_found", status=404)


class SourceNotFound(ReaderError):
    code = "source_not_found"
    status = 404

    def __init__(self) -> None:
        super().__init__("找不到指定的原始檔，或它不在可檢視的清單中。", code="source_not_found", status=404)


__all__ = [
    "EntryNotFound",
    "InvalidFilter",
    "InvalidQuery",
    "KindMismatch",
    "ObjectNotFound",
    "QueryTooLong",
    "ReaderError",
    "RegistryNotFound",
    "SourceNotFound",
    "UnsupportedKind",
]
