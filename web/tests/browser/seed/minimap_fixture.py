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
        NORTH_GATE_XYZ,
        SOUTH_GATE_XYZ,
        sync_grid,
        sync_service_interiors,
        sync_wilderness,
    )
    from world.lore.settlements.places import PLACE_REGISTRY
    from world.maps.instance import spawn_instance_room
    from world.rules.map_knowledge import record_arrival

    sync_grid()
    sync_wilderness()
    sync_service_interiors()

    from evennia.contrib.grid.xyzgrid.xyzroom import XYZRoom

    def grid(xyz):
        return XYZRoom.objects.filter_xyz(xyz=xyz).first()

    south_gate = grid(SOUTH_GATE_XYZ)
    if south_gate is None:
        return
    character.location = south_gate
    record_arrival(character)

    # Record a distant grid node (北門) so the grid layer at 南門 carries a
    # remembered node outside the visual range for focus journeys.
    north_gate = grid(NORTH_GATE_XYZ)
    if north_gate is not None:
        character.location = north_gate
        record_arrival(character)
        character.location = south_gate

    # Synthetic install: the shipped bootstrap's 北門 gateway is not part of
    # the kit; the presenter resolves gateway rooms from the live
    # wilderness-entry registry, so record the kit gate's own grid room here.
    # (Under the shipped install this resolves to 北門 again — idempotent.)
    if os.environ.get("ELOSERN_BROWSER_SYNTH_CATALOGS") == "1":
        from web.browser_support.browser_fixtures_data import (
            first_live_wilderness_entry,
        )

        gate = first_live_wilderness_entry().gate_for("s")
        kit_gate = grid(gate.grid_xy + (gate.z_map_key,)) if gate else None
        if kit_gate is not None and kit_gate.id != north_gate.id:
            character.location = kit_gate
            record_arrival(character)
            character.location = south_gate

    # Interior layer: the permanent guild hall.
    halls = search_object_by_tag(PLACE_REGISTRY["altoria_guild_hall"].key)
    if halls:
        character.location = halls[0]
        record_arrival(character)
        character.location = south_gate

    # Wilderness layer: place the character into the wilderness directly
    # (enter_wilderness moves without charging the clock -- the gate exit's
    # wilderness_move charge is a gameplay cost this fixture does not need;
    # only the visited node must be recorded), then return to 南門.
    if north_gate is not None:
        from evennia.contrib.grid.wilderness.wilderness import enter_wilderness
        from typeclasses.rooms import TerrainRoom
        from web.browser_support.browser_fixtures_data import (
            first_live_wilderness_entry,
        )
        from world.maps.wilderness_provider import WILDERNESS_NAME

        entry = first_live_wilderness_entry()
        entered = enter_wilderness(
            character,
            coordinates=entry.approach_cell(entry.gate_for("s")),
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

