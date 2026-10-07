"""JSON envelope helpers for the GM API (design §4 "API conventions").

Success: ``{"ok": true, "data": <payload>}``. Failure:
``{"ok": false, "error": {"code": "<snake_case>", "message": "<zh-TW>"}}``
with the matching HTTP status. Clients branch on ``code`` only; the message is
operator-facing Traditional Chinese.

Pagination convention (first consumer arrives in S3, none in S1/S2): the request
carries ``?cursor=<opaque>&limit=<n>`` and the response data is
``{"items": [...], "next_cursor": <opaque|null>}``. Writes are POST-only and
CSRF-protected; S1 adds no production write endpoint.
"""

from __future__ import annotations

from typing import Any

from django.http import JsonResponse

ERROR_MESSAGES: dict[str, str] = {
    "unauthenticated": "請先登入。",
    "forbidden": "權限不足：需要 Developer 權限。",
    "not_found": "找不到此 API 路徑。",
    "method_not_allowed": "不支援此請求方法。",
    "csrf_failed": "安全驗證失敗，請重新整理頁面後再試一次。",
    "database_unreadable": "資料庫目前無法讀取。",
    "version_unavailable": "無法讀取遊戲版本。",
    "invalid_call_id": "呼叫識別碼格式不正確（需為 32 位小寫十六進位）。",
    "transcript_not_found": "找不到此呼叫的 transcript 紀錄（可能已超過保留期限）。",
    "transcript_disabled": "LLM transcript 已停用，無法查詢呼叫內容。",
}


def _json(body: dict[str, Any], status: int) -> JsonResponse:
    response = JsonResponse(body, status=status, json_dumps_params={"ensure_ascii": False})
    # Operator data is per-account and point-in-time; never cache it.
    response["Cache-Control"] = "no-store"
    return response


def ok(data: Any, status: int = 200) -> JsonResponse:
    """Return the success envelope around ``data``."""
    return _json({"ok": True, "data": data}, status)


def error(code: str, status: int, message: str | None = None) -> JsonResponse:
    """Return the failure envelope for ``code`` with its zh-TW message."""
    text = message if message is not None else ERROR_MESSAGES[code]
    return _json({"ok": False, "error": {"code": code, "message": text}}, status)
