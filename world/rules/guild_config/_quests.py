"""Quest-reward validation into immutable guild offers.

The side-effect-free ``register_guild_offer`` pre-flight stays here so catalog
load never mutates the process-global offer registry.
"""

from typing import Any, Mapping

from world.lore.items import ITEM_REGISTRY
from world.rules.guild_offers import GuildQuestOffer, ItemQuantity, QuestReward

from ._loaders import _error, _require_int


def validate_quest_rewards(raw: Any, definition_registry: Mapping[str, Any]) -> list[GuildQuestOffer]:
    """Validate YAML hand-written rewards into immutable offers.

    ``definition_registry`` is supplied by the caller so catalog loading can run
    before quest synchronization registers definitions without importing state.
    Validation is side-effect free; callers register the returned offers
    explicitly through ``register_catalog_offers``.
    """
    if not isinstance(raw, list):
        raise _error("quest_rewards must be a list")
    offers: list[GuildQuestOffer] = []
    for position, entry in enumerate(raw, start=1):
        if not isinstance(entry, Mapping):
            raise _error(f"quest_rewards[{position}] must be a mapping")
        definition_key = entry.get("definition_key")
        if definition_key not in definition_registry:
            raise _error(f"quest_rewards[{position}].definition_key {definition_key!r} is unknown")
        reward_entry = entry.get("reward")
        if not isinstance(reward_entry, Mapping):
            raise _error(f"quest_rewards[{position}].reward must be a mapping")
        copper = _require_int(reward_entry.get("copper"), f"quest_rewards.{definition_key}.copper", minimum=0)
        merit = _require_int(reward_entry.get("merit"), f"quest_rewards.{definition_key}.merit", minimum=0)
        items_entry = reward_entry.get("items")
        if not isinstance(items_entry, list):
            raise _error(f"quest_rewards.{definition_key}.items must be a list")
        quantities: list[ItemQuantity] = []
        seen: set[str] = set()
        for item_position, item in enumerate(items_entry, start=1):
            if not isinstance(item, Mapping):
                raise _error(f"quest_rewards.{definition_key}.items[{item_position}] must be a mapping")
            item_key = item.get("item_key")
            if item_key not in ITEM_REGISTRY:
                raise _error(f"quest_rewards.{definition_key}.items[{item_position}].item_key {item_key!r} is unknown")
            if item_key in seen:
                raise _error(f"quest_rewards.{definition_key} has duplicate item {item_key!r}")
            seen.add(item_key)
            quantity = _require_int(item.get("quantity"), f"quest_rewards.{definition_key}.{item_key}.quantity", minimum=1)
            quantities.append(ItemQuantity(item_key=item_key, quantity=quantity))
        offer = GuildQuestOffer(
            definition_key=definition_key,
            issuer_branch_key="guild_branch_altoria",
            reward=QuestReward(copper=copper, items=tuple(quantities), merit=merit),
        )
        # Validate the full offer contract (known branch, rank band, items)
        # without touching the process-global offer registry.
        validate_guild_offer_side_effect_free(offer)
        offers.append(offer)
    return offers


def validate_guild_offer_side_effect_free(offer: GuildQuestOffer) -> None:
    """Run ``register_guild_offer``'s validation without mutating the registry."""
    from world.rules.guild_offers import GuildOfferError, validate_offer

    try:
        validate_offer(offer)
    except GuildOfferError as error:
        raise _error(f"catalog offer {offer.definition_key!r} is invalid: {error}") from error
