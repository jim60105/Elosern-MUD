"""Account inspection reader (S3 §4 "Account").

Reuses the account roster read model for owned characters and reads everything
else straight off the account: permissions, creation and last-login dates, live
sessions and the owned character list. Nothing is written and no character
shell is provisioned.
"""

from __future__ import annotations

from typing import Any

from web.gm.readers._entities import (
    dbref_of,
    label_of,
    read_attr,
    sequence_values,
    typeclass_of,
)
from web.gm.readers._sections import (
    SectionError,
    chip,
    chips,
    column,
    compute_sections,
    ledger,
    link,
    row,
    table,
    table_row,
)

KIND = "accounts"


def _permission_names(account: Any) -> list[str]:
    handler = getattr(account, "permissions", None)
    entries = handler.all() if handler is not None and hasattr(handler, "all") else []
    names = []
    for entry in entries:
        key = getattr(entry, "db_key", None)
        names.append(str(key if key is not None else entry))
    return sorted(set(names))


def _owned_characters(account: Any) -> list[Any]:
    """The account's own characters, read from the stored list itself.

    ``account.characters`` wraps the same attribute but its handler cleans and
    re-assigns the list on construction, and ``build_account_roster`` renders a
    *puppeted character's* view that refuses any other actor. Reading the
    stored identity list and resolving the live objects is the same ownership
    boundary with no write at all.
    """
    stored = read_attr(account, "_playable_characters", default=None)
    if stored is None:
        raise SectionError("knowledge_unavailable", "無法讀取此帳號的角色清單。")
    entries = sequence_values(stored)
    if entries is None:
        raise SectionError("stored_state_invalid", "帳號的角色清單格式不正確。")
    identities: list[int] = []
    for entry in entries:
        value = getattr(entry, "pk", entry)
        if isinstance(value, bool) or not isinstance(value, int):
            continue
        identities.append(int(value))
    if not identities:
        return []
    from evennia.objects.models import ObjectDB

    by_identity = {
        entity.pk: entity
        for entity in ObjectDB.objects.filter(pk__in=sorted(set(identities)))
    }
    return [by_identity[pk] for pk in sorted(set(identities)) if pk in by_identity]


def _live_sessions(account: Any) -> list[Any]:
    handler = getattr(account, "sessions", None)
    if handler is None or not hasattr(handler, "all"):
        raise SectionError(
            "source_unavailable", "此帳號的連線工作階段目前無法讀取。"
        )
    return list(handler.all())


def item_of(account: Any) -> dict[str, Any]:
    """One account list row (summary fields only)."""
    dbref = dbref_of(account)
    permissions = _permission_names(account)
    from evennia.objects.models import ObjectDB

    character_total = ObjectDB.objects.filter(db_account_id=dbref).count()
    return {
        "id": str(dbref),
        "kind": KIND,
        "dbref": dbref,
        "label": label_of(account),
        "fields": [
            row("權限", "、".join(permissions) or "無"),
            row("角色數", character_total),
            row("最後登入", _stamp(getattr(account, "last_login", None))),
        ],
    }


def _stamp(value: Any) -> str:
    from web.gm.readers._json import json_value

    return json_value(value) if value is not None else "—"


def detail(account: Any) -> dict[str, Any]:
    """The account detail sections."""

    def identity() -> dict[str, Any]:
        return ledger(
            [
                row("名稱", label_of(account)),
                row("識別碼", f"#{dbref_of(account)}", mono=True),
                row("型別", typeclass_of(account), mono=True),
            ]
        )

    def access() -> dict[str, Any]:
        return chips(
            [chip(name) for name in _permission_names(account)]
            or [chip("無權限字串")],
            note="超級使用者" if getattr(account, "is_superuser", False) else "一般帳號",
        )

    def lifecycle() -> dict[str, Any]:
        return ledger(
            [
                row("建立時間", _stamp(getattr(account, "date_joined", None)), mono=True),
                row("最後登入", _stamp(getattr(account, "last_login", None)), mono=True),
                row("啟用中", "是" if getattr(account, "is_active", False) else "否"),
            ]
        )

    def sessions() -> dict[str, Any]:
        entries = _live_sessions(account)
        rows = []
        for session in entries:
            puppet = getattr(session, "puppet", None)
            cells = {
                "session": mono_cell(str(getattr(session, "sessid", "") or "—")),
                "puppet": _entity_cell(puppet),
                "address": mono_cell(str(getattr(session, "address", "") or "—")),
            }
            rows.append(table_row(cells, key=str(getattr(session, "sessid", ""))))
        return table(
            [
                column("session", "工作階段", mono=True),
                column("puppet", "操縱角色"),
                column("address", "來源位址", mono=True),
            ],
            rows,
            empty_note="目前沒有連線中的工作階段。",
        )

    def characters() -> dict[str, Any]:
        rows = []
        for character in _owned_characters(account):
            dbref = dbref_of(character)
            cells = {
                "name": _entity_cell(character, "characters"),
                "identity": mono_cell(f"#{dbref}"),
                "pending": mono_cell(
                    "是" if read_attr(character, "creation_pending", default=False) else "否"
                ),
            }
            rows.append(table_row(cells, key=str(dbref)))
        return table(
            [
                column("name", "角色"),
                column("identity", "識別碼", mono=True),
                column("pending", "待完成建立"),
            ],
            rows,
            empty_note="此帳號目前沒有角色。",
        )

    return {
        "id": str(dbref_of(account)),
        "kind": KIND,
        "label": label_of(account),
        "dbref": dbref_of(account),
        "typeclass": typeclass_of(account),
        "sections": compute_sections(
            [
                ("identity", "身分", identity),
                ("access", "權限", access),
                ("lifecycle", "帳號歷程", lifecycle),
                ("sessions", "連線工作階段", sessions),
                ("characters", "擁有的角色", characters),
            ]
        ),
    }


def _entity_cell(entity: Any, kind: str = "object") -> dict[str, Any]:
    """A table cell for an entity reference (linked when it has a dbref)."""
    if entity is None:
        return {"value": "—"}
    dbref = dbref_of(entity)
    label = label_of(entity)
    if dbref is None:
        return {"value": label}
    return {
        "value": f"#{dbref}",
        "mono": True,
        "link": link(kind, dbref, label),
    }


def mono_cell(value: Any) -> dict[str, Any]:
    """A plain monospace table cell."""
    return {"value": value, "mono": True}


__all__ = ["KIND", "detail", "item_of"]
