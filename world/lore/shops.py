"""Immutable shop identity registry for the deterministic economy (guild-economy D-8).

Shop definitions carry stable identity and offered item keys only; exact
prices, hours, and stock quantities live in
``world/rules/rulebook/guild_economy.yaml``.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ShopDefinition:
    """Immutable identity of one deterministic shop."""

    key: str
    merchant_component_key: str
    offered_item_keys: tuple[str, ...]


SHOP_REGISTRY: dict[str, ShopDefinition] = {
    definition.key: definition
    for definition in (
        ShopDefinition(
            key="altoria_general_store",
            merchant_component_key="merchant",
            offered_item_keys=("meal", "healing_potion", "plain_sword"),
        ),
    )
}