"""Immutable guild quest offers that bind economics to quest definitions (guild-economy D-3).

``ItemQuantity``, ``QuestReward``, and ``GuildQuestOffer`` are frozen values.
Registration validates every reference against the quest, guild, item, and
branch identities it names and enforces the referenced quest rank's copper
reward band. Equal duplicate registration is idempotent; conflicting content
fails before replacement. Board listing filters by canonical guild rank only.
"""

from dataclasses import dataclass
from typing import Any

from world.lore.guild import GUILD_BRANCH_REGISTRY, GUILD_RANK_REGISTRY
from world.lore.items import ITEM_REGISTRY
from world.quests.definitions import QUEST_DEFINITION_REGISTRY


class GuildOfferError(ValueError):
    """An offer violates the closed registration contract."""


class GuildOfferNotFound(KeyError):
    """A referenced offer is not registered."""


@dataclass(frozen=True)
class ItemQuantity:
    """One item key plus its positive integer quantity in a reward."""

    item_key: str
    quantity: int


@dataclass(frozen=True)
class QuestReward:
    """The immutable reward surfaces of one completed guild quest."""

    copper: int
    items: tuple[ItemQuantity, ...]
    merit: int


@dataclass(frozen=True)
class GuildQuestOffer:
    """One branch-issued offer of a quest definition with its reward."""

    definition_key: str
    issuer_branch_key: str
    reward: QuestReward


GUILD_OFFER_REGISTRY: dict[tuple[str, str], GuildQuestOffer] = {}


def _reject(message: str) -> None:
    raise GuildOfferError(message)


def validate_offer(offer: GuildQuestOffer) -> None:
    """Raise ``GuildOfferError`` unless ``offer`` is fully valid.

    Validates every named reference (quest definition, branch identity via a
    non-empty issuer key, item keys, and duplicate reward item keys) plus the
    reward quantity/bound rules: non-negative integer copper and merit,
    positive integer item quantities, and copper inside the referenced quest
    rank's ``GUILD_RANK_REGISTRY`` reward band (with S honoring its open upper
    bound).
    """
    if not isinstance(offer, GuildQuestOffer):
        _reject("guild offers must be GuildQuestOffer values, not raw mappings")
    if not isinstance(offer.definition_key, str) or not offer.definition_key:
        _reject("definition_key must be a non-empty string")
    definition = QUEST_DEFINITION_REGISTRY.get(offer.definition_key)
    if definition is None:
        _reject(f"unknown quest definition {offer.definition_key!r}")
    if not isinstance(offer.issuer_branch_key, str) or not offer.issuer_branch_key:
        _reject("issuer_branch_key must be a non-empty string")
    if offer.issuer_branch_key not in GUILD_BRANCH_REGISTRY:
        _reject(f"unknown guild branch {offer.issuer_branch_key!r}")

    reward = offer.reward
    if not isinstance(reward, QuestReward):
        _reject("reward must be a QuestReward value")
    if isinstance(reward.copper, bool) or not isinstance(reward.copper, int):
        _reject("reward copper must be an integer")
    if reward.copper < 0:
        _reject(f"reward copper must be non-negative, got {reward.copper}")
    if isinstance(reward.merit, bool) or not isinstance(reward.merit, int):
        _reject("reward merit must be an integer")
    if reward.merit < 0:
        _reject(f"reward merit must be non-negative, got {reward.merit}")
    if not isinstance(reward.items, tuple):
        _reject("reward items must be a tuple of ItemQuantity values")

    rank = GUILD_RANK_REGISTRY.get(definition.rank)
    if rank is None:
        _reject(f"quest rank {definition.rank!r} is not in GUILD_RANK_REGISTRY")
    band_floor = rank.reward_min_copper
    band_ceiling = rank.reward_max_copper
    if reward.copper < band_floor:
        _reject(
            f"{offer.definition_key!r} copper {reward.copper} is below "
            f"{rank.key} rank minimum {band_floor}"
        )
    if band_ceiling is not None and reward.copper > band_ceiling:
        _reject(
            f"{offer.definition_key!r} copper {reward.copper} is above "
            f"{rank.key} rank maximum {band_ceiling}"
        )

    seen_items: set[str] = set()
    for quantity in reward.items:
        if not isinstance(quantity, ItemQuantity):
            _reject("reward items must carry ItemQuantity values")
        item_key = quantity.item_key
        if item_key not in ITEM_REGISTRY:
            _reject(f"unknown reward item {item_key!r}")
        if isinstance(quantity.quantity, bool) or (
            not isinstance(quantity.quantity, int) or quantity.quantity < 1
        ):
            _reject(
                f"reward item {item_key!r} quantity must be a positive integer"
            )
        if item_key in seen_items:
            _reject(f"duplicate reward item key {item_key!r}")
        seen_items.add(item_key)


def register_guild_offer(offer: GuildQuestOffer) -> None:
    """Register one validated offer idempotently.

    Equal content under an existing ``(definition_key, issuer_branch_key)``
    identity is a no-op; conflicting content raises before replacing the
    original.
    """
    validate_offer(offer)
    key = (offer.definition_key, offer.issuer_branch_key)
    current = GUILD_OFFER_REGISTRY.get(key)
    if current is not None:
        if current == offer:
            return
        _reject(
            f"conflicting offer {offer.definition_key!r} already registered "
            f"for branch {offer.issuer_branch_key!r}"
        )
    GUILD_OFFER_REGISTRY[key] = offer


def get_guild_offer(definition_key: str, issuer_branch_key: str) -> GuildQuestOffer:
    """Return the registered offer or raise ``GuildOfferNotFound``."""
    try:
        return GUILD_OFFER_REGISTRY[(definition_key, issuer_branch_key)]
    except KeyError as error:
        raise GuildOfferNotFound(
            f"no offer for {definition_key!r} at branch {issuer_branch_key!r}"
        ) from error


class BoardAccessError(ValueError):
    """A board listing/acceptance violates registration or rank eligibility."""


def _rank_order(rank_key: str) -> int:
    rank = GUILD_RANK_REGISTRY.get(rank_key)
    if rank is None:
        raise BoardAccessError(f"unknown guild rank {rank_key!r}")
    return rank.order


def list_guild_offers(
    actor: Any,
    staff: Any,
) -> tuple[GuildQuestOffer, ...]:
    """Return local branch offers whose quest rank is at or below the actor's.

    Eligibility uses the actor's canonical ``guild_rank`` only; registration
    snapshot values and ``disguised_stats`` are never read here. Results are
    ordered by (quest rank order, definition key).
    """
    from world.rules.guild import parse_guild_registration
    from typeclasses.components import GuildStaff

    registration = parse_guild_registration(actor)
    if registration is None:
        raise BoardAccessError("actor is not registered")
    if not hasattr(staff, "components") or not staff.components.has(GuildStaff.name):
        raise BoardAccessError("no local GuildStaff host")
    guild_staff = staff.components.get(GuildStaff.get_component_slot())
    branch_key = guild_staff.branch_key
    if branch_key is None:
        raise BoardAccessError("GuildStaff host has no branch_key")

    actor_rank = getattr(actor, "guild_rank", None)
    if actor_rank is None:
        raise BoardAccessError("actor has no guild rank")
    actor_order = _rank_order(actor_rank)

    eligible = [
        offer
        for offer in GUILD_OFFER_REGISTRY.values()
        if offer.issuer_branch_key == branch_key
        and _rank_order(QUEST_DEFINITION_REGISTRY[offer.definition_key].rank)
        <= actor_order
    ]
    return tuple(
        sorted(
            eligible,
            key=lambda offer: (
                _rank_order(QUEST_DEFINITION_REGISTRY[offer.definition_key].rank),
                offer.definition_key,
            ),
        )
    )


def accept_guild_offer(
    actor: Any,
    staff: Any,
    definition_key: str,
) -> Any:
    """Validate board eligibility, then delegate acceptance to the quest runtime.

    The guild layer never constructs or mutates quest records itself.
    """
    offers = list_guild_offers(actor, staff)
    if not any(offer.definition_key == definition_key for offer in offers):
        raise BoardAccessError(f"offer {definition_key!r} is not board-eligible")
    from world.quests.runtime import accept_quest

    return accept_quest(actor, definition_key)


def abandon_guild_quest(actor: Any, staff: Any, quest_id: str) -> Any:
    """Delegate abandonment to the quest runtime for the exact quest ID.

    The guild layer performs no second abandonment state and never constructs
    or reinterprets quest-record dicts itself.
    """
    del staff
    from world.quests.runtime import abandon_quest

    return abandon_quest(actor, quest_id)