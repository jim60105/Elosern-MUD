"""Immutable quest issuances that bind quest definitions to issuers (guild or private).

Defines the issuer key grammar, the closed ``Settlement`` vocabulary, the immutable
``QuestIssuance`` value, the ``QUEST_ISSUANCE_REGISTRY`` for private commissions,
and the normalized ``resolve_issuance`` read seam.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from typeclasses.components import QuestIssuer

from world.lore.items import ITEM_REGISTRY
from world.observability import log_info
from world.quests.definitions import QUEST_DEFINITION_REGISTRY
from world.rules.guild_offers import (
    GUILD_OFFER_REGISTRY,
    GuildOfferNotFound,
    ItemQuantity,
    QuestReward,
    get_guild_offer,
)

MAX_ISSUER_KEY_LENGTH = 64
VALID_NAMESPACES = frozenset({"guild", "npc"})


class IssuerKeyError(ValueError):
    """An issuer key violates the closed grammar contract."""


class QuestIssuanceError(ValueError):
    """An issuance or registration violates the issuance contract."""


@dataclass(frozen=True)
class ParsedIssuerKey:
    """The parsed components of a validated issuer key."""

    namespace: str
    remainder: str
    entity_pk: int | None = None


class Settlement(StrEnum):
    """The closed settlement mode vocabulary for quest rewards."""

    COUNTER = "counter"
    AUTO = "auto"


def parse_issuer_key(value: Any) -> ParsedIssuerKey:
    """Parse and validate an issuer key into its namespace and remainder.

    Accepts exactly:
    - ``guild:<branch_key>``
    - ``npc:<content_key>``
    - ``npc:#<pk>`` where pk is a positive decimal integer

    Raises ``IssuerKeyError`` on any violation. Performs no registry lookup.
    """
    if not isinstance(value, str):
        raise IssuerKeyError(f"issuer key must be a string, got {type(value).__name__}")
    if not value:
        raise IssuerKeyError("issuer key must be non-empty")
    if len(value) > MAX_ISSUER_KEY_LENGTH:
        raise IssuerKeyError(
            f"issuer key exceeds maximum length of {MAX_ISSUER_KEY_LENGTH} code points: {len(value)}"
        )

    parts = value.split(":")
    if len(parts) != 2:
        raise IssuerKeyError(
            f"issuer key must have exactly one ':' separator, got {value!r}"
        )

    namespace, remainder = parts[0], parts[1]
    if not namespace:
        raise IssuerKeyError("issuer key namespace must not be empty")
    if not remainder:
        raise IssuerKeyError("issuer key remainder must not be empty")
    if namespace not in VALID_NAMESPACES:
        raise IssuerKeyError(
            f"unknown issuer key namespace {namespace!r}, must be one of {sorted(VALID_NAMESPACES)}"
        )

    entity_pk: int | None = None
    if namespace == "npc" and remainder.startswith("#"):
        pk_str = remainder[1:]
        if not pk_str or not pk_str.isascii() or not pk_str.isdigit():
            raise IssuerKeyError(
                f"npc:# remainder must be a positive integer, got {remainder!r}"
            )
        try:
            entity_pk = int(pk_str)
        except ValueError as exc:
            raise IssuerKeyError(
                f"npc:# remainder could not be converted to int: {remainder!r}"
            ) from exc
        if entity_pk <= 0:
            raise IssuerKeyError(
                f"npc:# remainder must be positive, got {entity_pk}"
            )
    elif namespace == "npc" and remainder.isascii() and remainder.isdigit():
            raise IssuerKeyError(
            f"authored npc: content key cannot be digit-only, got {remainder!r}; use npc:#<pk> for primary keys"
            )

    return ParsedIssuerKey(
        namespace=namespace,
        remainder=remainder,
        entity_pk=entity_pk,
    )


def guild_issuer_key(branch_key: Any) -> str:
    """Construct and validate a guild-namespaced issuer key."""
    if not isinstance(branch_key, str) or not branch_key:
        raise IssuerKeyError(f"branch_key must be a non-empty string, got {branch_key!r}")
    key = f"guild:{branch_key}"
    parse_issuer_key(key)
    return key


def npc_issuer_key(content_key: str | None = None, pk: int | None = None) -> str:
    """Construct and validate an npc-namespaced issuer key.

    Exactly one of ``content_key`` or ``pk`` must be provided.
    """
    if (content_key is None and pk is None) or (content_key is not None and pk is not None):
        raise IssuerKeyError("exactly one of content_key or pk must be provided")

    if pk is not None:
        if isinstance(pk, bool) or not isinstance(pk, int):
            raise IssuerKeyError(f"pk must be an integer, got {type(pk).__name__}")
        if pk <= 0:
            raise IssuerKeyError(f"pk must be a positive integer, got {pk}")
        key = f"npc:#{pk}"
    else:
        if not isinstance(content_key, str) or not content_key:
            raise IssuerKeyError(
                f"content_key must be a non-empty string, got {content_key!r}"
            )
        key = f"npc:{content_key}"

    parse_issuer_key(key)
    return key


def _validate_reward_surface(reward: Any) -> None:
    """Validate reward surface integrity for private commissions."""
    if not isinstance(reward, QuestReward):
        raise QuestIssuanceError("reward must be a QuestReward value")
    if isinstance(reward.copper, bool) or not isinstance(reward.copper, int):
        raise QuestIssuanceError("reward copper must be an integer")
    if reward.copper < 0:
        raise QuestIssuanceError(f"reward copper must be non-negative, got {reward.copper}")
    if isinstance(reward.merit, bool) or not isinstance(reward.merit, int):
        raise QuestIssuanceError("reward merit must be an integer")
    if reward.merit < 0:
        raise QuestIssuanceError(f"reward merit must be non-negative, got {reward.merit}")
    if not isinstance(reward.items, tuple):
        raise QuestIssuanceError("reward items must be a tuple of ItemQuantity values")

    seen_items: set[str] = set()
    for quantity in reward.items:
        if not isinstance(quantity, ItemQuantity):
            raise QuestIssuanceError("reward items must carry ItemQuantity values")
        item_key = quantity.item_key
        if item_key not in ITEM_REGISTRY:
            raise QuestIssuanceError(f"unknown reward item {item_key!r}")
        if isinstance(quantity.quantity, bool) or (
            not isinstance(quantity.quantity, int) or quantity.quantity < 1
        ):
            raise QuestIssuanceError(
                f"item quantity must be a positive integer, got {quantity.quantity!r}"
            )
        if item_key in seen_items:
            raise QuestIssuanceError(f"duplicate reward item {item_key!r}")
        seen_items.add(item_key)


@dataclass(frozen=True)
class QuestIssuance:
    """An immutable binding of a quest definition to an issuer with reward and settlement mode."""

    definition_key: str
    issuer_key: str
    reward: QuestReward
    settlement: Settlement

    def __post_init__(self) -> None:
        if not isinstance(self.definition_key, str) or not self.definition_key:
            raise QuestIssuanceError("definition_key must be a non-empty string")
        if self.definition_key not in QUEST_DEFINITION_REGISTRY:
            raise QuestIssuanceError(f"unknown quest definition {self.definition_key!r}")

        parsed = parse_issuer_key(self.issuer_key)

        if not isinstance(self.settlement, Settlement):
            raise QuestIssuanceError(
                f"settlement must be a Settlement enum member, got {self.settlement!r}"
            )

        _validate_reward_surface(self.reward)

        if parsed.namespace == "npc" and self.reward.merit != 0:
            raise QuestIssuanceError(
                f"private commissions (npc:) cannot grant guild merit, got {self.reward.merit}"
            )


QUEST_ISSUANCE_REGISTRY: dict[tuple[str, str], QuestIssuance] = {}


def register_quest_issuance(issuance: QuestIssuance) -> None:
    """Register a private commission into ``QUEST_ISSUANCE_REGISTRY``.

    Idempotent for identical registrations; raises ``QuestIssuanceError`` on conflict.
    Refuses ``guild:``-namespaced issuances (guild offers have their own registry).
    """
    if not isinstance(issuance, QuestIssuance):
        raise QuestIssuanceError("issuance must be a QuestIssuance instance")

    parsed = parse_issuer_key(issuance.issuer_key)
    if parsed.namespace == "guild":
        raise QuestIssuanceError(
            "QUEST_ISSUANCE_REGISTRY only stores npc-namespaced issuances, "
            f"got guild key {issuance.issuer_key!r}"
        )

    key = (issuance.definition_key, issuance.issuer_key)
    existing = QUEST_ISSUANCE_REGISTRY.get(key)
    if existing is not None:
        if existing == issuance:
            return
        raise QuestIssuanceError(
            f"conflicting issuance already registered for identity {key}: "
            f"existing={existing}, new={issuance}"
        )

    QUEST_ISSUANCE_REGISTRY[key] = issuance
    log_info(
        "quest_issuance_registered",
        context={"quest": issuance.definition_key, "issuer": issuance.issuer_key},
    )


def resolve_issuance(definition_key: str, issuer_key: str) -> QuestIssuance | None:
    """Single normalized read seam resolving an issuance for any issuer namespace.

    Dispatches on the issuer key's namespace:
    - ``guild:`` reads from ``GUILD_OFFER_REGISTRY`` and wraps as counter-settled ``QuestIssuance``
    - ``npc:`` reads from ``QUEST_ISSUANCE_REGISTRY``
    - Malformed keys propagate ``IssuerKeyError``.
    - Unregistered identities return ``None``.
    """
    parsed = parse_issuer_key(issuer_key)
    if parsed.namespace == "guild":
        try:
            offer = get_guild_offer(definition_key, parsed.remainder)
        except GuildOfferNotFound:
            # observability: ignore R2: Unregistered guild offer resolves to None per read seam contract
            return None
        return QuestIssuance(
            definition_key=definition_key,
            issuer_key=issuer_key,
            reward=offer.reward,
            settlement=Settlement.COUNTER,
        )
    if parsed.namespace == "npc":
        return QUEST_ISSUANCE_REGISTRY.get((definition_key, issuer_key))
    return None


def resolve_issuer_key(host: Any) -> str | None:
    """Resolve the issuer key of a private-commission host, or ``None``.

    A host carrying :class:`QuestIssuer` resolves to exactly one key: a
    non-empty authored ``issuer_key`` yields ``npc:<authored key>`` validated
    against the shared grammar (a malformed value raises ``IssuerKeyError``
    rather than being coerced), and an absent (``None``) or empty-string
    value yields the host's identity form ``npc:#<primary key>``. Any other
    stored value is malformed state and raises. A host without the component
    carries no issuing authority and resolves to ``None``. Read-only: no
    registry lookup, so a key resolves whether or not any commission is
    registered for it.
    """
    holder = getattr(host, "components", None)
    component = (
        holder.get(QuestIssuer.get_component_slot())
        if holder is not None
        else None
    )
    if component is None:
        return None
    authored = component.issuer_key
    if authored is None or (isinstance(authored, str) and authored == ""):
        return npc_issuer_key(pk=host.pk)
    if not isinstance(authored, str):
        raise IssuerKeyError(
            f"issuer_key must be a string, got {type(authored).__name__}"
        )
    key = f"npc:{authored}"
    parse_issuer_key(key)
    return key
