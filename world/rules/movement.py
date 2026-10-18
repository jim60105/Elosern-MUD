"""Shared movement-cost charging for every exit lineage (map-movement-clock).

One function, ``charge_movement``, is the single place an exit traversal advances
``WorldClock`` for a successful, player-driven step. Each exit typeclass carries
a ``movement_cost_key`` resolved against ``CLOCK_YAML["command_defaults"]``, so
grid steps, the Limbo bridge, instance-room doorways, and wilderness steps all
share one cost table and one charging mechanism instead of bespoke inline
``get_world_clock().advance(...)`` calls (design.md D-1/D-5).
"""


def charge_movement(
    traversing_object,
    cost_key: str,
    *,
    source_location,
    wilderness_source_coordinates: tuple[int, int] | None = None,
) -> None:
    """Charge ``WorldClock`` for one successful traversal, if the traverser is a player.

    Resolves the cost from ``CLOCK_YAML["command_defaults"][cost_key]`` and calls
    ``WorldClock.advance(cost, AdvanceSource.COMMAND, entities)`` only when
    ``traversing_object`` is player-driven — matching design doc D4 ("the world
    advances only on player action"). Anything else is a no-op, so a future NPC
    or monster crossing an exit never drives the global clock on its own
    schedule (design.md D-8). A ``PlayerCharacter`` owning the ``flight`` skill
    is waived the ``wilderness_move`` cost entirely (movement-skill-waiver
    design); every other cost key charges normally.

    ``entities`` is the traverser followed by every party member the follow
    step moves with it (party-rest-move-settlement): the effective companions
    co-located in ``source_location`` before the step and, for a possessed
    traverser, the commander's body. The follower set comes from the same
    ``follow_scope`` predicate ``follow_companions`` uses, evaluated against
    the pre-move ``source_location`` (and ``wilderness_source_coordinates``
    for a wilderness step), so charging and following can never disagree.
    ``source_location`` is required so a caller cannot silently fall back to
    the post-relocation room.
    """

    from world.rules.player_control import is_player_driven

    if not is_player_driven(traversing_object):
        return
    from world.rules.clock import CLOCK_YAML, AdvanceSource, get_world_clock
    from world.rules.party import follow_scope

    from world.skills.restrictions import skill_effect_allowed

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
    _, followers = follow_scope(
        traversing_object,
        source_location,
        wilderness_source_coordinates,
        log_unresolved=False,
    )
    cost = CLOCK_YAML["command_defaults"][cost_key]
    get_world_clock().advance(
        cost,
        AdvanceSource.COMMAND,
        [traversing_object, *followers],
    )
