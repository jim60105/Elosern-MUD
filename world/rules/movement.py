"""Shared movement-cost charging for every exit lineage (map-movement-clock).

One function, ``charge_movement``, is the single place an exit traversal advances
``WorldClock`` for a successful, player-driven step. Distance-bearing outdoor
traversal charges the physical duration the exit resolved at preflight
(``world.rules.travel_cost``: authored edge geometry integrated against the
slowest eligible source-present traveller's terrain speed, recomputed at every
member threshold and terrain boundary, rounded upward once);
explicit non-distance connectors — the Limbo bridge, instance-room doorways, a
plain room pair — charge their authored ``CLOCK_YAML["command_defaults"]``
duration. Grid steps, wilderness steps and gate approaches still share one cost
mechanism instead of bespoke inline ``get_world_clock().advance(...)`` calls
(design.md D-1/D-5).

The charge settles as one indivisible interval through
``WorldClock.advance_bounded``: a committed edge longer than the clock's
one-day single-call bound is advanced in bounded pieces that share one
full-window rollback snapshot rather than being clipped. Admission (forced
sleepers, pre-destination depletion) runs before the flight waiver and before
any time or location write.

``wilderness_move`` is retained only as the distinct wilderness travel context
that carries the existing flight waiver. It is never a seconds authority: a
wilderness step with no resolvable physical edge is refused instead of being
priced from a fixed constant.
"""


class MovementCostError(ValueError):
    """A movement event has no priceable traversal (refused, not guessed)."""


def charge_movement(
    traversing_object,
    cost_key: str,
    *,
    source_location,
    wilderness_source_coordinates: tuple[int, int] | None = None,
) -> None:
    """Charge ``WorldClock`` for one successful traversal, if the traverser is a player.

    The cost is the preflight record the exit resolved before relocation
    (``preflight_movement_cost``), consumed here without changing this public
    signature: its seconds, its source-present traveller tuple and its terrain
    are immutable, so post-relocation room pooling can never alter the charge.
    A direct call outside an exit lineage falls back to resolving from
    ``source_location`` and the traverser's current location — exactly the
    values the exit would have preflighted.

    ``WorldClock.advance_bounded(cost, AdvanceSource.COMMAND, entities)`` runs
    only when ``is_player_driven(traversing_object)`` is true — matching design doc D4
    ("the world advances only on player action"). Anything else is a no-op, so a
    future NPC or monster crossing an exit never drives the global clock on its
    own schedule (design.md D-8). A ``PlayerCharacter`` owning the ``flight``
    skill is waived the ``wilderness_move`` cost entirely
    (movement-skill-waiver design); every other cost key charges normally.

    ``entities`` is the traverser followed by every party member the follow
    step moves with it (party-rest-move-settlement): the effective companions
    co-located in ``source_location`` before the step and, for a possessed
    traverser, the commander's body. The set comes from the same
    ``travel_scope`` predicate ``follow_companions`` uses, evaluated against
    the pre-move ``source_location`` (and ``wilderness_source_coordinates`` for
    a wilderness step), so admission, charging and following can never
    disagree; a preflighted exit reuses that record's traveller tuple.
    ``source_location`` is required so a caller cannot silently fall back to
    the post-relocation room.
    """

    from world.rules.player_control import is_player_driven

    if not is_player_driven(traversing_object):
        return
    from world.rules.clock import CLOCK_YAML, AdvanceSource, get_world_clock
    from world.rules.travel_cost import (
        MovementPreflightRefused,
        TraversalStatus,
        consume_preflight_resolution,
        refuse_sleeping_party,
        resolve_traversal_cost,
        source_present_members,
    )
    from world.skills.restrictions import skill_effect_allowed

    resolution = consume_preflight_resolution(
        traversing_object, cost_key, source_location
    )
    members = (
        tuple(resolution.members)
        if resolution is not None
        else source_present_members(
            traversing_object, source_location, wilderness_source_coordinates
        )
    )
    # Admission precedes every early return, so a flight waiver can never carry
    # a forced-sleeping present member and a direct charge call cannot bypass
    # the exit lineages' preflight refusal.
    refuse_sleeping_party(members)
    if (
        cost_key == "wilderness_move"
        and "flight" in traversing_object.skills.owned_keys()
        and skill_effect_allowed(traversing_object, "flight")
    ):
        # Owning ``flight`` waives the wilderness clock cost entirely — the
        # lore's "可前往遠處的場合" read as unencumbered long-distance travel
        # (movement-skill-waiver design). ``flash_step`` explicitly does NOT
        # waive this cost; only the flight-required-exit gate honors it.
        return
    if resolution is None:
        resolution = resolve_traversal_cost(
            traversing_object,
            cost_key,
            source_location=source_location,
            destination=getattr(traversing_object, "location", None),
            wilderness_source_coordinates=wilderness_source_coordinates,
            members=members,
        )
    if resolution.status is TraversalStatus.UNRESOLVED:
        raise MovementPreflightRefused(
            "unresolved_outdoor_edge",
            f"{cost_key!r} movement has no authored physical traversal",
        )
    if resolution.cost is not None:
        cost = resolution.cost.seconds
    else:
        if cost_key == "wilderness_move":
            # No fixed wilderness seconds authority remains: a wilderness
            # context with no physical edge is a caller error, never a price.
            raise MovementCostError(
                "wilderness_move requires a resolved physical traversal"
            )
        cost = CLOCK_YAML["command_defaults"][cost_key]
    from world.rules.fatigue import FatigueActivity, IntervalCompletion
    from world.rules.mental_time import plan_for

    members = tuple(resolution.members)
    # The traversal is one indivisible interval: every source-present member
    # settles foot-travel physiology for its full duration, and a body that
    # depletes collapses only after the step has committed. A committed edge
    # longer than the clock's one-call bound is advanced in bounded pieces that
    # share one full-window snapshot, never clipped to a daily cap.
    get_world_clock().advance_bounded(
        cost,
        AdvanceSource.COMMAND,
        list(members),
        mental=plan_for(
            members,
            awake_activity=FatigueActivity.FOOT_TRAVEL,
            completion=IntervalCompletion.INDIVISIBLE,
        ),
    )
