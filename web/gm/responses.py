"""JSON envelope helpers for the GM API (design §4 "API conventions").

Success: ``{"ok": true, "data": <payload>}``. Failure:
``{"ok": false, "error": {"code": "<snake_case>", "message": "<zh-TW>"}}``
with the matching HTTP status. Clients branch on ``code`` only; the message is
operator-facing Traditional Chinese.

Pagination convention (first consumer arrives in S3, none in S1/S2): the request
carries ``?cursor=<opaque>&limit=<n>`` and the response data is
``{"items": [...], "next_cursor": <opaque|null>}``. Writes are POST-only and
CSRF-protected; the first one is the S4 prompt-library reload.
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
    # S3 runtime state inspection (gm-portal-s3-runtime-state §7).
    "object_not_found": "找不到指定的物件。",
    "kind_mismatch": "此物件的種類與請求的路徑不符。",
    "unsupported_kind": "不支援的狀態種類。",
    "invalid_filter": "查詢條件不正確。",
    "invalid_limit": "每頁筆數必須介於 1 與 200 之間。",
    "invalid_cursor": "分頁游標不正確或與目前的查詢條件不符。",
    "invalid_query": "查詢文字不正確。",
    "query_too_long": "查詢文字超過 2000 字元上限。",
    # S4 authored world data (gm-portal-s4-world-data).
    "registry_not_found": "找不到指定的登錄表。",
    "entry_not_found": "此登錄表中沒有這個條目。",
    "source_not_found": "找不到指定的原始檔，或它不在可檢視的清單中。",
    "prompt_reload_failed": "重新載入提示詞庫時發生錯誤。",
    # S5 world saves (gm-portal-s5-saves).
    "invalid_save_id": "存檔識別碼格式不正確（需為 YYYYMMDDTHHMMSS-六位十六進位）。",
    "save_not_found": "找不到指定的存檔，或它不完整。",
    "save_incompatible": "這份存檔包含目前程式碼不認得的資料庫遷移，無法讀取。",
    "save_in_progress": "另一項存檔作業或待套用的讀檔正在進行，請稍後再試。",
    "save_delete_forbidden": "自動存檔由保留規則管理，不能手動刪除。",
    "save_failed": "存檔作業失敗，目前的世界狀態沒有變動。",
    # S6 deterministic console.
    "unknown_verb": "不支援的主控台操作。",
    "invalid_argument": "操作參數的格式或範圍不正確。",
    "registry_key_not_found": "找不到指定的登錄表條目。",
    "target_not_found": "找不到操作目標，或世界時鐘尚未建立。",
    "target_kind_mismatch": "此目標的種類不支援這項操作。",
    "raw_edit_invalid": "原始資料編輯內容不正確，整批變更未套用。",
    "snapshot_failed": "介入前存檔失敗，操作未執行。",
    "internal_error": "操作執行失敗，請查看伺服器紀錄。",
    "state_projection_failed": "操作已完成，但無法讀取更新後的狀態。請重新整理。",
}


def _json(body: dict[str, Any], status: int) -> JsonResponse:
    response = JsonResponse(body, status=status, json_dumps_params={"ensure_ascii": False})
    # Operator data is per-account and point-in-time; never cache it.
    response["Cache-Control"] = "no-store"
    return response


def ok(data: Any, status: int = 200) -> JsonResponse:
    """Return the success envelope around ``data``."""
    return _json({"ok": True, "data": data}, status)


def error(
    code: str, status: int, message: str | None = None,
    *, snapshot: dict[str, Any] | None = None,
) -> JsonResponse:
    """Return the failure envelope for ``code`` with its zh-TW message."""
    text = message if message is not None else ERROR_MESSAGES[code]
    body = {"ok": False, "error": {"code": code, "message": text}}
    if snapshot is not None:
        body["snapshot"] = snapshot
    return _json(body, status)
