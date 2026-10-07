"""Independent summary sections and their presentation vocabulary.

Each curated summary is an ordered list of named sections computed on its own
(design §1/§7): a failing source yields an error slot for that section only, so
the operator still sees every section that did read. The payload vocabulary
(ledger rows, tables, groups, tiles, chips, JSON trees, text) is the one shape
the GM SPA renders for every entity kind, which keeps the curated panels
uniform without moving rule calculations into the browser.

Section keys are stable snake_case identifiers; titles are Traditional Chinese.
Clients branch on ``error.code`` only.
"""

from __future__ import annotations

from typing import Any, Callable

from world.observability import log_warn

#: Operator-facing copy for a failed section, keyed by its stable code.
SECTION_MESSAGES: dict[str, str] = {
    "knowledge_unavailable": "此區塊的來源資料目前無法讀取。",
    "status_unreadable": "角色狀態資料損毀，無法解析。",
    "stored_state_invalid": "儲存的資料格式不正確，無法顯示。",
    "source_unavailable": "此區塊的來源目前不存在或無法使用。",
}


class SectionError(Exception):
    """A section failure with a stable snake_case code."""

    def __init__(self, code: str, message: str | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.message = message if message is not None else SECTION_MESSAGES.get(
            code, SECTION_MESSAGES["source_unavailable"]
        )


def error_slot(code: str, message: str | None = None) -> dict[str, Any]:
    """The error object a failed section carries in its own slot."""
    return {
        "error": {
            "code": code,
            "message": message if message is not None else SECTION_MESSAGES.get(
                code, SECTION_MESSAGES["source_unavailable"]
            ),
        }
    }


def compute_sections(
    specs: list[tuple[str, str, Callable[[], dict[str, Any]]]],
) -> list[dict[str, Any]]:
    """Compute every ``(key, title, builder)`` independently.

    A builder returns the section payload without ``key``/``title``; this
    wrapper adds them and contains a failure as that section's error slot.
    """
    sections: list[dict[str, Any]] = []
    for key, title, build in specs:
        try:
            payload = build()
        except SectionError as error:
            log_warn(
                "gm_section_failed",
                exc=error,
                context={"section": key, "code": error.code},
            )
            sections.append({"key": key, "title": title, **error_slot(error.code, error.message)})
        except Exception as error:
            log_warn(
                "gm_section_failed",
                exc=error,
                context={"section": key, "code": "source_unavailable"},
            )
            sections.append(
                {
                    "key": key,
                    "title": title,
                    **error_slot(
                        "source_unavailable",
                        f"{title}：{SECTION_MESSAGES['source_unavailable']}",
                    ),
                }
            )
        else:
            sections.append({"key": key, "title": title, **payload})
    return sections


# --- the presentation vocabulary -------------------------------------------


def link(kind: str, identity: Any, label: str | None = None) -> dict[str, Any]:
    """One identifier rendered as a link to its entity, source, or call."""
    value: dict[str, Any] = {"kind": str(kind), "id": str(identity)}
    if label:
        value["label"] = str(label)
    return value


def row(
    label: str,
    value: Any,
    *,
    key: str | None = None,
    mono: bool = False,
    link_to: dict[str, Any] | None = None,
    tone: str | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {"key": key or label, "label": str(label), "value": value}
    if mono:
        entry["mono"] = True
    if link_to is not None:
        entry["link"] = link_to
    if tone:
        entry["tone"] = tone
    return entry


def cell(
    value: Any,
    *,
    mono: bool = False,
    link_to: dict[str, Any] | None = None,
    tone: str | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {"value": value}
    if mono:
        entry["mono"] = True
    if link_to is not None:
        entry["link"] = link_to
    if tone:
        entry["tone"] = tone
    return entry


def column(key: str, label: str, *, mono: bool = False) -> dict[str, Any]:
    entry: dict[str, Any] = {"key": key, "label": label}
    if mono:
        entry["mono"] = True
    return entry


def table_row(cells: dict[str, dict[str, Any]], *, key: str | None = None) -> dict[str, Any]:
    entry: dict[str, Any] = {"cells": cells}
    if key:
        entry["key"] = key
    return entry


def tile(label: str, value: Any, *, key: str | None = None, unit: str | None = None,
         tone: str | None = None) -> dict[str, Any]:
    entry: dict[str, Any] = {"key": key or label, "label": str(label), "value": value}
    if unit:
        entry["unit"] = unit
    if tone:
        entry["tone"] = tone
    return entry


def chip(label: str, *, key: str | None = None, tone: str | None = None,
         link_to: dict[str, Any] | None = None) -> dict[str, Any]:
    entry: dict[str, Any] = {"key": key or label, "label": str(label)}
    if tone:
        entry["tone"] = tone
    if link_to is not None:
        entry["link"] = link_to
    return entry


def group(title: str, rows: list[dict[str, Any]], *, key: str | None = None,
          note: str | None = None) -> dict[str, Any]:
    entry: dict[str, Any] = {"key": key or title, "title": str(title), "rows": list(rows)}
    if note:
        entry["note"] = note
    return entry


def ledger(rows: list[dict[str, Any]], *, note: str | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {"type": "ledger", "rows": list(rows)}
    if note:
        value["note"] = note
    return value


def table(columns: list[dict[str, Any]], rows: list[dict[str, Any]], *,
          note: str | None = None, empty_note: str | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {
        "type": "table",
        "columns": list(columns),
        "rows": list(rows),
    }
    if note:
        value["note"] = note
    if empty_note:
        value["empty_note"] = empty_note
    return value


def groups(items: list[dict[str, Any]], *, note: str | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {"type": "groups", "groups": list(items)}
    if note:
        value["note"] = note
    return value


def tiles(items: list[dict[str, Any]], *, note: str | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {"type": "tiles", "tiles": list(items)}
    if note:
        value["note"] = note
    return value


def chips(items: list[dict[str, Any]], *, note: str | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {"type": "chips", "chips": list(items)}
    if note:
        value["note"] = note
    return value


def tree(value: Any, *, note: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"type": "tree", "value": value}
    if note:
        payload["note"] = note
    return payload


def text(body: str, *, note: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"type": "text", "text": body}
    if note:
        payload["note"] = note
    return payload


def empty(note: str, *, tone: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"type": "empty", "note": note}
    if tone:
        payload["tone"] = tone
    return payload


def list_summary(rows: list[dict[str, Any]], *, note: str | None = None) -> dict[str, Any]:
    """A compact bullet list (used by narrative subtypes)."""
    payload: dict[str, Any] = {"type": "bullets", "items": [str(item) for item in rows]}
    if note:
        payload["note"] = note
    return payload


__all__ = [
    "SECTION_MESSAGES",
    "SectionError",
    "cell",
    "chip",
    "chips",
    "column",
    "compute_sections",
    "empty",
    "error_slot",
    "group",
    "groups",
    "ledger",
    "link",
    "list_summary",
    "row",
    "table",
    "table_row",
    "text",
    "tile",
    "tiles",
    "tree",
]
