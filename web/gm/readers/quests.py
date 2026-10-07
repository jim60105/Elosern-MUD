"""Quest record inspection reader (S3 §4 "Quest record").

Runtime records come from the character-owned quest log through the quest
runtime's strict reader (``QuestRecord`` fields only — the id is owner-scoped,
so the owner is part of the identity), rewards from the immutable issuance
registry, and generated quests additionally show their stored payload through
the store's non-creating read.
"""

from __future__ import annotations

from typing import Any

from web.gm.readers import characters
from web.gm.readers._entities import (
    dbref_of,
    label_of,
    mapping_values,
    read_attr,
    sequence_values,
)
from web.gm.readers._sections import (
    column,
    compute_sections,
    empty,
    ledger,
    link,
    row,
    table,
    table_row,
    text,
    tree,
)
from web.gm.readers.world import authored_link

KIND = "quests"

#: Quest record states, mirrored from ``world.quests.runtime.QuestState``.
STATE_LABELS = {
    "in_progress": "進行中",
    "completed": "已完成",
    "failed": "已失敗",
}


def resolve_owner(owner_dbref: Any) -> Any:
    """Resolve the quest log's owning character, or raise the lookup error."""
    from evennia.objects.models import ObjectDB
    from web.gm.readers.errors import InvalidFilter, ObjectNotFound

    if owner_dbref in (None, ""):
        raise InvalidFilter("查詢任務紀錄必須指定擁有者（?owner=#dbref）。")
    text_value = str(owner_dbref).strip().lstrip("#")
    if not text_value.isdigit():
        raise InvalidFilter("擁有者必須是角色的 dbref（例如 ?owner=#5）。")
    actor = ObjectDB.objects.filter(pk=int(text_value)).first()
    if actor is None:
        raise ObjectNotFound()
    return actor


def owner_records(owner_dbref: Any) -> list[Any]:
    from world.quests.runtime import read_records

    return read_records(resolve_owner(owner_dbref))


def generated_payloads() -> list[dict]:
    from world.quests.generated_quest_store import read_payloads

    return read_payloads()


def _reward_of(record: Any) -> Any | None:
    from world.rules.quest_issuance import QUEST_ISSUANCE_REGISTRY

    return QUEST_ISSUANCE_REGISTRY.get((record.definition_key, record.issuer_key))


def _reward_rows(record: Any) -> list[dict[str, Any]]:
    issuance = _reward_of(record)
    if issuance is None:
        return []
    reward = issuance.reward
    rows = [
        row("發布識別", record.issuer_key, mono=True),
        row("結算方式", getattr(issuance.settlement, "value", str(issuance.settlement)), mono=True),
        row("銅幣", reward.copper, mono=True),
        row("功績", reward.merit, mono=True),
    ]
    if reward.items:
        rows.append(
            row(
                "物品",
                "、".join(
                    f"{characters.item_label(item.item_key)} × {item.quantity}"
                    for item in reward.items
                ),
            )
        )
    return rows


def _payload_for(record: Any) -> dict | None:
    for stored_payload in generated_payloads():
        payload = mapping_values(stored_payload)
        if payload is None:
            continue
        definition = mapping_values(payload.get("definition"))
        issuance = mapping_values(payload.get("issuance"))
        if definition is None or issuance is None:
            continue
        if definition.get("key") == record.definition_key and issuance.get("issuer_key") == record.issuer_key:
            return dict(payload)
    return None


def _entity_link_cell(identity: Any) -> dict[str, Any]:
    from evennia.objects.models import ObjectDB

    if not isinstance(identity, int) or isinstance(identity, bool):
        return {"value": "—"}
    entity = ObjectDB.objects.filter(pk=identity).first()
    if entity is None:
        return {"value": f"#{identity}", "mono": True}
    return {
        "value": f"#{identity}",
        "mono": True,
        "link": link("object", identity, label_of(entity)),
    }


def detail_for_record(record: Any, owner: Any) -> dict[str, Any]:
    def identity() -> dict[str, Any]:
        rows = [
            row("任務編號", record.quest_id, mono=True),
            row(
                "定義鍵",
                record.definition_key,
                mono=True,
                link_to=authored_link("quest_definitions", record.definition_key),
            ),
            row("發布識別", record.issuer_key, mono=True),
            row(
                "擁有角色",
                f"#{dbref_of(owner)}",
                mono=True,
                link_to=link("characters", dbref_of(owner), label_of(owner)),
            ),
            row("狀態", STATE_LABELS.get(str(record.state.value), str(record.state)), tone="ok" if record.state.value == "completed" else None),
            row("階段", record.stage_index, mono=True),
            row("階段進度", record.stage_progress, mono=True),
            row("接受 tick", record.accepted_tick, mono=True),
            row(
                "截止 tick",
                record.deadline_tick if record.deadline_tick is not None else "無期限",
                mono=True,
            ),
            row("追蹤中", "是" if record.tracked else "否"),
            row("失敗原因", record.failure_reason or "—", mono=True),
        ]
        return ledger(rows)

    def definition() -> dict[str, Any]:
        from world.quests.definitions import QUEST_DEFINITION_REGISTRY

        definition_row = QUEST_DEFINITION_REGISTRY.get(record.definition_key)
        if definition_row is None:
            return empty("此定義鍵目前不在任務註冊表中。")
        rows = [
            row("名稱", getattr(definition_row, "display_name", "—")),
            row("類型", str(getattr(definition_row, "quest_type", "—")), mono=True),
            row("階級", str(getattr(definition_row, "rank", "—")), mono=True),
        ]
        stages = getattr(definition_row, "stages", ())
        rows.append(row("階段總數", len(stages)))
        if 0 <= record.stage_index < len(stages):
            objective = stages[record.stage_index].objective
            rows.append(row("目前目標", str(getattr(objective, "kind", "—")), mono=True))
            rows.append(row("目標數量", getattr(objective, "quantity", "—"), mono=True))
            if getattr(objective, "site_key", None):
                rows.append(
                    row(
                        "據點",
                        str(objective.site_key),
                        mono=True,
                        link_to=authored_link("monster_sites", objective.site_key),
                    )
                )
            if getattr(objective, "species_key", None):
                rows.append(
                    row(
                        "物種",
                        str(objective.species_key),
                        mono=True,
                        link_to=authored_link("monster_species", objective.species_key),
                    )
                )
            if getattr(objective, "region_key", None):
                rows.append(
                    row(
                        "區域",
                        str(objective.region_key),
                        mono=True,
                        link_to=authored_link("wilderness_regions", objective.region_key),
                    )
                )
        return ledger(rows)

    def targets() -> dict[str, Any]:
        rows = []
        for identity_value in record.objective_target_ids:
            rows.append(
                table_row({"target": _entity_link_cell(identity_value)}, key=f"objective:{identity_value}")
            )
        for identity_value in record.protected_entity_ids:
            rows.append(
                table_row(
                    {"target": _entity_link_cell(identity_value), "role": {"value": "受保護", "tone": "gold"}},
                    key=f"protected:{identity_value}",
                )
            )
        return table(
            [column("target", "目標", mono=True), column("role", "性質")],
            rows,
            empty_note="此任務目前沒有綁定目標。",
        )

    def rewards() -> dict[str, Any]:
        rows = _reward_rows(record)
        if not rows:
            return empty("找不到此任務的發布紀錄，無法顯示獎勵。")
        return ledger(rows)

    def stage_room() -> dict[str, Any]:
        if record.stage_room_id is None:
            return empty("此任務沒有綁定房間。")
        return ledger([row("目標房間", f"#{record.stage_room_id}", mono=True, link_to=link("rooms", record.stage_room_id))])

    def payload() -> dict[str, Any]:
        stored = _payload_for(record)
        if stored is None:
            return empty("這不是生成任務，或找不到其保存的內容。")
        return tree(stored)

    return {
        "id": record.quest_id,
        "kind": KIND,
        "label": f"{record.quest_id}",
        "dbref": None,
        "typeclass": "",
        "owner_dbref": dbref_of(owner),
        "sections": compute_sections(
            [
                ("identity", "任務紀錄", identity),
                ("definition", "定義", definition),
                ("targets", "綁定目標", targets),
                ("stage_room", "目標房間", stage_room),
                ("rewards", "獎勵", rewards),
                ("payload", "生成內容", payload),
            ]
        ),
    }


def item_of(record: Any, owner: Any) -> dict[str, Any]:
    """One quest list row (summary fields only)."""
    return {
        "id": record.quest_id,
        "kind": KIND,
        "dbref": None,
        "label": record.quest_id,
        "fields": [
            row(
                "定義鍵",
                record.definition_key,
                mono=True,
                link_to=authored_link("quest_definitions", record.definition_key),
            ),
            row("狀態", STATE_LABELS.get(str(record.state.value), str(record.state))),
            row("階段", f"{record.stage_index} / {record.stage_progress}", mono=True),
            row("擁有角色", f"#{dbref_of(owner)}", mono=True),
        ],
    }


def generated_item_of(payload: dict, index: int) -> dict[str, Any]:
    stored = mapping_values(payload) or {}
    definition = mapping_values(stored.get("definition")) or {}
    issuance = mapping_values(stored.get("issuance")) or {}
    definition_key = definition.get("key") or definition.get("display_name") or "—"
    issuer_key = issuance.get("issuer_key") or "—"
    name = definition.get("name") or definition.get("display_name")
    return {
        "id": f"generated:{index}",
        "kind": KIND,
        "dbref": None,
        "label": str(name or definition_key),
        "fields": [
            row("定義鍵", str(definition_key), mono=True),
            row("發布識別", str(issuer_key), mono=True),
            row("來源", "生成任務"),
        ],
    }


def generated_detail(payload: dict) -> dict[str, Any]:
    stored = mapping_values(payload) or {}
    definition = mapping_values(stored.get("definition")) or {}
    issuance = mapping_values(stored.get("issuance")) or {}
    name = definition.get("name") or definition.get("display_name")
    definition_key = definition.get("key") or name or "—"
    issuer_key = issuance.get("issuer_key") or "—"

    def identity() -> dict[str, Any]:
        return ledger(
            [
                row("名稱", str(name or definition_key)),
                row("定義鍵", str(definition_key), mono=True),
                row("發布識別", str(issuer_key), mono=True),
                row("來源", "生成任務", mono=True),
            ]
        )

    def reward() -> dict[str, Any]:
        reward = mapping_values(issuance.get("reward"))
        if reward is None:
            return empty("此生成任務沒有獎勵紀錄。")
        items = [entry for entry in (sequence_values(reward.get("items")) or [])]
        return ledger(
            [
                row("結算方式", str(issuance.get("settlement", "—")), mono=True),
                row("銅幣", reward.get("copper", 0), mono=True),
                row("功績", reward.get("merit", 0), mono=True),
                row(
                    "物品",
                    "、".join(
                        f"{characters.item_label(item.get('item_key'))} × {item.get('quantity')}"
                        for item in items
                        if mapping_values(item) is not None
                    )
                    or "—",
                ),
            ]
        )

    def requirements() -> dict[str, Any]:
        return tree(stored.get("requirements") or [])

    def raw() -> dict[str, Any]:
        return tree(stored)

    return {
        "id": str(definition_key),
        "kind": KIND,
        "label": str(name or definition_key),
        "dbref": None,
        "typeclass": "",
        "sections": compute_sections(
            [
                ("identity", "生成任務", identity),
                ("rewards", "獎勵", reward),
                ("requirements", "生成需求", requirements),
                ("payload", "保存內容", raw),
            ]
        ),
    }


__all__ = [
    "KIND",
    "STATE_LABELS",
    "detail_for_record",
    "generated_detail",
    "generated_item_of",
    "generated_payloads",
    "item_of",
    "owner_records",
    "resolve_owner",
]
