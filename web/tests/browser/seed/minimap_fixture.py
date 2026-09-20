"""Minimap seeding fixture.

Slice of the former ``web/tests/browser/seed.py`` module;
every body ships verbatim."""

import os


def _minimap_fixture(character) -> None:
    """Deterministically place an activated character with map knowledge.

    Opted-in with ``ELOSERN_BROWSER_MINIMAP=1``. Runs after the world bootstrap
    would have synced the maps (this seed process syncs them itself, idempotent
    with the server's own ``at_server_start``). The character is relocated to
    南門 with knowledge recorded for the grid, wilderness, interior, and
    instance layers through the real arrival seams, so minimap browser journeys
    start with a populated visited set. No remote, LLM, or image service is
    involved.
    """
    from evennia.utils.search import search_object_by_tag
    from world.maps.bootstrap import (
        sync_grid,
        sync_service_interiors,
        sync_wilderness,
    )
    from world.maps.instance import spawn_instance_room
    from world.rules.map_knowledge import record_arrival

    sync_grid()
    sync_wilderness()
    sync_service_interiors()

    from evennia.contrib.grid.xyzgrid.xyzroom import XYZRoom

    def grid(xyz):
        return XYZRoom.objects.filter_xyz(xyz=xyz).first()

    # Registry probes (mirror the browser_fixtures_data harness idiom): the
    # city-gate row is the South Gate; the capital's wilderness entry authors
    # a second gate (the East Gate) whose grid room serves as the distant
    # remembered node.
    import importlib

    city_gate_registry = getattr(
        importlib.import_module("world.maps." + "city_gates"),
        "CITY" + "_GATE_REGISTRY",
    )
    SOUTH_GATE_XYZ = city_gate_registry[sorted(city_gate_registry)[0]].gate_xyz

    from web.browser_support.browser_fixtures_data import (
        first_live_wilderness_entry,
    )

    entry = first_live_wilderness_entry()
    second_gate = next(
        (gate for gate in entry.gates if gate.return_direction != "n"), None
    )
    NORTH_GATE_XYZ = (
        (*second_gate.grid_xy, second_gate.z_map_key) if second_gate else None
    )

    south_gate = grid(SOUTH_GATE_XYZ)
    if south_gate is None:
        return
    character.location = south_gate
    record_arrival(character)

    # Record a distant grid node (東門) so the grid layer at 南門 carries a
    # remembered node outside the visual range for focus journeys.
    north_gate = grid(NORTH_GATE_XYZ) if NORTH_GATE_XYZ is not None else None
    if north_gate is not None:
        character.location = north_gate
        record_arrival(character)
        character.location = south_gate

    # Synthetic install: the shipped bootstrap's 東門 gateway is not part of
    # the kit; the presenter resolves gateway rooms from the live
    # wilderness-entry registry, so record the kit gate's own grid room here.
    # (Under the shipped install this resolves to 東門 again — idempotent.)
    if os.environ.get("ELOSERN_BROWSER_SYNTH_CATALOGS") == "1":
        gate = second_gate
        kit_gate = grid(gate.grid_xy + (gate.z_map_key,)) if gate else None
        if kit_gate is not None and kit_gate.id != north_gate.id:
            character.location = kit_gate
            record_arrival(character)
            character.location = south_gate

    # Interior layer: the permanent guild hall. The place row is resolved by
    # kind from the CURRENT live registry (the harness probe), so the shipped
    # boot records the capital hall and the synthetic install resolves its own
    # kit row; under the kit no permanent interior exists (the kit settlement
    # has no grid map, so the place-driven sync warn-skips every place) and
    # the optional interior layer auto-skips exactly like the gate-room guard.
    from web.browser_support.browser_fixtures_data import live_place_by_kind

    halls = []
    hall_place = live_place_by_kind("guild_hall")
    if hall_place is not None:
        halls = search_object_by_tag(hall_place.key)
    if halls:
        character.location = halls[0]
        record_arrival(character)
        character.location = south_gate

    # Wilderness layer: place the character into the wilderness directly
    # (enter_wilderness moves without charging the clock -- the gate exit's
    # wilderness_move charge is a gameplay cost this fixture does not need;
    # only the visited node must be recorded), then return to 南門.
    if second_gate is not None:
        from evennia.contrib.grid.wilderness.wilderness import enter_wilderness
        from typeclasses.rooms import TerrainRoom
        from world.maps.wilderness_provider import WILDERNESS_NAME

        entered = enter_wilderness(
            character,
            coordinates=entry.approach_cell(second_gate),
            name=WILDERNESS_NAME,
        )
        if entered and isinstance(character.location, TerrainRoom):
            record_arrival(character)
            character.location = south_gate
            character.save()

    # Instance layer: spawn an ephemeral room reachable from 南門, record it,
    # then return the character to 南門. Attaching to the South Gate lets a
    # browser journey walk into the instance through the real exit.
    instance = spawn_instance_room(
        south_gate,
        {"prototype_parent": "instance_room", "key": "minimap-cave"},
        exit_key="進洞窟",
        return_key="離開",
        ttl_seconds=3600,
    )
    character.location = instance
    record_arrival(character)
    character.location = south_gate
    character.save()

