"""Shared movement-cost charging for every exit lineage (map-movement-clock).

One function, ``charge_movement``, is the single place an exit traversal advances
``WorldClock`` for a successful, player-driven step. Each exit typeclass carries
a ``movement_cost_key`` resolved against ``CLOCK_YAML["command_defaults"]``, so
grid steps, the Limbo bridge, instance-room doorways, and wilderness steps all
share one cost table and one charging mechanism instead of bespoke inline
``get_world_clock().advance(...)`` calls (design.md D-1/D-5).
"""


def charge_movement(traversing_object, cost_key: str) -> None:
    """Charge ``WorldClock`` for one successful traversal, if the traverser is a player.

    Resolves the cost from ``CLOCK_YAML["command_defaults"][cost_key]`` and calls
    ``WorldClock.advance(cost, AdvanceSource.COMMAND, [traversing_object])`` only
    when ``traversing_object`` is a ``PlayerCharacter`` — matching design doc D4
    ("the world advances only on player action"). Anything else is a no-op, so a
    future NPC or monster crossing an exit never drives the global clock on its
    own schedule (design.md D-8).
    """

    from typeclasses.characters import PlayerCharacter

    if not isinstance(traversing_object, PlayerCharacter):
        return
    from world.rules.clock import CLOCK_YAML, AdvanceSource, get_world_clock

    cost = CLOCK_YAML["command_defaults"][cost_key]
    get_world_clock().advance(cost, AdvanceSource.COMMAND, [traversing_object])
