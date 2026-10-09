"""The hand-maintained index of authored registries (gm-portal-s4 §3.2).

``REGISTRY_INDEX`` lists every module-level registry the GM portal browses: a
stable snake_case name, a Traditional Chinese label, one of eight display
groups, a lazy loader returning the loaded ``key -> frozen dataclass`` mapping,
the repository-relative source path, and optional summary fields. The index is
explicit on purpose: a registry missing from it is simply not browsable, and a
contract test keeps every startup-synchronised registry represented.

Loaders import lazily, so importing this module pulls in no rules, skills or
quest package; startup synchronisation (``world/lore/sync.py``) is untouched.
Every loader returns what the server process has loaded (the module-level
registry or the owning package's load cache), never a fresh read of source.

``build_reference_index`` walks every entry for the fields declared with
``world.lore.registry_refs`` and returns the forward and inverse reference
maps. Registries are immutable at runtime, so the result is cached for the
process lifetime. ``check_references`` and ``declaration_errors`` are the CI
integrity contract over shipped data; nothing here runs at startup.
"""

from __future__ import annotations

import dataclasses
import functools
import typing
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from world.lore.registry_refs import RefSpec, ref_spec_of

#: The eight display groups, in navigation order.
GROUPS: tuple[str, ...] = ("世界", "生物", "物品與經濟", "聚落", "人物", "技能", "任務", "規則書")


@dataclass(frozen=True)
class RegistrySpec:
    """One browsable registry."""

    name: str
    label: str
    group: str
    loader: Callable[[], Mapping[str, Any]]
    source_path: str
    #: Field names (dotted for nested dataclasses) shown in entry lists.
    summary_fields: tuple[str, ...] = ()


# --- lazy loaders -------------------------------------------------------------
#
# Each loader imports its owning module on first call and returns a read-only
# view. The lore registries are plain module attributes; the rules-derived ones
# use the owning package's own load seam.


def _attr(module: str, attribute: str) -> Callable[[], Mapping[str, Any]]:
    def load() -> Mapping[str, Any]:
        import importlib

        return MappingProxyType(dict(getattr(importlib.import_module(module), attribute)))

    load.__qualname__ = f"load<{module}.{attribute}>"
    return load


def _quest_definitions() -> Mapping[str, Any]:
    # The authored quest catalog. The process ``QUEST_DEFINITION_REGISTRY`` is
    # filled at startup and also holds runtime-generated quests (runtime state,
    # inspected by S3), so the authored browser reads the catalog itself.
    from world.quests.catalog import QUEST_CATALOG

    return MappingProxyType({definition.key: definition for definition in QUEST_CATALOG})


def _professions() -> Mapping[str, Any]:
    from world.rules.profession_config import all_professions

    return MappingProxyType({profession.key: profession for profession in all_professions()})


def _guild_section(section: str) -> Callable[[], Mapping[str, Any]]:
    """One keyed section of the guild-economy catalog.

    The server loads ``guild_config.CATALOG`` at startup, after quest
    synchronisation; that loaded snapshot is used whenever it exists. Before it
    exists (offline tooling, tests), the section is built with the same
    validators the catalog loader runs, skipping only the quest-reward join that
    needs the startup quest registry.
    """

    def load() -> Mapping[str, Any]:
        from world.rules import guild_config

        catalog = guild_config.CATALOG
        if catalog is not None:
            if section == "shop_configs":
                return MappingProxyType(dict(catalog.shop_configs))
            return MappingProxyType(dict(catalog.host_by_service_id))
        if section == "shop_configs":
            commerce = guild_config.load_commerce_config()
            return MappingProxyType(
                dict(
                    guild_config.validate_shop_configs(
                        commerce["shops"],
                        guild_config.validate_assortment_configs(commerce["assortments"]),
                        guild_config.validate_price_scales(commerce["price_scales"]),
                    )
                )
            )
        return MappingProxyType({row.service_id: row for row in guild_config.validate_service_hosts()})

    load.__qualname__ = f"load<guild_config.{section}>"
    return load


_LORE = "world/lore"
_RULEBOOK = "world/rules/rulebook"


def _spec(
    name: str,
    label: str,
    group: str,
    loader: Callable[[], Mapping[str, Any]],
    source_path: str,
    *summary_fields: str,
) -> RegistrySpec:
    return RegistrySpec(name, label, group, loader, source_path, tuple(summary_fields))


REGISTRY_INDEX: tuple[RegistrySpec, ...] = (
    # 世界
    _spec("races", "種族", "世界", _attr("world.lore.races", "RACE_REGISTRY"), f"{_LORE}/races.py", "display_name_zh"),
    _spec("subraces", "亞種", "世界", _attr("world.lore.races", "SUBRACE_REGISTRY"), f"{_LORE}/races.py", "display_name_zh", "race_key"),
    _spec("static_tiers", "靜態階級", "世界", _attr("world.lore.races", "STATIC_TIER_REGISTRY"), f"{_LORE}/races.py", "display_name_zh", "race_key"),
    _spec("elements", "元素", "世界", _attr("world.lore.elements", "ELEMENT_REGISTRY"), f"{_LORE}/elements.py", "display_name_zh"),
    _spec("magic_tiers", "魔法階級", "世界", _attr("world.lore.magic", "MAGIC_TIER_REGISTRY"), f"{_LORE}/magic.py", "display_name_zh"),
    _spec("nations", "國家", "世界", _attr("world.lore.nations", "NATION_REGISTRY"), f"{_LORE}/nations.py", "display_name_zh", "capital_anchor_key"),
    _spec("anchors", "錨點", "世界", _attr("world.lore.anchors", "ANCHOR_REGISTRY"), f"{_LORE}/anchors.py", "display_name_zh", "kind"),
    _spec("anchor_placements", "錨點配置", "世界", _attr("world.lore.anchor_placement", "ANCHOR_PLACEMENT_REGISTRY"), f"{_LORE}/anchor_placement.py", "zcoord", "entrance_xy"),
    _spec("wilderness_regions", "野外區域", "世界", _attr("world.lore.wilderness_regions", "WILDERNESS_REGION_REGISTRY"), f"{_LORE}/wilderness_regions.py", "display_name_zh", "nation_key"),
    _spec("wilderness_entries", "野外入口", "世界", _attr("world.lore.wilderness_entry", "WILDERNESS_ENTRY_REGISTRY"), f"{_LORE}/wilderness_entry.py", "origin_xy"),
    _spec("scene_archetypes", "場景原型", "世界", _attr("world.lore.scene_archetypes", "SCENE_ARCHETYPE_REGISTRY"), f"{_LORE}/scene_archetypes.py", "display_name_zh"),
    _spec("name_packs", "命名套組", "世界", _attr("world.lore.names", "NAME_PACK_REGISTRY"), f"{_LORE}/names.py", "race_key"),
    _spec("titles", "固定稱號", "世界", _attr("world.lore.titles", "FIXED_TITLE_REGISTRY"), f"{_LORE}/titles.py", "display_name_zh", "category"),
    # 生物
    _spec("monster_tiers", "魔物階級", "生物", _attr("world.lore.monsters", "MONSTER_TIER_REGISTRY"), f"{_LORE}/monsters.py", "display_name_zh"),
    _spec("monster_species", "魔物物種", "生物", _attr("world.lore.monster_species", "MONSTER_SPECIES_REGISTRY"), f"{_LORE}/monster_species.py", "display_name_zh", "default_variant_key"),
    _spec("monster_variants", "魔物變體", "生物", _attr("world.lore.monster_species", "MONSTER_VARIANT_REGISTRY"), f"{_LORE}/monster_species.py", "display_name_zh", "species_key", "threat_tier"),
    _spec("ambient_placements", "環境配置", "生物", _attr("world.lore.monster_placement", "AMBIENT_PLACEMENT_REGISTRY"), f"{_LORE}/monster_placement.py", "region_key", "quantity", "capacity"),
    _spec("monster_sites", "魔物據點", "生物", _attr("world.lore.monster_placement", "MONSTER_SITE_REGISTRY"), f"{_LORE}/monster_placement.py", "kind", "region_key"),
    # 物品與經濟
    _spec("items", "物品", "物品與經濟", _attr("world.lore.items", "ITEM_REGISTRY"), f"{_LORE}/items", "display_name_zh", "price_table_key"),
    _spec("prices", "價格表", "物品與經濟", _attr("world.lore.economy", "PRICE_TABLE"), f"{_LORE}/economy.py", "display_name_zh", "min_copper", "max_copper"),
    _spec("assortments", "商品組合", "物品與經濟", _attr("world.lore.settlements.assortments", "ASSORTMENT_REGISTRY"), f"{_LORE}/settlements/assortments.py", "display_name_zh"),
    _spec("starting_kits", "起始裝備", "物品與經濟", _attr("world.lore.starting_kits", "SUBRACE_STARTING_KIT_REGISTRY"), f"{_LORE}/starting_kits.py", "subrace_key"),
    # 聚落
    _spec("settlements", "聚落", "聚落", _attr("world.lore.settlements.settlements", "SETTLEMENT_REGISTRY"), f"{_LORE}/settlements/settlements.py", "archetype", "zcoord"),
    _spec("places", "場所", "聚落", _attr("world.lore.settlements.places", "PLACE_REGISTRY"), f"{_LORE}/settlements", "room_name_zh", "settlement_key", "kind"),
    _spec("shops", "商店", "聚落", _attr("world.lore.settlements.shops", "SHOP_REGISTRY"), f"{_LORE}/settlements/shops.py", "host_name", "host_title"),
    # 人物
    _spec("npc_profiles", "NPC 人物設定", "人物", _attr("world.lore.npc_profiles", "NPC_PROFILE_REGISTRY"), f"{_LORE}/npc_profiles", "card.identity.public", "apparent_age"),
    _spec("dialogue", "對話表", "人物", _attr("world.lore.dialogue", "DIALOGUE_ROWS"), f"{_LORE}/dialogue", "greeting"),
    _spec("npc_tiers", "NPC 階級", "人物", _attr("world.lore.npc_tiers", "NPC_TIER_REGISTRY"), f"{_LORE}/npc_tiers.py", "display_name_zh", "static_tier_key"),
    _spec("player_presets", "玩家預設角色", "人物", _attr("world.lore.player_presets.assembly", "PLAYER_PRESET_REGISTRY"), f"{_LORE}/player_presets", "display_name", "race", "subrace"),
    _spec("guild_ranks", "公會階級", "人物", _attr("world.lore.guild", "GUILD_RANK_REGISTRY"), f"{_LORE}/guild.py", "order", "title_key"),
    _spec("guild_branches", "公會分部", "人物", _attr("world.lore.guild", "GUILD_BRANCH_REGISTRY"), f"{_LORE}/guild.py", "display_name_zh", "host_name"),
    # 技能
    _spec("skills", "技能", "技能", _attr("world.skills.registry", "SKILL_REGISTRY"), "world/skills/registry", "label", "kind", "category"),
    _spec("sexual_acts", "性行為", "技能", _attr("world.skills.sexual_acts", "SEXUAL_ACT_REGISTRY"), "world/skills/sexual_acts", "base_pleasure", "actor_part", "target_part"),
    # 任務
    _spec("quest_definitions", "任務定義", "任務", _quest_definitions, "world/quests/catalog.py", "display_name", "quest_type", "rank"),
    # 規則書
    _spec("professions", "職業", "規則書", _professions, f"{_RULEBOOK}/professions.yaml", "default_tier", "schedule_template"),
    _spec("shop_configs", "商店營業設定", "規則書", _guild_section("shop_configs"), f"{_RULEBOOK}/commerce", "display_name_zh", "open_hour", "close_hour"),
    _spec("service_hosts", "服務主持人", "規則書", _guild_section("service_hosts"), f"{_LORE}/settlements/places.py", "name", "title", "anchor_room"),
    _spec("monster_behaviour_profiles", "魔物行為設定", "規則書", _attr("world.rules.monster_behaviour", "BEHAVIOUR_PROFILES"), f"{_RULEBOOK}/monster_behaviour.yaml", "target_strategy", "skill_choice"),
)


def spec_by_name(name: str, specs: tuple[RegistrySpec, ...] | None = None) -> RegistrySpec | None:
    for spec in REGISTRY_INDEX if specs is None else specs:
        if spec.name == name:
            return spec
    return None


# --- references -------------------------------------------------------------


@dataclass(frozen=True)
class Reference:
    """One declared reference found in one entry."""

    registry: str
    key: str
    field_path: str
    target_registry: str
    target_key: Any
    inverse: str


@dataclass(frozen=True)
class Declaration:
    """One reference declaration: the declaring dataclass field."""

    owner: str
    field: str
    target_registry: str
    inverse: str
    many: bool


@dataclass(frozen=True)
class DanglingReference:
    """A declared reference whose target registry has no such key."""

    registry: str
    key: str
    field_path: str
    target_registry: str
    missing_key: Any


@dataclass(frozen=True)
class ReferenceIndex:
    """Forward and inverse reference maps over every indexed entry.

    ``forward[(registry, key)]`` lists the entry's references in field order;
    ``inverse[(target_registry, target_key)][inverse_name]`` lists the
    referrers grouped by the declaration's inverse name.
    """

    forward: Mapping[tuple[str, str], tuple[Reference, ...]]
    inverse: Mapping[tuple[str, Any], Mapping[str, tuple[Reference, ...]]]
    declarations: frozenset[Declaration]


def _sorted_members(value: Any) -> list[Any]:
    """A deterministic order for an unordered collection (matches the GM JSON)."""
    return sorted(value, key=lambda item: (type(item).__name__, str(item)))


def _owner_name(instance: Any) -> str:
    cls = type(instance)
    return f"{cls.__module__}.{cls.__qualname__}"


def _walk(
    value: Any, path: str, found: list[tuple[str, RefSpec, Any]], declared: set[Declaration]
) -> None:
    """Collect ``(field_path, spec, key)`` for every declared reference in ``value``."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        for field in dataclasses.fields(value):
            child = getattr(value, field.name)
            child_path = f"{path}.{field.name}" if path else field.name
            spec = ref_spec_of(field)
            if spec is None:
                _walk(child, child_path, found, declared)
                continue
            declared.add(
                Declaration(_owner_name(value), field.name, spec.registry, spec.inverse, spec.many)
            )
            if spec.many:
                members = _sorted_members(child) if isinstance(child, (set, frozenset)) else list(child or ())
                for index, member in enumerate(members):
                    found.append((f"{child_path}[{index}]", spec, member))
            elif child is None and spec.nullable:
                continue
            else:
                found.append((child_path, spec, child))
        return
    if isinstance(value, Mapping):
        for key, child in value.items():
            _walk(child, f"{path}.{key}" if path else str(key), found, declared)
        return
    if isinstance(value, (set, frozenset)):
        value = _sorted_members(value)
    if isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _walk(child, f"{path}[{index}]", found, declared)


def entry_references(entry: Any) -> tuple[list[tuple[str, RefSpec, Any]], set[Declaration]]:
    """Every declared reference of one entry, with the declarations met."""
    found: list[tuple[str, RefSpec, Any]] = []
    declared: set[Declaration] = set()
    _walk(entry, "", found, declared)
    return found, declared


def _hinted_dataclasses(hint: Any) -> Iterator[type]:
    """Every dataclass type named anywhere inside one type hint."""
    if isinstance(hint, type) and dataclasses.is_dataclass(hint):
        yield hint
    for argument in typing.get_args(hint):
        yield from _hinted_dataclasses(argument)


def type_declarations(cls: type, seen: set[type] | None = None) -> set[Declaration]:
    """Every declaration reachable from a dataclass type through its field hints.

    Instances only reveal the declarations their values reach (a nested
    optional dataclass that no shipped entry fills is never walked), so the
    declaration contract also follows the type hints.
    """
    seen = set() if seen is None else seen
    if cls in seen:
        return set()
    seen.add(cls)
    found: set[Declaration] = set()
    owner = f"{cls.__module__}.{cls.__qualname__}"
    for field in dataclasses.fields(cls):
        spec = ref_spec_of(field)
        if spec is not None:
            found.add(Declaration(owner, field.name, spec.registry, spec.inverse, spec.many))
    try:
        hints = typing.get_type_hints(cls)
    except Exception:  # observability: ignore R2: an unresolvable hint only hides type-level declarations; instances are still walked
        hints = {}
    for hint in hints.values():
        for nested in _hinted_dataclasses(hint):
            found |= type_declarations(nested, seen)
    return found


def _build(specs: tuple[RegistrySpec, ...]) -> ReferenceIndex:
    forward: dict[tuple[str, str], tuple[Reference, ...]] = {}
    inverse: dict[tuple[str, Any], dict[str, list[Reference]]] = {}
    declarations: set[Declaration] = set()
    seen_types: set[type] = set()
    for spec in specs:
        for key, entry in spec.loader().items():
            found, declared = entry_references(entry)
            declarations |= declared
            if type(entry) not in seen_types:
                declarations |= type_declarations(type(entry), seen_types)
            references = tuple(
                Reference(spec.name, str(key), path, ref.registry, target, ref.inverse)
                for path, ref, target in found
            )
            if references:
                forward[(spec.name, str(key))] = references
            for reference in references:
                groups = inverse.setdefault((reference.target_registry, reference.target_key), {})
                groups.setdefault(reference.inverse, []).append(reference)
    return ReferenceIndex(
        forward=MappingProxyType(forward),
        inverse=MappingProxyType(
            {
                target: MappingProxyType({name: tuple(refs) for name, refs in groups.items()})
                for target, groups in inverse.items()
            }
        ),
        declarations=frozenset(declarations),
    )


@functools.lru_cache(maxsize=8)
def _cached(specs: tuple[RegistrySpec, ...]) -> ReferenceIndex:
    return _build(specs)


def build_reference_index(specs: tuple[RegistrySpec, ...] | None = None) -> ReferenceIndex:
    """The forward/inverse reference maps, cached per index for the process.

    Registries never change at runtime, so one walk per process suffices. The
    cache is keyed by the index tuple itself, so a different index (a test's
    synthetic one) never reuses another index's maps.
    """
    return _cached(REGISTRY_INDEX if specs is None else tuple(specs))


def _key_sets(specs: tuple[RegistrySpec, ...]) -> dict[str, frozenset[Any]]:
    return {spec.name: frozenset(spec.loader()) for spec in specs}


def check_references(specs: tuple[RegistrySpec, ...] | None = None) -> list[DanglingReference]:
    """Every declared reference whose target key is absent (CI contract)."""
    index_specs = REGISTRY_INDEX if specs is None else tuple(specs)
    keys = _key_sets(index_specs)
    dangling: list[DanglingReference] = []
    for references in build_reference_index(index_specs).forward.values():
        for reference in references:
            if reference.target_key not in keys.get(reference.target_registry, frozenset()):
                dangling.append(
                    DanglingReference(
                        reference.registry,
                        reference.key,
                        reference.field_path,
                        reference.target_registry,
                        reference.target_key,
                    )
                )
    return dangling


def declaration_errors(specs: tuple[RegistrySpec, ...] | None = None) -> list[str]:
    """Declarations naming an unindexed registry or reusing an inverse name.

    Distinct declarations (declaring class and field) into one target registry
    must use distinct inverse names; repeated instances of one declaration are
    the same declaration and never collide.
    """
    index_specs = REGISTRY_INDEX if specs is None else tuple(specs)
    names = {spec.name for spec in index_specs}
    errors: list[str] = []
    owners: dict[tuple[str, str], tuple[str, str]] = {}
    for declaration in sorted(
        build_reference_index(index_specs).declarations,
        key=lambda item: (item.target_registry, item.inverse, item.owner, item.field),
    ):
        site = f"{declaration.owner}.{declaration.field}"
        if declaration.target_registry not in names:
            errors.append(f"{site} references unindexed registry {declaration.target_registry!r}")
        slot = (declaration.target_registry, declaration.inverse)
        previous = owners.get(slot)
        if previous is not None and previous != (declaration.owner, declaration.field):
            errors.append(
                f"{site} reuses inverse {declaration.inverse!r} into "
                f"{declaration.target_registry!r} already declared by {previous[0]}.{previous[1]}"
            )
        owners.setdefault(slot, (declaration.owner, declaration.field))
    return errors


def iter_declared_fields(cls: type) -> Iterator[tuple[str, RefSpec]]:
    """The declared reference fields of one dataclass type."""
    for field in dataclasses.fields(cls):
        spec = ref_spec_of(field)
        if spec is not None:
            yield field.name, spec


__all__ = [
    "GROUPS",
    "REGISTRY_INDEX",
    "DanglingReference",
    "Declaration",
    "Reference",
    "ReferenceIndex",
    "RegistrySpec",
    "build_reference_index",
    "check_references",
    "declaration_errors",
    "entry_references",
    "iter_declared_fields",
    "spec_by_name",
]
