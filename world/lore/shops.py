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


def validate_registry_identity_uniqueness(
    shop_rows: dict[str, ShopDefinition] | None = None,
    branch_rows=None,
    rank_rows=None,
) -> None:
    """Cross-registry authored-name uniqueness over all three name sources (D4).

    Pure checker callable with explicit row mappings (shop, guild-branch and
    rank rows are read for their authored ``host_name``/``examiner_name``);
    defaults to the shipped registries. Every authored name across the three
    registries must be distinct; a collision raises ``NPCNameError`` naming
    both holders. Cycle-safe: the guild registries are imported function-
    locally, so ``guild.py`` can (and does) run the same check through this
    function at its own load time.
    """
    if shop_rows is None:
        shop_rows = SHOP_REGISTRY
    if branch_rows is None or rank_rows is None:
        from .guild import GUILD_BRANCH_REGISTRY, GUILD_RANK_REGISTRY

        if branch_rows is None:
            branch_rows = GUILD_BRANCH_REGISTRY
        if rank_rows is None:
            rank_rows = GUILD_RANK_REGISTRY
    from world.rules.npc_identity import validate_unique_npc_names

    entries: list[tuple[str, str]] = [
        (f"shop:{definition.key}", definition.host_name)
        for definition in shop_rows.values()
    ]
    entries += [
        (f"guild_branch:{branch.key}", branch.host_name)
        for branch in branch_rows.values()
    ]
    entries += [
        (f"guild_rank:{rank.key}", rank.examiner_name)
        for rank in rank_rows.values()
    ]
    validate_unique_npc_names(entries)


def validate_shipped_identity_uniqueness() -> None:
    """Run the cross-registry uniqueness checker over the shipped rows (D4)."""
    validate_registry_identity_uniqueness()


validate_shop_npc_identities()
validate_shipped_identity_uniqueness()
