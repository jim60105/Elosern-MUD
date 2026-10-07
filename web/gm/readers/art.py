"""Art record inspection reader (S3 §4 "Art asset").

Art records are Scripts keyed ``art:<subject-key>`` (or ``art:<subject>:
gen:<image-id>`` for a spent gallery job), so the raw tab reports their stored
record fields rather than Evennia object metadata. The thumbnail is served
through the existing ``/art/`` media route and is offered only when the stored
identity resolves to an existing file under ``ART_STORE_ROOT``.
"""

from __future__ import annotations

from typing import Any

from web.gm.readers._entities import key_of, mapping_values, read_attr
from web.gm.readers._json import json_value
from web.gm.readers._sections import (
    column,
    compute_sections,
    empty,
    ledger,
    row,
    table,
    table_row,
    text,
    tree,
)

KIND = "art"

RECORD_FIELDS = (
    "kind",
    "subject_key",
    "source_description",
    "source_hash",
    "prompt_digest",
    "generation_token",
    "status",
    "output_identity",
    "prior_output_identity",
    "attempt_count",
    "last_error_code",
    "enqueued_at",
    "claimed_at",
    "completed_at",
    "aspect_ratio",
    "hash_changed",
    "seed",
    "gallery_image_id",
    "gallery_binding",
    "gallery_face_rect",
    "gallery_requested_fields",
)


def records() -> list[Any]:
    """Every art record Script, ordered by its stable key."""
    from world.art.store import ArtAssetRecord

    return list(ArtAssetRecord.objects.all().order_by("db_key"))


def _gallery_identity(record: Any, image_id: Any) -> str | None:
    """The stored identity of a gallery job's published card, when it exists."""
    subject_key = read_attr(record, "subject_key", default=None)
    if not isinstance(subject_key, str) or not subject_key:
        return None
    from evennia.utils.search import search_script

    for sibling in search_script(f"art:{subject_key}"):
        for stored_entry in sibling.db.cards or []:
            entry = mapping_values(stored_entry)
            if entry is None:
                continue
            if str(entry.get("image_id")) != str(image_id):
                continue
            identity = entry.get("stored_identity")
            if isinstance(identity, str) and identity:
                return identity
    return None


def thumbnail_url(record: Any) -> str | None:
    """``/art/<identity>`` for an existing stored file, else None."""
    from world.art.paths import resolved_under_store_root

    candidates = []
    output = read_attr(record, "output_identity", default=None)
    if isinstance(output, str) and output:
        candidates.append(output)
    gallery_image_id = read_attr(record, "gallery_image_id", default=None)
    if gallery_image_id:
        identity = _gallery_identity(record, gallery_image_id)
        if identity:
            candidates.append(identity)
    for identity in candidates:
        resolved = resolved_under_store_root(identity)
        if resolved is not None and resolved.is_file():
            return f"/art/{identity}"
    return None


def detail(record: Any) -> dict[str, Any]:
    identity = key_of(record)

    def identity_section() -> dict[str, Any]:
        thumbnail = thumbnail_url(record)
        rows = [
            row("記錄鍵", identity, mono=True),
            row("主體", read_attr(record, "subject_key", default=None) or "—", mono=True),
            row("種類", read_attr(record, "kind", default=None) or "—", mono=True),
            row("狀態", read_attr(record, "status", default=None) or "—", mono=True),
            row(
                "縮圖",
                thumbnail or "沒有可用的檔案",
                mono=True,
                link_to={"kind": "media", "id": thumbnail} if thumbnail else None,
                tone="ok" if thumbnail else None,
            ),
        ]
        return ledger(rows)

    def generation_section() -> dict[str, Any]:
        rows = [
            row("來源敘述", "（見下方）" if read_attr(record, "source_description", default=None) else "—"),
            row("來源雜湊", read_attr(record, "source_hash", default=None) or "—", mono=True),
            row("提示摘要", read_attr(record, "prompt_digest", default=None) or "—", mono=True),
            row("生成權杖", read_attr(record, "generation_token", default=None) or "—", mono=True),
            row("嘗試次數", read_attr(record, "attempt_count", default=0), mono=True),
            row("最後錯誤", read_attr(record, "last_error_code", default=None) or "—", mono=True),
            row("排入時間", json_value(read_attr(record, "enqueued_at", default=None)), mono=True),
            row("取得時間", json_value(read_attr(record, "claimed_at", default=None)), mono=True),
            row("完成時間", json_value(read_attr(record, "completed_at", default=None)), mono=True),
            row("長寬比", read_attr(record, "aspect_ratio", default=None) or "—", mono=True),
            row("種子", read_attr(record, "seed", default=None) if read_attr(record, "seed", default=None) is not None else "—", mono=True),
        ]
        return ledger(rows)

    def output_section() -> dict[str, Any]:
        rows = [
            row("輸出識別", read_attr(record, "output_identity", default=None) or "—", mono=True),
            row(
                "前一版輸出",
                read_attr(record, "prior_output_identity", default=None) or "—",
                mono=True,
            ),
            row("雜湊已變更", "是" if read_attr(record, "hash_changed", default=False) else "否"),
        ]
        return ledger(rows)

    def gallery_section() -> dict[str, Any]:
        image_id = read_attr(record, "gallery_image_id", default=None)
        if not image_id:
            return empty("這不是畫廊任務記錄。")
        return ledger(
            [
                row("畫廊影像", str(image_id), mono=True),
                row("綁定", json_value(read_attr(record, "gallery_binding", default=None)), mono=True),
                row("臉部範圍", json_value(read_attr(record, "gallery_face_rect", default=None)), mono=True),
                row(
                    "要求欄位",
                    "、".join(str(item) for item in (read_attr(record, "gallery_requested_fields", default=None) or []))
                    or "—",
                    mono=True,
                ),
            ]
        )

    def prompt_section() -> dict[str, Any]:
        description = read_attr(record, "source_description", default=None)
        if not description:
            return empty("此記錄沒有來源敘述。")
        return text(str(description))

    sections = compute_sections(
        [
            ("identity", "身分", identity_section),
            ("prompt", "來源敘述", prompt_section),
            ("generation", "生成", generation_section),
            ("output", "輸出", output_section),
            ("gallery", "畫廊任務", gallery_section),
        ]
    )
    return {
        "id": identity,
        "kind": KIND,
        "label": str(read_attr(record, "subject_key", default=None) or identity),
        "dbref": None,
        "typeclass": "",
        "sections": sections,
        "raw": {"record": json_value(_record_fields(record))},
    }


def _record_fields(record: Any) -> dict[str, Any]:
    return {field: read_attr(record, field, default=None) for field in RECORD_FIELDS}


def item_of(record: Any) -> dict[str, Any]:
    """One art list row (summary fields only)."""
    identity = key_of(record)
    return {
        "id": identity,
        "kind": KIND,
        "dbref": None,
        "label": str(read_attr(record, "subject_key", default=None) or identity),
        "fields": [
            row("種類", read_attr(record, "kind", default=None) or "—", mono=True),
            row("狀態", read_attr(record, "status", default=None) or "—"),
            row("記錄鍵", identity, mono=True),
            row("失敗代碼", read_attr(record, "last_error_code", default=None) or "—", mono=True),
            row("畫廊任務", "是" if read_attr(record, "gallery_image_id", default=None) else "否"),
        ],
    }


def list_items(filters: dict[str, Any]) -> list[dict[str, Any]]:
    """Every art record, filtered on its own stored fields."""
    rows = [item_of(record) for record in records()]
    status = filters.get("status")
    art_kind = filters.get("kind")
    if status:
        rows = [
            row
            for row in rows
            if _field(row, "狀態") == str(status)
        ]
    if art_kind:
        rows = [row for row in rows if _field(row, "種類") == str(art_kind)]
    return rows


def _field(item: dict[str, Any], label: str) -> Any:
    for field in item.get("fields", []):
        if field.get("label") == label:
            return field.get("value")
    return None


__all__ = [
    "KIND",
    "RECORD_FIELDS",
    "detail",
    "item_of",
    "list_items",
    "records",
    "thumbnail_url",
]
