"""Exploration-menu seeding fixture.

Slice of the former ``web/tests/browser/seed.py`` module;
every body ships verbatim."""

import os


def _settle_admitted_portrait(entity, stable_key: str) -> None:
    """Give one present entity a named policy and an admitted DONE portrait.

    The completed record's output file is written under the runtime art store,
    so ``/art/portrait/character/<stable_key>.png`` serves real bytes from the
    project origin: the production exploration descriptor then carries the
    catalog key the presenter emits, and the committed art panel carries the
    image URL (with its face rectangle) beside it. The record is created,
    claimed and settled through the canonical queue, exactly as the worker
    would; nothing here invents a key or a URL.
    """
    from pathlib import Path

    from typeclasses.npcs import NPC, ensure_npc_canonical_age
    from web.tests.browser.seed.identity import FIXTURE_VALID_PNG
    from world.art.queue import claim, ensure, record_key, settle
    from world.art.store import ArtAssetRecord, ArtAssetStatus
    from world.art.subjects import character_subject_for

    entity.db.portrait_policy = {"mode": "named", "stable_key": stable_key}
    if isinstance(entity, NPC):
        # Without canonical ages the presenter resolves the entry to the
        # unavailable placeholder and emits no reference at all.
        ensure_npc_canonical_age(entity)
    entity.save()

    subject = character_subject_for(entity)
    if subject is None:
        raise RuntimeError(f"portrait fixture: no named subject for {stable_key}")
    ensure(subject, "browser exploration portrait fixture")
    # Eager startup sync enqueues the scene/monster records first; the subject
    # record enqueued last is claimed by a bounded number of rounds, and a
    # genuinely absent record fails loudly instead of timing out later.
    token = None
    for _ in range(20):
        claimed = claim(50)
        record = ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()
        if record is not None and record.db.status == ArtAssetStatus.IN_PROGRESS:
            token = str(record.db.generation_token)
            break
        if not claimed:
            break
    if token is None:
        raise RuntimeError(f"portrait fixture: record {stable_key} not claimed")

    root = Path(os.environ["ELOSERN_BROWSER_ART_ROOT"])
    identity = f"portrait/character/{stable_key}.png"
    (root / "portrait" / "character").mkdir(parents=True, exist_ok=True)
    (root / identity).write_bytes(FIXTURE_VALID_PNG)
    settle(
        subject,
        generation_token=token,
        status=ArtAssetStatus.DONE,
        output_identity=identity,
        error=None,
    )


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
    from typeclasses.characters import PlayerCharacter
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

    if os.environ.get("ELOSERN_BROWSER_COMPANION_LINEUP") == "1":
        from world.rules.party import PARTY_MAX_COMPANIONS, join_party, party_size

        # Under the synthetic catalogs the shipped races are not registered;
        # the only race the patched registry knows is the kit race.
        companion_race = "t_duskmari" if synth else "human"
        # The preset activation already bound its declared starting
        # companions; top the party up to the cap so the lineup journey
        # always sees exactly PARTY_MAX_COMPANIONS companions.
        for index in range(PARTY_MAX_COMPANIONS - party_size(character)):
            npc = create_object(LLMNPC, key=f"測試同行{index}", location=south_gate)
            npc.race = companion_race
            npc.apply_race_baseline()
            npc.db.age = npc.db.apparent_age = 30
            join_party(npc, character)

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

    if os.environ.get("ELOSERN_BROWSER_EXPLORATION_PORTRAITS") == "1":
        # Opt-in admitted media (restore-exploration-portrait-refs task 4.1):
        # the scripted host — an interact target — and a second present
        # player-character — a look-only bystander, never an interact target —
        # each get a real, server-served portrait, so the live producer packet
        # carries their decimal references and the committed art catalog
        # carries the matching URL. The extra look entity is exactly what the
        # dashed bystander medallion needs; no other fixture branch sees it.
        bystander = create_object(
            PlayerCharacter,
            key="旅人見習",
            location=south_gate,
        )
        bystander.db.age = 22
        bystander.db.apparent_age = 22
        bystander.save()
        _settle_admitted_portrait(host, "browser-exploration-host")
        _settle_admitted_portrait(bystander, "browser-exploration-traveller")

    print("seeded exploration fixture: south gate + scripted host + LLMNPC + goblin + defeated wolf + cave (+ boot-provisioned 荒野 gate)")

