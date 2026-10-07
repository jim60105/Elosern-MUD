"""Monster inspection reader (S3 §4 "Monster").

Identity, provenance and placement are read back through the owning modules:
``world.rules.monster_individual`` resolves the variant, derived threat tier and
danger grade, ``world.rules.traits`` names the numeric source that built the
individual's traits, and ``world.lore.monster_placement`` names the owning site
or ambient region. Loot and behaviour come from the monster's own stored state
and the behaviour rulebook, both read without provisioning anything.
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
    typeclass_of,
)
from web.gm.readers._sections import (
    SectionError,
    chip,
    chips,
    column,
    compute_sections,
    empty,
    ledger,
    link,
    row,
    table,
    table_row,
)

KIND = "monsters"

#: Operator-facing names for the numeric sources a monster may be built from.
NUMERIC_SOURCE_LABELS = {
    "approved_profile": "已核可數值檔",
    "interim_tier_band": "暫定階級區間",
    "tier_band": "階級區間（無數值檔）",
}


def _species_label(key: Any) -> str | None:
    if not isinstance(key, str) or not key:
        return None
    from world.lore.monster_species import MONSTER_SPECIES_REGISTRY

    species = MONSTER_SPECIES_REGISTRY.get(key)
    return str(getattr(species, "display_name_zh", None) or key)


def _variant(key: Any) -> Any | None:
    if not isinstance(key, str) or not key:
        return None
    from world.lore.monster_species import MONSTER_VARIANT_REGISTRY

    return MONSTER_VARIANT_REGISTRY.get(key)


def region_of(monster: Any) -> str | None:
    """The region this individual stands in: its site's, or its ambient rule's."""
    from world.lore.monster_placement import (
        AMBIENT_PLACEMENT_REGISTRY,
        MONSTER_SITE_REGISTRY,
    )

    site_key = read_attr(monster, "site_key", default=None)
    if isinstance(site_key, str) and site_key:
        site = MONSTER_SITE_REGISTRY.get(site_key)
        if site is not None:
            return str(site.region_key)
    variant_key = read_attr(monster, "variant_key", default=None)
    if isinstance(variant_key, str) and variant_key:
        for rule in AMBIENT_PLACEMENT_REGISTRY.values():
            if variant_key in tuple(rule.variant_keys):
                return str(rule.region_key)
    return None


def numeric_source(monster: Any) -> tuple[str, Any | None]:
    """The numeric source that built this individual's traits.

    A species-backed individual is resolved through the owning rule
    (``initial_trait_config_for_variant`` returns the source it would use); a
    tier-only individual carries no approved profile, so its source is the
    plain tier band.
    """
    from world.rules.monster_individual import resolve_individual_tier
    from world.rules.traits import initial_trait_config_for_variant

    species_key = read_attr(monster, "species_key", default=None)
    variant_key = read_attr(monster, "variant_key", default=None)
    variant = _variant(variant_key)
    if species_key is None or variant is None:
        return "tier_band", None
    _config, source = initial_trait_config_for_variant(variant, "floor")
    return str(source), variant


def identity_section(monster: Any) -> dict[str, Any]:
    from world.rules.monster_individual import individual_danger_grade, resolve_individual_tier

    species_key = read_attr(monster, "species_key", default=None)
    variant_key = read_attr(monster, "variant_key", default=None)
    stored_tier = read_attr(monster, "threat_tier", default=None)
    tier = resolve_individual_tier(monster, stored_tier)
    rows = [
        row("名稱", label_of(monster)),
        row("識別碼", f"#{dbref_of(monster)}", mono=True),
        row("型別", typeclass_of(monster), mono=True),
        row("物種", _species_label(species_key) or "（未設定）"),
        row("變體", _variant(variant_key).display_name_zh if _variant(variant_key) else "（未設定）"),
        row("威脅階級", str(tier) if tier else "—", mono=True),
        row("危險等級", individual_danger_grade(monster) or "—", mono=True),
    ]
    source, _variant_row = numeric_source(monster)
    rows.append(row("數值來源", NUMERIC_SOURCE_LABELS.get(source, source), mono=True))
    return ledger(rows)


def numeric_section(monster: Any) -> dict[str, Any]:
    source, variant = numeric_source(monster)
    rows = [row("來源", NUMERIC_SOURCE_LABELS.get(source, source), tone="gold" if source != "approved_profile" else "ok")]
    profile = getattr(variant, "combat_profile", None) if variant is not None else None
    if profile is not None:
        rows.append(
            row(
                "已核可數值",
                "、".join(
                    f"{name}={getattr(profile, name)}"
                    for name in ("hp", "mp", "sp", "atk_phys", "agility", "defense", "magic_power")
                ),
                mono=True,
            )
        )
    else:
        rows.append(row("已核可數值", "此個體沒有已核可的完整數值檔", mono=True))
    return ledger(rows)


def placement_section(monster: Any) -> dict[str, Any]:
    site_key = read_attr(monster, "site_key", default=None)
    rows: list[dict[str, Any]] = []
    if isinstance(site_key, str) and site_key:
        from world.lore.monster_placement import MONSTER_SITE_REGISTRY

        site = MONSTER_SITE_REGISTRY.get(site_key)
        rows.append(row("歸屬", "據點", tone="gold"))
        rows.append(row("據點", site_key, mono=True))
        if site is not None:
            rows.append(row("據點類型", str(site.kind), mono=True))
            rows.append(row("區域", str(site.region_key), mono=True))
            rows.append(row("座標", f"{site.coordinates[0]}, {site.coordinates[1]}", mono=True))
    else:
        rows.append(row("歸屬", "環境散布", tone="gold"))
        rows.append(row("區域", str(region_of(monster) or "—"), mono=True))
    location = getattr(monster, "location", None)
    if location is not None:
        rows.append(
            row(
                "所在房間",
                f"#{dbref_of(location)}",
                mono=True,
                link_to=link("rooms", dbref_of(location), label_of(location)),
            )
        )
    return ledger(rows)


def loot_section(monster: Any) -> dict[str, Any]:
    stored = read_attr(monster, "loot_table", default=None)
    entries = sequence_values(stored) or []
    rows = []
    for index, entry in enumerate(entries):
        if isinstance(entry, str):
            item_key, quantity, chance = entry, 1, None
        else:
            entry_map = mapping_values(entry)
            if entry_map is not None:
                item_key = entry_map.get("item_key") or entry_map.get("key") or "—"
                quantity = entry_map.get("quantity", 1)
                chance = entry_map.get("chance")
            else:
                item_key, quantity, chance = str(entry), 1, None
        rows.append(
            table_row(
                {
                    "item": {"value": characters.item_label(item_key)},
                    "key": {"value": str(item_key), "mono": True},
                    "quantity": {"value": quantity, "mono": True},
                    "chance": {"value": chance if chance is not None else "—", "mono": True},
                },
                key=f"{index}:{item_key}",
            )
        )
    return table(
        [
            column("item", "掉落物"),
            column("key", "物品鍵", mono=True),
            column("quantity", "數量", mono=True),
            column("chance", "機率", mono=True),
        ],
        rows,
        empty_note="此魔物目前沒有掉落表。",
    )


def behaviour_section(monster: Any) -> dict[str, Any]:
    from world.rules.monster_behaviour import read_behaviour_profile

    profile = read_behaviour_profile(monster)
    stored_key = read_attr(monster, "behaviour_tree", default=None)
    rows = [
        row("行為鍵", str(stored_key) if stored_key else "（使用階級預設）", mono=True),
        row("目標策略", str(profile.target_strategy), mono=True),
        row("技能選擇", str(profile.skill_choice), mono=True),
        row("多敵優先群體技", "是" if profile.prefer_area_when_multiple_enemies else "否"),
        row("逃跑生命比例", profile.flee_hp_fraction if profile.flee_hp_fraction is not None else "—", mono=True),
    ]
    return ledger(rows)


def detail(monster: Any) -> dict[str, Any]:
    sections = compute_sections(
        [
            ("identity", "身分", lambda: identity_section(monster)),
            ("numeric", "數值來源", lambda: numeric_section(monster)),
            ("placement", "配置", lambda: placement_section(monster)),
            ("loot", "掉落表", lambda: loot_section(monster)),
            ("behaviour", "行為設定", lambda: behaviour_section(monster)),
        ]
    )
    sections.extend(
        compute_sections(
            [
                ("resources", "資源", lambda: characters.resources_section(monster)),
                ("conditions", "狀態與增益", lambda: characters.conditions_section(monster)),
                ("traits", "屬性", lambda: characters.traits_section(monster)),
            ]
        )
    )
    dbref = dbref_of(monster)
    sections.append(
        {
            "key": "links",
            "title": "相關連結",
            **chips(
                [
                    chip(
                        "所在房間",
                        key="room",
                        link_to=link("rooms", dbref_of(monster.location), label_of(monster.location)),
                    )
                    if monster.location is not None
                    else chip("無所在房間", key="room")
                ]
            ),
        }
    )
    return {
        "id": str(dbref),
        "kind": KIND,
        "label": label_of(monster),
        "dbref": dbref,
        "typeclass": typeclass_of(monster),
        "sections": sections,
    }


def item_of(monster: Any) -> dict[str, Any]:
    """One monster list row (summary fields only)."""
    from world.rules.monster_individual import resolve_individual_tier

    dbref = dbref_of(monster)
    species_key = read_attr(monster, "species_key", default=None)
    variant_key = read_attr(monster, "variant_key", default=None)
    tier = resolve_individual_tier(monster, read_attr(monster, "threat_tier", default=None))
    source, _variant_row = numeric_source(monster)
    return {
        "id": str(dbref),
        "kind": KIND,
        "dbref": dbref,
        "label": label_of(monster),
        "fields": [
            row("物種", _species_label(species_key) or "（未設定）"),
            row("變體", str(variant_key) if variant_key else "（未設定）", mono=True),
            row("威脅階級", str(tier) if tier else "—", mono=True),
            row("數值來源", NUMERIC_SOURCE_LABELS.get(source, source)),
        ],
    }


__all__ = ["KIND", "NUMERIC_SOURCE_LABELS", "detail", "item_of", "numeric_source"]
