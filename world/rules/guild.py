"""Guild registration, membership, and local service-host resolution (guild-economy D-2).

``register_adventurer`` is the sole registration writer. It accepts an
unregistered ``PlayerCharacter`` standing with a local ``GuildStaff`` host,
derives the branch exclusively from that component, snapshots all eight
displayed trait keys through ``get_display_value``, and assigns the universal
F rank atomically. Re-registration is an idempotent read that preserves the
original branch/tick/snapshot.
"""

from enum import StrEnum
from typing import Any

from django.db import transaction

from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildStaff
from world.rules.clock import get_world_clock
from world.rules.surfaces import attribute_snapshot
from world.rules.traits import get_display_value

REGISTRATION_TRAIT_KEYS = (
    "hp",
    "mp",
    "sp",
    "atk_phys",
    "agility",
    "defense",
    "magic_level",
    "guild_merit",
)
_REGISTRATION_FIELDS = frozenset(
    {"branch_key", "registered_tick", "displayed_stats"}
)


class GuildDataError(ValueError):
    """Malformed persisted or supplied guild data."""


class GuildServiceError(ValueError):
    """A required local service host is absent or ambiguous."""


class GuildError(ValueError):
    """A generic deterministic guild rejection with a named reason."""


class RegistrationReason(StrEnum):
    NOT_A_PLAYER = "not_a_player"
    NO_STAFF = "no_staff"
    AMBIGUOUS_STAFF = "ambiguous_staff"
    REMOTE_STAFF = "remote_staff"
    ALREADY_REGISTERED = "already_registered"
    MALFORMED_REGISTRATION = "malformed_registration"


def resolve_local_service_host(actor: Any, component_class: type) -> Any:
    """Return the single local host carrying ``component_class``.

    Searches only ``actor.location.contents``; a missing host raises
    ``GuildServiceError`` (reason 0) and multiple matching hosts raise with
    reason ``ambiguous``. Remote dbref use is impossible by construction: this
    API never accepts a dbref argument.
    """
    if actor.location is None:
        raise GuildServiceError("no local service host")
    matches = [
        obj
        for obj in actor.location.contents
        if getattr(obj, "components", None) is not None
        and obj.components.has(component_class.name)
    ]
    if not matches:
        raise GuildServiceError("no local service host")
    if len(matches) > 1:
        raise GuildServiceError("multiple local service hosts")
    return matches[0]


def parse_guild_registration(actor: Any) -> dict[str, Any]:
    """Strictly parse ``actor.db.guild_registration``.

    A missing record returns ``None``. A present record must contain exactly
    ``branch_key``, ``registered_tick``, and ``displayed_stats`` (a mapping of
    exactly the eight registration trait keys); any other shape raises
    ``GuildDataError`` without repair.
    """
    raw = actor.db.guild_registration
    if raw is None:
        return None
    try:
        raw = dict(raw)
    except (TypeError, ValueError) as error:
        raise GuildDataError(
            f"guild_registration is not a mapping: {error}"
        ) from error
    unknown = set(raw) - _REGISTRATION_FIELDS
    if unknown:
        raise GuildDataError(
            f"guild_registration has unknown fields {sorted(unknown)}"
        )
    missing = _REGISTRATION_FIELDS - set(raw)
    if missing:
        raise GuildDataError(
            f"guild_registration is missing fields {sorted(missing)}"
        )
    branch_key = raw["branch_key"]
    registered_tick = raw["registered_tick"]
    if not isinstance(branch_key, str) or not branch_key:
        raise GuildDataError("branch_key must be a non-empty string")
    if isinstance(registered_tick, bool) or not isinstance(registered_tick, int):
        raise GuildDataError("registered_tick must be an integer")
    displayed = raw["displayed_stats"]
    try:
        displayed = dict(displayed)
    except (TypeError, ValueError) as error:
        raise GuildDataError(
            f"displayed_stats is not a mapping: {error}"
        ) from error
    if set(displayed) != set(REGISTRATION_TRAIT_KEYS):
        raise GuildDataError(
            f"displayed_stats must cover exactly {sorted(REGISTRATION_TRAIT_KEYS)}"
        )
    for key, value in displayed.items():
        if isinstance(value, bool) or not isinstance(value, int):
            raise GuildDataError(f"displayed_stats.{key} must be an integer")
    return {
        "branch_key": branch_key,
        "registered_tick": registered_tick,
        "displayed_stats": {key: displayed[key] for key in REGISTRATION_TRAIT_KEYS},
    }


def _registration_snapshot(actor: Any) -> dict[str, Any]:
    return {
        "registration": attribute_snapshot(actor, "guild_registration"),
        "rank": attribute_snapshot(actor, "guild_rank"),
    }


def _restore_registration(actor: Any, snapshot: dict[str, Any]) -> None:
    from world.rules.surfaces import restore_attribute_best_effort

    restore_attribute_best_effort(actor, "guild_registration", snapshot["registration"])
    restore_attribute_best_effort(actor, "guild_rank", snapshot["rank"])
    try:
        actor.attributes.reset_cache()
    except Exception:
        pass


def registration_data_for(actor: Any) -> bool:
    """Return whether ``actor`` holds a valid guild registration."""
    try:
        return parse_guild_registration(actor) is not None
    except GuildDataError:
        return False


def register_adventurer(
    actor: Any,
    staff: Any | None = None,
) -> dict[str, Any]:
    """Register an unregistered ``PlayerCharacter`` at rank F through local staff.

    ``staff`` may be the resolved ``GuildStaff`` host (as a command passes it)
    or ``None``; when ``None`` the local host is resolved from the actor's
    current room. The branch is derived only from the validated component.
    Re-registering a valid member returns the original record without
    overwriting it.
    """
    if not isinstance(actor, PlayerCharacter):
        raise GuildError(RegistrationReason.NOT_A_PLAYER)
    current = parse_guild_registration(actor)
    if current is not None:
        return current
    if actor.guild_rank is not None and current is None:
        raise GuildDataError(
            "guild_rank is set but guild_registration is missing its snapshot"
        )

    if staff is not None and actor.location is not None:
        if actor.location != staff.location:
            raise GuildError(RegistrationReason.REMOTE_STAFF)
    if staff is None:
        staff = resolve_local_service_host(actor, GuildStaff)
    if not hasattr(staff, "components") or not staff.components.has(GuildStaff.name):
        raise GuildError(RegistrationReason.NO_STAFF)
    if actor.location is None or staff.location != actor.location:
        raise GuildError(RegistrationReason.REMOTE_STAFF)

    guild_staff = staff.components.get(GuildStaff.get_component_slot())
    branch_key = guild_staff.branch_key
    if not isinstance(branch_key, str) or not branch_key:
        raise GuildDataError("GuildStaff component has no branch_key")

    snapshot = _registration_snapshot(actor)
    try:
        with transaction.atomic():
            actor.db.guild_registration = {
                "branch_key": branch_key,
                "registered_tick": get_world_clock().tick,
                "displayed_stats": {
                    key: int(get_display_value(actor, key))
                    for key in REGISTRATION_TRAIT_KEYS
                },
            }
            actor.guild_rank = "F"
    except Exception:
        _restore_registration(actor, snapshot)
        raise
    parsed = parse_guild_registration(actor)
    if parsed is None:
        raise GuildDataError("registration write produced no parseable record")
    return parsed


class RewardClaimError(ValueError):
    """A reward claim violates the atomic settlement contract."""


class RewardClaim(StrEnum):
    UNREGISTERED = "unregistered"
    NO_STAFF = "no_staff"
    NO_COMPLETED_RECORD = "no_completed_record"
    OFFER_UNKNOWN = "offer_unknown"
    ALREADY_CLAIMED = "already_claimed"
    MALFORMED_CLAIMS = "malformed_claims"


def parse_reward_claims(actor: Any) -> list[str]:
    """Strictly parse ``actor.db.guild_reward_claims`` (a JSON-safe ID list)."""
    raw = actor.db.guild_reward_claims
    if raw is None:
        return []
    if isinstance(raw, (str, bytes)) or not hasattr(raw, "__iter__"):
        raise RewardClaimError(RewardClaim.MALFORMED_CLAIMS)
    claims = list(raw)
    if not all(isinstance(item, str) and item for item in claims):
        raise RewardClaimError(RewardClaim.MALFORMED_CLAIMS)
    if len(set(claims)) != len(claims):
        raise RewardClaimError(RewardClaim.MALFORMED_CLAIMS)
    return claims


def _require_local_staff(actor: Any, staff: Any) -> None:
    if staff is None:
        raise RewardClaimError(RewardClaim.NO_STAFF)
    if not hasattr(staff, "components") or not staff.components.has(GuildStaff.name):
        raise RewardClaimError(RewardClaim.NO_STAFF)
    if actor.location is None or staff.location != actor.location:
        raise RewardClaimError(RewardClaim.NO_STAFF)


def turn_in_quest(
    actor: Any,
    staff: Any,
    quest_id: str,
) -> dict[str, Any]:
    """Claim one completed guild quest reward exactly once (D-4/D-10).

    Requires a valid registration, local GuildStaff, a parsed ``COMPLETED``
    record with the exact quest ID, a registered offer for that definition at
    the staff's branch, and the quest ID absent from reward claims. All reward
    surfaces (wallet, inventory, ACQUIRE quest log, merit, claims) commit in
    one transaction with full cache restoration.
    """
    from world.quests.runtime import QuestState, find_record, read_records
    from world.rules.guild_offers import (
        GuildOfferNotFound,
        get_guild_offer,
    )
    from world.rules.surfaces import (
        attribute_snapshot,
        restore_attribute,
        restore_traits,
        snapshot_attributes,
        snapshot_traits,
    )
    from world.rules.equipment import plan_inventory_delta

    if not isinstance(actor, PlayerCharacter):
        raise GuildError(RegistrationReason.NOT_A_PLAYER)
    if parse_guild_registration(actor) is None:
        raise RewardClaimError(RewardClaim.UNREGISTERED)
    _require_local_staff(actor, staff)
    guild_staff = staff.components.get(GuildStaff.get_component_slot())
    branch_key = guild_staff.branch_key
    if not isinstance(branch_key, str) or not branch_key:
        raise RewardClaimError(RewardClaim.NO_STAFF)

    records = read_records(actor)
    record = find_record(records, quest_id)
    if record is None or record.state is not QuestState.COMPLETED:
        raise RewardClaimError(RewardClaim.NO_COMPLETED_RECORD)
    try:
        offer = get_guild_offer(record.definition_key, branch_key)
    except GuildOfferNotFound as error:
        raise RewardClaimError(RewardClaim.OFFER_UNKNOWN) from error

    claims = parse_reward_claims(actor)
    if quest_id in claims:
        raise RewardClaimError(RewardClaim.ALREADY_CLAIMED)

    reward = offer.reward
    inventory_plan = plan_inventory_delta(
        actor,
        additions=tuple(
            item.item_key
            for item in reward.items
            for _ in range(item.quantity)
        ),
    )

    snapshots = snapshot_attributes(
        actor,
        ("wallet", "inventory", "quest_log", "guild_reward_claims"),
    )
    trait_snapshot = snapshot_traits(actor)
    pin_operations = inventory_plan.acquire[1] if inventory_plan.acquire is not None else ()
    pin_snapshots = {}
    from world.quests.transitions import snapshot_pin_reasons

    for room, _, _ in pin_operations:
        pin_snapshots[id(room)] = snapshot_pin_reasons(room)

    def writer():
        actor.db.wallet = int(actor.db.wallet or 0) + reward.copper
        actor.db.inventory = list(inventory_plan.after)
        from world.rules.surfaces import read_counter_trait, write_counter_trait

        write_counter_trait(
            actor,
            "guild_merit",
            read_counter_trait(actor, "guild_merit") + reward.merit,
        )
        if inventory_plan.acquire is not None:
            from world.quests.transitions import apply_quest_log_delta

            apply_quest_log_delta(
                actor,
                list(inventory_plan.acquire[0]),
                inventory_plan.acquire[1],
            )
        actor.db.guild_reward_claims = [*claims, quest_id]

    def restore():
        from world.rules.surfaces import restore_attribute_best_effort

        for key in ("wallet", "inventory", "quest_log", "guild_reward_claims"):
            restore_attribute_best_effort(actor, key, snapshots[key])
        restore_traits(actor, trait_snapshot)
        from world.quests.transitions import restore_pin_reasons

        for room, _, _ in pin_operations:
            restore_pin_reasons(room, pin_snapshots[id(room)])

    try:
        with transaction.atomic():
            writer()
    except Exception:
        restore()
        raise
    return {
        "quest_id": quest_id,
        "copper": reward.copper,
        "merit": reward.merit,
        "items": [str(item.item_key) for item in reward.items],
    }