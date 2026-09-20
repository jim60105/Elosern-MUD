"""Options-surface seeding fixture.

Slice of the former ``web/tests/browser/seed.py`` module;
every body ships verbatim."""

import os


def _options_surface_fixture(character) -> None:
    """Deterministically prepare an options-surface fixture (webclient-options-surface).

    Opted-in with ``ELOSERN_BROWSER_OPTIONS_SURFACE=1``. Creates one dedicated
    plaza room (key ``選項測試廣場``, unique) hosting exactly one ``LLMNPC``
    (the freeform dialogue binding) and one living monster (the engage card),
    plus a second empty plaza-adjacent room (key ``選項測試空地``) whose
    CJK-labeled exits keep its degraded rule cards inside the suggestion label
    bounds. The unique room keys let every browser journey reset the
    character's location with ``@tel 選項測試廣場`` between tests. No remote,
    LLM, or image service is involved.
    """
    from evennia.contrib.grid.xyzgrid.xyzroom import XYZRoom
    from evennia.utils.create import create_object
    from typeclasses.exits import Exit
    from typeclasses.monsters import Monster
    from typeclasses.npcs import LLMNPC
    from typeclasses.rooms import Room
    from world.maps.bootstrap import SOUTH_GATE_XYZ, sync_grid
    from world.rules.map_knowledge import record_arrival

    if os.environ.get("ELOSERN_BROWSER_OPTIONS_SURFACE") != "1":
        return

    sync_grid()
    south_gate = XYZRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
    if south_gate is None:
        return

    from web.browser_support.browser_fixtures_data import (
        SYNTH_BPLAZA_PARTNER_KEY,
        SYNTH_EMPTY_GROUND_KEY,
        SYNTH_PLAZA_MONSTER_KEY,
        SYNTH_PLAZA_ROOM_KEY,
        first_live_monster_tier_key,
    )

    synth = os.environ.get("ELOSERN_BROWSER_SYNTH_CATALOGS") == "1"
    plaza_key = SYNTH_PLAZA_ROOM_KEY if synth else "選項測試廣場"
    empty_key = SYNTH_EMPTY_GROUND_KEY if synth else "選項測試空地"

    plaza = create_object(
        Room,
        key=plaza_key,
        nohome=True,
        location=None,
    )
    plaza.db.desc = "選項測試的廣場，四周牆上掛著未點亮的燈籠。"
    plaza.save()
    create_object(Exit, key="進入測試廣場", location=south_gate, destination=plaza)
    create_object(Exit, key="離開廣場", location=plaza, destination=south_gate)

    empty_ground = create_object(
        Room,
        key=empty_key,
        nohome=True,
        location=None,
    )
    empty_ground.db.desc = "選項測試的空地，地面鋪著乾淨的石板。"
    empty_ground.save()
    create_object(Exit, key="前往測試空地", location=plaza, destination=empty_ground)
    create_object(Exit, key="回到廣場", location=empty_ground, destination=plaza)

    create_object(
        LLMNPC, key=SYNTH_BPLAZA_PARTNER_KEY if synth else "廣場夥伴", location=plaza
    )

    wolf = create_object(
        Monster, key=SYNTH_PLAZA_MONSTER_KEY if synth else "廣場野狼", location=plaza
    )
    wolf.threat_tier = first_live_monster_tier_key()
    wolf.apply_monster_tier("floor")

    character.location = plaza
    # A map-knowledge record must exist for the local_map panel (and thus the
    # dock's move rows) to render; the plaza node is the fixture's start.
    record_arrival(character)
    character.save()
    print("seeded options-surface fixture: 選項測試廣場 + LLMNPC + wolf")

