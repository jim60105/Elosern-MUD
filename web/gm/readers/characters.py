"""Curated character projection, shared by player characters and NPCs.

The reader never recomputes rules: traits, gauges, conditions, disguise,
breakdowns, wallet, guild merit, titles, skills and lineage all come from the
authoritative read models (`world/rules/status_query/`,
`displayed_stats`/`title_view`/`lineage_query`), so the numbers an operator
sees here match what the game shows. Every section is computed independently,
so one corrupt source leaves the remaining panels readable (design §1/§7).
"""

from __future__ import annotations

from typing import Any

from web.gm.readers._entities import (
    dbref_of,
    label_of,
    mapping_values,
    read_attr,
    sequence_values,
    typeclass_of,
)
from web.gm.readers._sections import (
    cell,
    chip,
    chips,
    column,
    compute_sections,
    empty,
    group,
    groups,
    ledger,
    link,
    list_summary,
    row,
    table,
    table_row,
    tile,
    tiles,
)
from web.gm.readers.world import authored_link

#: The affinity projection's row ceiling (the title-codex precedent: the
#: counters still describe the full set, only the rendered rows are bounded).
MAX_AFFINITY_ROWS = 50

#: Presentation labels for the player-facing currency units.
UNIT_GOLD = "金"
UNIT_SILVER = "銀"
UNIT_COPPER = "銅"


def money_display(copper: int) -> str:
    """The derived gold/silver/copper reading of an integer copper wallet."""
    from world.lore.economy import COPPER_PER_GOLD, COPPER_PER_SILVER

    gold, rest = divmod(int(copper), COPPER_PER_GOLD)
    silver, copper_left = divmod(rest, COPPER_PER_SILVER)
    return f"{UNIT_GOLD} {gold}、{UNIT_SILVER} {silver}、{UNIT_COPPER} {copper_left}"


def item_label(key: Any) -> str:
    """The item registry's display name, falling back to the stored key."""
    from world.lore.items import ITEM_REGISTRY

    text = str(key)
    definition = ITEM_REGISTRY.get(text)
    if definition is None:
        return text
    return str(getattr(definition, "display_name_zh", None) or text)


def _registry_label(registry: Any, key: Any) -> str | None:
    if not isinstance(key, str) or not key:
        return None
    entry = registry.get(key) if hasattr(registry, "get") else None
    if entry is None:
        return key
    return str(getattr(entry, "display_name_zh", None) or key)


def _entity_row(label: str, entity: Any, kind: str) -> dict[str, Any]:
    dbref = dbref_of(entity)
    return row(
        label,
        f"#{dbref}",
        mono=True,
        link_to=link(kind, dbref, label_of(entity)),
    )


# --- sections ---------------------------------------------------------------


def identity_section(entity: Any) -> dict[str, Any]:
    from world.lore.races import RACE_REGISTRY, SUBRACE_REGISTRY

    rows = [
        row("名稱", label_of(entity)),
        row("識別碼", f"#{dbref_of(entity)}", mono=True),
        row("型別", typeclass_of(entity), mono=True),
    ]
    race_key = read_attr(entity, "race", default=None)
    if race_key:
        rows.append(
            row(
                "種族",
                _registry_label(RACE_REGISTRY, race_key) or str(race_key),
                link_to=authored_link("races", race_key),
            )
        )
    subrace_key = read_attr(entity, "subrace", default=None)
    if subrace_key:
        rows.append(
            row(
                "亞種",
                _registry_label(SUBRACE_REGISTRY, subrace_key) or str(subrace_key),
                link_to=authored_link("subraces", subrace_key),
            )
        )
    sex = read_attr(entity, "sex", default=None)
    if sex:
        rows.append(row("性別", str(sex)))
    age = read_attr(entity, "age", default=None)
    if age is not None:
        rows.append(row("年齡", age, mono=True))
    apparent = read_attr(entity, "apparent_age", default=None)
    if apparent is not None:
        rows.append(row("外觀年齡", apparent, mono=True))
    location = getattr(entity, "location", None)
    if location is not None:
        rows.append(_entity_row("當前房間", location, "rooms"))
    return ledger(rows)


def resources_section(entity: Any) -> dict[str, Any]:
    from world.rules.status_query import TRAIT_LABELS, build_status_read_model

    model = build_status_read_model(entity)
    gauges = [
        tile(
            TRAIT_LABELS.get(key, key),
            gauge.current,
            key=key,
            unit=f"/ {gauge.maximum}",
        )
        for key, gauge in model.resources.items()
    ]
    if not gauges:
        return empty("沒有可顯示的資源條。")
    return tiles(gauges, note=model.full_title or None)


def conditions_section(entity: Any) -> dict[str, Any]:
    from world.rules.status_query import build_status_read_model

    model = build_status_read_model(entity)
    rows = []
    for condition in model.conditions:
        rows.append(
            table_row(
                {
                    "code": cell(condition.code, mono=True),
                    "label": cell(condition.label),
                    "severity": cell(condition.severity, tone=condition.severity),
                    "remaining": cell(
                        condition.remaining_seconds
                        if condition.remaining_seconds is not None
                        else "—",
                        mono=True,
                    ),
                    "modifiers": cell("、".join(sorted(condition.modifiers)) or "—", mono=True),
                },
                key=condition.code,
            )
        )
    return table(
        [
            column("code", "代碼", mono=True),
            column("label", "名稱"),
            column("severity", "嚴重度"),
            column("remaining", "剩餘秒數", mono=True),
            column("modifiers", "修正", mono=True),
        ],
        rows,
        empty_note="目前沒有作用中的狀態或增益。",
    )


def traits_section(entity: Any) -> dict[str, Any]:
    from world.rules.status_query import TRAIT_LABELS, build_character_read_model

    model = build_character_read_model(entity)
    rows = []
    for trait in model.traits:
        value: Any = trait.current
        if trait.maximum is not None:
            value = f"{trait.current} / {trait.maximum}"
        rows.append(
            row(TRAIT_LABELS.get(trait.key, trait.key), value, key=trait.key, mono=True)
        )
    return ledger(rows)


def disguise_section(entity: Any) -> dict[str, Any]:
    from world.rules.status_query import TRAIT_LABELS, build_character_read_model

    model = build_character_read_model(entity)
    if not model.disguise_displayed:
        return ledger([], note="此角色目前沒有偽裝數值。")
    rows = [
        row(TRAIT_LABELS.get(key, key), value, key=key, mono=True)
        for key, value in model.disguise_displayed
    ]
    return ledger(rows, note="僅顯示用：偽裝數值永不取代真實屬性。")


def breakdown_section(entity: Any) -> dict[str, Any]:
    from world.rules.status_query import TRAIT_LABELS, build_character_read_model

    model = build_character_read_model(entity)
    items = []
    for entry in model.breakdown:
        rows = [row("基礎", entry.base, mono=True)]
        for layer in entry.layers:
            amount = layer.amount
            if layer.kind == "mult":
                amount = f"×{amount}"
            elif layer.kind == "pct":
                amount = f"{amount:+d}%"
            else:
                amount = f"{amount:+}"
            rows.append(
                row(
                    f"{layer.name}（{layer.source}）",
                    amount,
                    key=f"{entry.key}:{layer.source}:{layer.name}",
                    mono=True,
                )
            )
        items.append(
            group(
                TRAIT_LABELS.get(entry.key, entry.key),
                rows,
                key=entry.key,
                note=f"有效值 {entry.effective}",
            )
        )
    if not items:
        return empty("沒有可顯示的屬性組成。")
    return groups(items, note="基礎 → 技能 → 裝備 → 狀態，逐層重建。")


def skills_section(entity: Any) -> dict[str, Any]:
    from world.rules.status_query import build_character_read_model, group_skill_keys

    model = build_character_read_model(entity)
    items = []
    for group_view in group_skill_keys(model.active_keys):
        rows = []
        for sub in group_view.groups:
            for skill in sub.skills:
                rows.append(
                    row(
                        skill.label,
                        skill.key,
                        key=skill.key,
                        mono=True,
                        tone=None,
                    )
                )
        items.append(group(group_view.label, rows, key=group_view.category))
    if model.passive_keys:
        items.append(
            group(
                "被動",
                [row(item_label(key), key, key=key, mono=True) for key in model.passive_keys],
                key="passive",
            )
        )
    if not items:
        return empty("此角色目前沒有技能。")
    return groups(items)


def lineage_section(entity: Any) -> dict[str, Any]:
    from world.rules.lineage_query import build_lineage_view

    view = build_lineage_view(entity)
    items = []
    for chain in view.chains:
        rows = [
            row(
                node.display_name_zh,
                f"Lv.{node.level}" + ("（已滿）" if node.capped else ""),
                key=node.skill_key,
                mono=True,
                tone="ok" if node.owned else None,
            )
            for node in chain.nodes
        ]
        items.append(
            group(
                chain.element_or_style_zh,
                rows,
                key=chain.root_skill_key,
                note=("已消耗" if chain.consumed else "") or None,
            )
        )
    if not items:
        return empty("此角色目前沒有技能系譜。")
    return groups(items, note=f"完成 {view.completed_count} / {view.total_count}")


def equipment_section(entity: Any) -> dict[str, Any]:
    from world.rules.status_query import build_character_read_model

    model = build_character_read_model(entity)
    rows = [
        table_row(
            {
                "slot": cell(entry.slot, mono=True),
                "item": cell(item_label(entry.item_key)),
                "key": cell(entry.item_key, mono=True),
            },
            key=entry.slot,
        )
        for entry in model.equipment
    ]
    return table(
        [column("slot", "部位", mono=True), column("item", "物品"), column("key", "物品鍵", mono=True)],
        rows,
        empty_note="此角色目前沒有裝備。",
    )


def inventory_section(entity: Any) -> dict[str, Any]:
    stored = read_attr(entity, "inventory", default=None)
    counts: dict[str, int] = {}
    entries = sequence_values(stored)
    if entries is not None:
        for key in entries:
            if isinstance(key, str) and key:
                counts[key] = counts.get(key, 0) + 1
    else:
        stored_map = mapping_values(stored)
        for key, value in (stored_map or {}).items():
            if isinstance(key, str) and key and isinstance(value, int) and not isinstance(value, bool):
                counts[key] = value
    rows = [
        table_row(
            {
                "item": cell(item_label(key)),
                "key": cell(key, mono=True),
                "quantity": cell(count, mono=True),
            },
            key=key,
        )
        for key, count in sorted(counts.items())
    ]
    return table(
        [column("item", "物品"), column("key", "物品鍵", mono=True), column("quantity", "數量", mono=True)],
        rows,
        empty_note="此角色目前沒有物品。",
    )


def wallet_section(entity: Any) -> dict[str, Any]:
    from world.rules.status_query import build_character_read_model

    model = build_character_read_model(entity)
    return ledger(
        [
            row("銅幣（整數）", model.wallet, mono=True),
            row("換算", money_display(model.wallet), mono=True),
        ]
    )


def guild_section(entity: Any) -> dict[str, Any]:
    from world.rules.status_query import build_character_read_model

    model = build_character_read_model(entity)
    rows = [row("階級", model.guild_rank or "—", mono=True), row("功績", model.guild_merit, mono=True)]
    return ledger(rows)


def titles_section(entity: Any) -> dict[str, Any]:
    from world.rules.title_view import build_title_codex_view

    view = build_title_codex_view(entity)
    items = []
    if view.full_title:
        items.append(group("目前全銜", [row("全銜", view.full_title)]))
    fixed = [
        row(
            entry.display,
            "已解鎖" if entry.unlocked else (entry.hint or "未解鎖"),
            key=entry.key,
            tone="ok" if entry.unlocked else None,
        )
        for entry in view.fixed_rows
    ]
    if fixed:
        items.append(group("固定稱號", fixed))
    epithets = [
        row(
            entry.display,
            entry.basis or "—",
            key=f"{entry.display}:{entry.granted_tick}",
            tone="gold" if entry.equipped else None,
        )
        for entry in view.epithet_rows
    ]
    if epithets:
        items.append(group("帶入的稱號", epithets))
    if view.pending_ballot:
        items.append(
            group(
                "待提名",
                [row(str(entry.get("display", key)), str(key), key=str(key)) for key, entry in enumerate(view.pending_ballot)],
            )
        )
    if not items:
        return empty("此角色目前沒有稱號。")
    return groups(items, note=f"已解鎖 {view.unlocked} / {view.total}")


def affinity_section(entity: Any) -> dict[str, Any]:
    """Every NPC's affinity toward this player character (read-only)."""
    from world.rules.affinity import RelationHandler
    from typeclasses.npcs import NPC

    rows: list[dict[str, Any]] = []
    total = 0
    for npc in NPC.objects.all_family().order_by("id"):
        handler = RelationHandler(npc)
        if not handler.has_record(entity):
            continue
        total += 1
        if len(rows) >= MAX_AFFINITY_ROWS:
            continue
        rows.append(
            table_row(
                {
                    "npc": cell(
                        f"#{npc.pk}",
                        mono=True,
                        link_to=link("npcs", npc.pk, npc.key),
                    ),
                    "name": cell(label_of(npc)),
                    "value": cell(handler.affinity_for(entity), mono=True),
                    "cap": cell(handler.cap_for(entity), mono=True),
                    "stage": cell(handler.stage_for(entity), mono=True),
                },
                key=str(npc.pk),
            )
        )
    note = None
    if total > len(rows):
        note = f"僅顯示前 {len(rows)} 筆（共 {total} 筆）。"
    return table(
        [
            column("npc", "NPC", mono=True),
            column("name", "名稱"),
            column("value", "好感度", mono=True),
            column("cap", "上限", mono=True),
            column("stage", "階段", mono=True),
        ],
        rows,
        note=note,
        empty_note="目前沒有 NPC 對這位角色留下好感度紀錄。",
    )


def party_section(entity: Any) -> dict[str, Any]:
    from world.rules.party import live_companions

    rows = []
    for companion in live_companions(entity):
        dbref = dbref_of(companion)
        rows.append(
            table_row(
                {
                    "npc": cell(
                        f"#{dbref}",
                        mono=True,
                        link_to=link("npcs", dbref, label_of(companion)),
                    ),
                    "name": cell(label_of(companion)),
                    "location": cell(label_of(companion.location) if companion.location else "—"),
                },
                key=str(dbref),
            )
        )
    return table(
        [column("npc", "同伴", mono=True), column("name", "名稱"), column("location", "所在位置")],
        rows,
        empty_note="目前沒有隊伍成員。",
    )


def possession_section(entity: Any) -> dict[str, Any]:
    from world.rules.possession import current_possession

    mapping = current_possession(entity)
    if mapping is None:
        return ledger([row("狀態", "未附身")])
    holder = (mapping_values(mapping) or {}).get("npc_id")
    rows = [row("狀態", "附身中", tone="gold")]
    if holder is not None:
        from evennia.objects.models import ObjectDB

        target = ObjectDB.objects.filter(pk=int(holder)).first() if str(holder).isdigit() else None
        if target is not None:
            rows.append(_entity_row("對象", target, "npcs"))
        else:
            rows.append(row("對象", f"#{holder}", mono=True))
    return ledger(rows)


def sexual_section(entity: Any) -> dict[str, Any]:
    from world.rules.status_query import build_character_read_model

    model = build_character_read_model(entity)
    intimate = model.intimate
    if intimate is None:
        return empty("目前沒有可顯示的情慾狀態。")
    return ledger(
        [
            row("興奮", intimate.arousal, mono=True),
            row("濕潤", intimate.wetness, mono=True),
            row("羞恥", intimate.shame, mono=True),
            row("暴露", intimate.exposure, mono=True),
            row("高潮階段", intimate.climax_phase, mono=True),
            row("今日高潮次數", intimate.climax_today, mono=True),
        ]
    )


def links_section(entity: Any, extra: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Every relationship identifier as a link (design §3)."""
    from world.rules.party import live_companions

    entries: list[dict[str, Any]] = []
    location = getattr(entity, "location", None)
    if location is not None:
        entries.append(
            chip(label_of(location), key="room", link_to=link("rooms", dbref_of(location), label_of(location)))
        )
    for companion in live_companions(entity):
        dbref = dbref_of(companion)
        entries.append(
            chip(label_of(companion), key=f"party:{dbref}", link_to=link("npcs", dbref, label_of(companion)))
        )
    dbref = dbref_of(entity)
    entries.append(chip("任務紀錄", key="quests", link_to=link("quests", f"owner:{dbref}", label_of(entity))))
    entries.append(chip("記憶", key="memories", link_to=link("memories", f"owner:{dbref}", label_of(entity))))
    entries.append(chip("對話", key="dialogue", link_to=link("dialogue", dbref, label_of(entity))))
    entries.extend(extra or [])
    return chips(entries)


def character_sections(entity: Any) -> list[dict[str, Any]]:
    """The shared curated character sections, each computed independently."""
    return compute_sections(
        [
            ("identity", "身分", lambda: identity_section(entity)),
            ("resources", "資源", lambda: resources_section(entity)),
            ("conditions", "狀態與增益", lambda: conditions_section(entity)),
            ("traits", "屬性", lambda: traits_section(entity)),
            ("disguise", "偽裝數值（僅顯示用）", lambda: disguise_section(entity)),
            ("breakdown", "屬性組成", lambda: breakdown_section(entity)),
            ("skills", "技能", lambda: skills_section(entity)),
            ("lineage", "技能系譜", lambda: lineage_section(entity)),
            ("equipment", "裝備", lambda: equipment_section(entity)),
            ("inventory", "物品欄", lambda: inventory_section(entity)),
            ("wallet", "錢包", lambda: wallet_section(entity)),
            ("guild", "公會", lambda: guild_section(entity)),
            ("titles", "稱號", lambda: titles_section(entity)),
            ("affinity", "好感度", lambda: affinity_section(entity)),
            ("party", "隊伍", lambda: party_section(entity)),
            ("possession", "附身", lambda: possession_section(entity)),
            ("sexual", "情慾狀態", lambda: sexual_section(entity)),
            ("links", "相關連結", lambda: links_section(entity)),
        ]
    )


def character_list_item(entity: Any) -> dict[str, Any]:
    """One player-character list row (summary fields only)."""
    from world.lore.races import RACE_REGISTRY

    dbref = dbref_of(entity)
    pending = read_attr(entity, "creation_pending", default=False)
    return {
        "id": str(dbref),
        "kind": "characters",
        "dbref": dbref,
        "label": label_of(entity),
        "fields": [
            row("待完成建立", "是" if pending else "否"),
            row(
                "種族",
                _registry_label(RACE_REGISTRY, read_attr(entity, "race", default=None)) or "—",
                link_to=authored_link("races", read_attr(entity, "race", default=None)),
            ),
            row("所在位置", label_of(entity.location) if entity.location else "—"),
        ],
    }


def character_detail(entity: Any) -> dict[str, Any]:
    """The complete player-character detail payload."""
    dbref = dbref_of(entity)
    return {
        "id": str(dbref),
        "kind": "characters",
        "label": label_of(entity),
        "dbref": dbref,
        "typeclass": typeclass_of(entity),
        "sections": character_sections(entity),
    }


__all__ = [
    "MAX_AFFINITY_ROWS",
    "breakdown_section",
    "character_detail",
    "character_list_item",
    "character_sections",
    "disguise_section",
    "identity_section",
    "item_label",
    "links_section",
    "money_display",
    "titles_section",
]
