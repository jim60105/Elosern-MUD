"""Immutable shop identity registry for the deterministic economy (guild-economy D-8).

Shop definitions carry stable identity, the merchant host's authored NPC
identity (name + title, npc-title-authored-identities D5), and offered item
keys; exact prices, hours, and stock quantities live in
``world/rules/rulebook/guild_economy.yaml``.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ShopDefinition:
    """Immutable identity of one deterministic shop."""

    key: str
    merchant_component_key: str
    # Authored NPC identity of the shop's service host (design D5).
    host_name: str
    host_title: str
    offered_item_keys: tuple[str, ...]


SHOP_REGISTRY: dict[str, ShopDefinition] = {
    definition.key: definition
    for definition in (
        ShopDefinition(
            key="altoria_general_store",
            merchant_component_key="merchant",
            host_name="瑪爾特·金秤",
            host_title="阿爾托利亞雜貨商店老闆",
            offered_item_keys=(
                "meal", "healing_potion", "plain_sword",
                "iron_dagger", "hunting_throwing_axe", "hunters_longbow", "apprentice_focus_staff", "knight_blade", "magic_sword", "leather_armor", "mage_robe", "chainmail", "iron_shield", "silver_hairpin", "wolf_fang_necklace", "pilgrim_medallion", "protective_ring", "storage_pouch", "gliding_cloak", "magic_lamp", "healing_herb", "rough_iron_ore", "beast_crystal", "evernight_shard", "mana_core", "dragon_scale_fragment", "elven_spider_silk", "baptismal_holy_water", "greater_healing_potion", "mana_potion",
                "purified_pendant", "fearless_brooch", "knight_platemail", "apothecary_beads", "archmage_mending_robe", "enticing_lace_set", "passion_silk_choker", "sister_vestments", "radiant_holy_emblem", "saintess_vestments",
            ),
        ),
    )
}


def validate_shop_npc_identities(
    definitions: dict[str, ShopDefinition] | None = None,
) -> None:
    """Fail closed on the shipped host authored identities (design D4).

    Pure checker callable with explicit rows (tests); defaults to the shipped
    registry. Raises ValueError naming the offending row and rule.
    """
    from world.rules.npc_identity import validate_npc_name, validate_npc_title

    for definition in (SHOP_REGISTRY if definitions is None else definitions).values():
        try:
            validate_npc_name(definition.host_name)
        except ValueError as error:
            raise ValueError(f"shop {definition.key} has an invalid host_name: {error}") from error
        try:
            validate_npc_title(definition.host_title)
        except ValueError as error:
            raise ValueError(f"shop {definition.key} has an invalid host_title: {error}") from error


def validate_shipped_identity_uniqueness() -> None:
    """Cross-registry authored-name uniqueness for the shipped rows (design D4).

    Runs here rather than in ``guild.py`` to keep the guild registry importable
    without the shop module; the shared checker itself is pure and callable
    with explicit entries from tests.
    """
    from .guild import GUILD_BRANCH_REGISTRY, GUILD_RANK_REGISTRY
    from world.rules.npc_identity import validate_unique_npc_names

    entries: list[tuple[str, str]] = [
        (f"shop:{definition.key}", definition.host_name)
        for definition in SHOP_REGISTRY.values()
    ]
    entries += [
        (f"guild_branch:{branch.key}", branch.host_name)
        for branch in GUILD_BRANCH_REGISTRY.values()
    ]
    entries += [
        (f"guild_rank:{rank.key}", rank.examiner_name)
        for rank in GUILD_RANK_REGISTRY.values()
    ]
    validate_unique_npc_names(entries)


validate_shop_npc_identities()
validate_shipped_identity_uniqueness()
