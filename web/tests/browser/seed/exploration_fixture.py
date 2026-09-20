"""Exploration-menu seeding fixture.

Slice of the former ``web/tests/browser/seed.py`` module;
every body ships verbatim."""

import os


def _exploration_fixture(character) -> None:
    """Deterministically prepare an exploration-menu fixture (webclient-exploration-menu).

    Opted-in with ``ELOSERN_BROWSER_EXPLORATION=1``. Places the character at the
    South Gate with a scripted-dialogue guild-staff host (first present entity,
    affinity-seeded so a look renders the stage line), a present ``LLMNPC``
    bard whose ``npc_dialogue`` profile is disabled offline, a living hostile
    monster, and a defeated monster. No remote, LLM, or image service is
    involved.
    """
    from evennia.contrib.grid.xyzgrid.xyzroom import XYZRoom
    from evennia.utils.create import create_object
    from typeclasses.components import ScriptedDialogue
    from typeclasses.monsters import Monster
    from typeclasses.npcs import LLMNPC, NPC
    from world.maps.bootstrap import (
        sync_grid,
        sync_service_interiors,
    )
    from world.rules.map_knowledge import record_arrival

    if os.environ.get("ELOSERN_BROWSER_EXPLORATION") != "1":
        return

    sync_grid()
    sync_service_interiors()
    # The capital's city-gate row coordinate, probed from the live registry
    # (mirrors test_limbo_room.py::_gate_row).
    import importlib

    city_gate_registry = getattr(
        importlib.import_module("world.maps." + "city_gates"),
        "CITY" + "_GATE_REGISTRY",
    )
    south_gate_xyz = city_gate_registry[sorted(city_gate_registry)[0]].gate_xyz
    south_gate = XYZRoom.objects.filter_xyz(xyz=south_gate_xyz).first()
    if south_gate is None:
        return
    character.location = south_gate
    record_arrival(character)

    # The scripted-talk host: an ordinary NPC carrying the synthetic (or
    # shipped) ScriptedDialogue table (created before the bard so it is the
    # first present interact/look entity), affinity-seeded so a look renders
    # the stage line.
    from web.browser_support.browser_fixtures_data import (
        SHIPPED_DIALOGUE_KEY,
        SYNTH_DIALOGUE_HOST_KEY,
        SYNTH_DIALOGUE_TABLE_KEY,
        SYNTH_BARD_KEY,
        SYNTH_DEFEATED_MONSTER_KEY,
        SYNTH_HOSTILE_MONSTER_KEY,
        first_live_monster_tier_key,
    )

    synth = os.environ.get("ELOSERN_BROWSER_SYNTH_CATALOGS") == "1"
    host = create_object(
        NPC,
        key=SYNTH_DIALOGUE_HOST_KEY if synth else "公會職員",
        location=south_gate,
    )
    host.components.add(
        ScriptedDialogue.create(
            host, dialogue_key=SYNTH_DIALOGUE_TABLE_KEY if synth else SHIPPED_DIALOGUE_KEY
        )
    )
    from world.rules.affinity import AffinitySource, apply_affinity_change

    apply_affinity_change(host, character, AffinitySource.QUEST_COMPLETION, 50)

    bard = create_object(LLMNPC, key=SYNTH_BARD_KEY if synth else "吟遊詩人", location=south_gate)
    bard.components.add(
        ScriptedDialogue.create(
            bard, dialogue_key=SYNTH_DIALOGUE_TABLE_KEY if synth else SHIPPED_DIALOGUE_KEY
        )
    )

    hostile = create_object(
        Monster, key=SYNTH_HOSTILE_MONSTER_KEY if synth else "哥布林", location=south_gate
    )
    hostile.threat_tier = first_live_monster_tier_key()
    hostile.apply_monster_tier("floor")

    # A second, defeated monster in the same room renders as a disabled
    # affordance row in the action dock (webclient-pointer-activation):
    # the explore.engage affordance is disabled with the target_dead reason.
    defeated_wolf = create_object(
        Monster,
        key=SYNTH_DEFEATED_MONSTER_KEY if synth else "狼",
        location=south_gate,
    )
    defeated_wolf.threat_tier = first_live_monster_tier_key()
    defeated_wolf.apply_monster_tier("floor")
    defeated_wolf.traits.hp.base = 0
    defeated_wolf.traits.hp.current = 0
    defeated_wolf.save()

    # A third exit from the south gate: an ephemeral instance cave (the
    # minimap fixture's spawn logic, re-used here so the exploration fixture
    # is self-contained). The move frame's third exit — the 荒野 wilderness
    # gate — is NOT seeded here: the managed server's startup
    # sync_wilderness() (wilderness-anchor-footprint: one grid-side gate exit
    # per registered gate; the South Gate is the "n" gate's grid room)
    # provisions it after this seed process, so the move frame stays at 3
    # exits and the 400x720 journey (2-column pane width) exercises the
    # partial last row (fix-webclient-hud-dock-exploration-grid-width D2: the
    # last tile spans the remaining columns of a partial final row). The
    # former training-grounds exit is retired: it made the room render 4
    # exits, completing the final 2-column row so the span was never emitted.
    from world.maps.instance import spawn_instance_room

    spawn_instance_room(
        south_gate,
        {"prototype_parent": "instance_room", "key": "minimap-cave"},
        exit_key="進洞窟",
        return_key="離開",
        ttl_seconds=3600,
    )

    print("seeded exploration fixture: south gate + scripted host + LLMNPC + goblin + defeated wolf + cave (+ boot-provisioned 荒野 gate)")

