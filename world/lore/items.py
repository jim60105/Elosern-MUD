"""Immutable item identity registry for the deterministic economy (guild-economy D-8).

Item definitions carry no tunable numeric rules; exact prices, stock, and
restock quantities live in ``world/rules/rulebook/guild_economy.yaml`` and are
joined to these identities by the guild-economy catalog loader.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ItemDefinition:
    """The immutable identity of one supported inventory item."""

    key: str
    display_name_zh: str
    price_table_key: str
    sellable: bool


ITEM_REGISTRY: dict[str, ItemDefinition] = {
    definition.key: definition
    for definition in (
        ItemDefinition(
            key="meal",
            display_name_zh="普通餐食",
            price_table_key="meal",
            sellable=True,
        ),
        ItemDefinition(
            key="healing_potion",
            display_name_zh="治療藥水",
            price_table_key="potion",
            sellable=True,
        ),
        ItemDefinition(
            key="plain_sword",
            display_name_zh="普通劍",
            price_table_key="plain_sword",
            sellable=True,
        ),
    )
}