"""Deterministic account/character seeding for browser acceptance tests.

Run as a one-off process against a freshly migrated browser-test database:

    ELOSERN_BROWSER_* uv run --locked python -m web.tests.browser.seed

The harness runs ``evennia migrate`` first. This process then creates Account
#1 (the superuser Evennia's launcher requires), an activated
PlayerCharacter owned by that account, a start room, and places the character
in it. The world bootstrap (lore sync, maps, clock) is left to the
managed server's ``at_server_start`` hook. Everything is deterministic: no
network service, no LLM, and no random sampling beyond the validated magic
band seeded to its deterministic lower bound.

Importing this module has no side effects; all setup and database work happens
only when it is executed as ``python -m web.tests.browser.seed``.
"""

import os
from pathlib import Path

# Deterministic fixture identity. Password is fixed so Playwright can log in.
BROWSER_ACCOUNT_USERNAME = os.environ.get("ELOSERN_BROWSER_ACCOUNT", "browserplayer")
BROWSER_ACCOUNT_EMAIL = "browser@example.test"
BROWSER_ACCOUNT_PASSWORD = os.environ.get(
    "ELOSERN_BROWSER_PASSWORD", "ElosernBrowserTest!2026"
)
BROWSER_CHARACTER_NAME = os.environ.get("ELOSERN_BROWSER_CHARACTER", "BrowserTest")
BROWSER_ROOM_NAME = os.environ.get("ELOSERN_BROWSER_ROOM", "測試起點")

# A minimal valid 4x4 RGB PNG so a ``done`` art record's media URL actually
# decodes in the browser. Image-load-failure journeys abort this URL on the
# wire; the bytes must stay valid for the rendering journeys to pass.
FIXTURE_VALID_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000004000000040802000000"
    "269309290000001049444154789c6338d0e000470cc4710078521801"
    "1ec406c00000000049454e44ae426082"
)


# The pending-creation login account (webclient-character-creation-ui). A
# separate NON-superuser account keeps the pending shell's ownership intact:
# Evennia's one-time initial setup swaps the superuser account's typeclass with
# clean_attributes=True, which wipes _playable_characters on the superuser
# account and, because the server caches that account in process memory, an
# external repair cannot refresh it.
CREATION_ACCOUNT_USERNAME = os.environ.get("ELOSERN_BROWSER_CREATION_ACCOUNT", "browsercreator")
CREATION_ACCOUNT_EMAIL = "creation@example.test"
CREATION_ACCOUNT_PASSWORD = os.environ.get(
    "ELOSERN_BROWSER_CREATION_PASSWORD", "CreationBrowserTest!2026"
)


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
        GUILD_HALL_TAG,
        NORTH_GATE_XYZ,
        SOUTH_GATE_XYZ,
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

    # Interior layer: the permanent guild hall.
    halls = search_object_by_tag(GUILD_HALL_TAG)
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


def _art_fixture(character, room) -> None:
    """Deterministically prepare art records for browser acceptance.

    Opted-in with ``ELOSERN_BROWSER_ART=<mode>``. Each mode places the
    character in a room that carries the validated ``scene_archetype`` seam and
    settles art records (done/pending/failed) whose output files are written
    under the runtime art store, so browser journeys can assert the real scene
    renderer and portrait catalog without any image service. ``missing`` leaves
    records untouched (missing placeholders). No remote, LLM, or image service
    is involved.
    """
    import os

    from evennia.utils.create import create_object
    from typeclasses.monsters import Monster
    from typeclasses.rooms import GridRoom
    from world.art.queue import ensure, settle
    from world.art.store import ArtAssetStatus
    from world.art.subjects import (
        ArtSubject,
        ArtSubjectKind,
        character_subject_for,
    )

    mode = os.environ.get("ELOSERN_BROWSER_ART", "")
    if not mode or os.environ.get("ELOSERN_BROWSER_SERVICES"):
        return

    from web.browser_support.browser_fixtures_data import (
        SHIPPED_ART_ARCHETYPE,
        SHIPPED_DIALOGUE_KEY,
        SHIPPED_MONSTER_TIER_KEY,
        SYNTH_ART_ARCHETYPE,
        SYNTH_DIALOGUE_HOST_KEY,
        SYNTH_DIALOGUE_TABLE_KEY,
        first_live_monster_tier_key,
        scene_archetype_registered,
    )

    synth = os.environ.get("ELOSERN_BROWSER_SYNTH_CATALOGS") == "1"
    archetype = SYNTH_ART_ARCHETYPE if synth else SHIPPED_ART_ARCHETYPE
    if not scene_archetype_registered(archetype):
        raise AssertionError("art fixture archetype must be a registered scene")

    art_room = create_object(
        GridRoom, key="art 合成場景" if synth else "art 酒館場景", nohome=True, location=None
    )
    art_room.scene_archetype = archetype
    character.location = art_room
    character.db.portrait_policy = {
        "mode": "named",
        "stable_key": f"browser-{character.pk}",
    }
    # A present named-policy NPC and a living monster so combat catalog tests
    # have both a dialogue host and a generic monster in the room.
    from typeclasses.npcs import NPC, ensure_npc_canonical_age

    host = create_object(
        NPC, key=SYNTH_DIALOGUE_HOST_KEY if synth else "酒館老闆", location=art_room
    )
    from typeclasses.components import ScriptedDialogue

    host.components.add(
        ScriptedDialogue.create(
            host, dialogue_key=SYNTH_DIALOGUE_TABLE_KEY if synth else SHIPPED_DIALOGUE_KEY
        )
    )
    # A named portrait policy on the dialogue host: the actor is excluded from
    # its own exploration-mode portrait catalog (art_view), so the focusable
    # catalog entry is the host's; settling it done gives the ArtPanel's
    # portrait full-view control (v-if="entry.url") a URL to render.
    host.db.portrait_policy = {
        "mode": "named",
        "stable_key": "browser-host",
    }
    # The host must carry canonical age attributes, or the presenter resolves
    # its catalog entry to the unavailable placeholder (status/url both None)
    # even when its art record is done.
    ensure_npc_canonical_age(host)
    host.save()
    monster = create_object(
        Monster,
        key="合成燼殼蟲" if synth else "酒館灰狼",
        location=art_room,
        nohome=True,
    )
    monster.threat_tier = (
        first_live_monster_tier_key() if synth else SHIPPED_MONSTER_TIER_ATTR
    )
    # Band position (not a registry key): free-form in either mode.
    monster.apply_monster_tier(SHIPPED_MONSTER_TIER_KEY)
    character.save()

    art_root = os.environ.get("ELOSERN_BROWSER_ART_ROOT")
    if not art_root:
        return
    root = Path(art_root)
    (root / "scene").mkdir(parents=True, exist_ok=True)

    scene = ArtSubject(ArtSubjectKind.SCENE, archetype)
    ensure(scene, "desc")
    if mode == "done":
        identity = f"scene/{archetype}.png"
        (root / identity).write_bytes(FIXTURE_VALID_PNG)
        from world.art.queue import claim, record_key
        from world.art.store import ArtAssetRecord

        # Ensure the named portrait records exist and claim every pending
        # record (the startup sync enqueued ~10 scenes, the monster tiers,
        # and the named portraits) so the scene and both named portraits
        # settle as done, giving the ArtPanel's portrait full-view control
        # (v-if="entry.url") a URL to render.
        host_subject = character_subject_for(host)
        actor_subject = character_subject_for(character)
        for subject in (actor_subject, host_subject):
            if subject is not None:
                ensure(subject, "desc")
        claimed = claim(50)
        tokens = {record.db_key: str(record.db.generation_token) for record in claimed}
        settle(
            scene,
            generation_token=tokens[record_key(scene)],
            status=ArtAssetStatus.DONE,
            output_identity=identity,
            error=None,
        )
        (root / "portrait" / "character").mkdir(parents=True, exist_ok=True)
        for subject, stable_key in (
            (actor_subject, f"browser-{character.pk}"),
            (host_subject, "browser-host"),
        ):
            if subject is None:
                continue
            # Fail loudly if the portrait record was not claimed (claim budget
            # 50 would otherwise leave it PENDING and settle is a silent
            # no-op), instead of a later browser timeout.
            record = ArtAssetRecord.objects.filter(db_key=record_key(subject)).first()
            if record is None:
                raise RuntimeError(f"art fixture: no art record for {stable_key}")
            if record.db.status != ArtAssetStatus.IN_PROGRESS:
                raise RuntimeError(
                    f"art fixture: portrait record {stable_key} not claimed "
                    f"(status={record.db.status}); claim budget too small"
                )
            portrait_identity = f"portrait/character/{stable_key}.png"
            (root / portrait_identity).write_bytes(FIXTURE_VALID_PNG)
            settle(
                subject,
                generation_token=tokens[record_key(subject)],
                status=ArtAssetStatus.DONE,
                output_identity=portrait_identity,
                error=None,
            )
    elif mode == "failed":
        from world.art.queue import claim

        claimed = claim(10)
        settle(
            scene,
            generation_token=str(claimed[0].db.generation_token),
            status=ArtAssetStatus.FAILED,
            output_identity=None,
            error="fixture",
        )
    elif mode == "pending":
        from world.art.queue import claim

        claim(10)
        pending = ArtSubject(ArtSubjectKind.SCENE, archetype)
        ensure(pending, "desc")
        record = __import__(
            "world.art.queue", fromlist=["record_key"]
        ).record_key(pending)
        record_obj = __import__(
            "world.art.store", fromlist=["ArtAssetRecord"]
        ).ArtAssetRecord.objects.filter(db_key=record).first()
        record_obj.db.status = ArtAssetStatus.PENDING
        record_obj.save()
    print(f"seeded art fixture: {mode}")


def _services_fixture(character) -> None:
    """Deterministically prepare a guild/quest/shop/inventory fixture.

    Opted-in with ``ELOSERN_BROWSER_SERVICES=<mode>``. Runs after the world
    bootstrap would have synced the maps and guild economy (this seed process
    syncs them itself, idempotent with the server's own ``at_server_start``).
    Each mode places the character with the exact canonical state a browser
    journey needs; no remote, LLM, or image service is involved.
    """
    import os

    from evennia.utils.search import search_object_by_tag
    from typeclasses.components import GuildStaff, Merchant
    from web.browser_support.browser_fixtures_data import (
        SHIPPED_GUILD_OFFER_KEY,
        SHIPPED_MEAL_KEY,
        SHIPPED_POTION_KEY,
        SHIPPED_WEAPON_KEY,
    )
    from world.maps.bootstrap import (
        GENERAL_STORE_TAG,
        GUILD_HALL_TAG,
        sync_grid,
        sync_service_interiors,
    )
    from world.quests.catalog import register_catalog
    from world.rules.clock import get_world_clock
    from world.rules.guild import register_adventurer
    from world.rules.guild_config import load_catalog_into_cache, register_catalog_offers
    from world.rules.guild_offers import accept_guild_offer
    from world.rules.guild_economy import sync_guild_economy
    from world.rules.surfaces import write_counter_trait

    mode = os.environ.get("ELOSERN_BROWSER_SERVICES", "")
    if not mode:
        return

    if os.environ.get("ELOSERN_BROWSER_SYNTH_CATALOGS") == "1":
        _services_fixture_synth(character, mode)
        return

    register_catalog()
    sync_grid()
    sync_service_interiors()
    catalog = load_catalog_into_cache()
    register_catalog_offers(catalog)
    sync_guild_economy()

    halls = search_object_by_tag(GUILD_HALL_TAG)
    stores = search_object_by_tag(GENERAL_STORE_TAG)
    hall = halls[0] if halls else None
    store = stores[0] if stores else None
    staff = None
    if hall is not None:
        staff = next(
            (
                obj
                for obj in hall.contents
                if getattr(obj, "components", None) is not None
                and obj.components.has(GuildStaff.name)
            ),
            None,
        )
    merchant_host = None
    if store is not None:
        merchant_host = next(
            (
                obj
                for obj in store.contents
                if getattr(obj, "components", None) is not None
                and obj.components.has(Merchant.name)
            ),
            None,
        )

    def place(room):
        character.location = room
        character.save()

    if mode == "guild_hall":
        place(hall)
        character.db.wallet = 1000
        character.save()
    elif mode == "guild_registered_board":
        place(hall)
        register_adventurer(character, staff=staff)
        character.db.wallet = 1000
        character.db.inventory = [SHIPPED_POTION_KEY]
        character.save()
    elif mode == "guild_active_quest":
        place(hall)
        register_adventurer(character, staff=staff)
        character.db.wallet = 1000
        accept_guild_offer(character, staff, SHIPPED_GUILD_OFFER_KEY)
        character.save()
    elif mode == "guild_completed_quest":
        place(hall)
        register_adventurer(character, staff=staff)
        character.db.wallet = 1000
        accept_guild_offer(character, staff, SHIPPED_GUILD_OFFER_KEY)
        from world.quests.runtime import (
            definition_for,
            fulfill_record,
            read_records,
            to_storage,
        )

        record = read_records(character)[0]
        completed = fulfill_record(record, definition_for(record))
        character.db.quest_log = [to_storage(completed)]
        character.save()
    elif mode == "guild_exam":
        place(hall)
        register_adventurer(character, staff=staff)
        write_counter_trait(character, "guild_merit", 50)
        character.db.wallet = 1000
        character.save()
    elif mode == "quest_away_from_clerk":
        # quest-drawer-split: an accepted guild quest held AWAY from any
        # clerk — the quest book must read and track anywhere, and the
        # drawer must replace the counter with its honest no-clerk marker.
        original_room = character.location
        place(hall)
        register_adventurer(character, staff=staff)
        character.db.wallet = 1000
        accept_guild_offer(character, staff, SHIPPED_GUILD_OFFER_KEY)
        place(original_room)
        character.save()
    elif mode == "store_open":
        place(store)
        character.db.wallet = 1000
        character.db.inventory = [
            SHIPPED_MEAL_KEY,
            SHIPPED_MEAL_KEY,
            SHIPPED_POTION_KEY,
        ]
        get_world_clock()._persist(12 * 3600)
        character.save()
    elif mode == "store_closed":
        place(store)
        character.db.wallet = 1000
        character.db.inventory = [SHIPPED_MEAL_KEY]
        get_world_clock()._persist(3 * 3600)
        character.save()
    elif mode == "inventory_only":
        character.db.wallet = 42
        character.db.inventory = [
            SHIPPED_MEAL_KEY,
            SHIPPED_MEAL_KEY,
            SHIPPED_WEAPON_KEY,
            SHIPPED_POTION_KEY,
        ]
        character.save()
    elif mode == "inventory_actions":
        # add-inventory-item-actions browser journeys: one injured holder of
        # two healing potions and one sword — use is enabled until the first
        # use closes the HP gap, then the stable hp_full refusal governs.
        character.db.wallet = 42
        character.db.inventory = [
            SHIPPED_POTION_KEY,
            SHIPPED_POTION_KEY,
            SHIPPED_WEAPON_KEY,
        ]
        maximum = int(character.traits.hp.max)
        character.traits.hp.current = maximum - 20
        character.save()
    print(f"seeded services fixture: {mode}")


def _services_fixture_synth(character, mode: str) -> None:
    """Synthetic-install variant of the services fixture.

    Under ``install_synthetic_catalogs()`` every shipped guild-economy seam
    (``load_catalog_into_cache``/``register_catalog_offers``/
    ``sync_guild_economy``) resolves shipped YAML keys the t_-only registries
    reject, and the server-side ``sync_guild_economy`` boot step is degraded.
    So this fixture installs the process-global catalog directly from the
    probe helpers, registers the board offer explicitly, and creates the hall
    clerk / store merchant / exam examiner hosts manually through the same
    component seams the roster sync would use. Every key is a kit ``t_`` row
    or authored fixture identity.
    """
    from evennia.utils.create import create_object
    from evennia.utils.search import search_object_by_tag
    from typeclasses.components import GuildExaminer, GuildStaff, Merchant
    from typeclasses.npcs import NPC, ensure_npc_canonical_age
    from world.rules.clock import get_world_clock
    from world.rules.guild import register_adventurer
    from world.rules.guild_offers import accept_guild_offer
    from world.rules.surfaces import write_counter_trait
    from web.browser_support.browser_fixtures_data import (
        SYNTH_INVENTORY_BY_MODE,
        SYNTH_SHOP_KEY,
    )
    from world.tests.synthetic_data import SYNTH_GUILD_BRANCH_KEY

    from world.maps.bootstrap import (
        GENERAL_STORE_TAG,
        GUILD_HALL_TAG,
        sync_grid,
        sync_service_interiors,
    )

    # The shared catalog was assigned process-globally by the harness install
    # (same builder the server calls), so the board offer and shop rows are
    # already registered when the seed reaches this fixture.
    from world.rules import guild_config

    catalog = guild_config.get_catalog()

    sync_grid()
    sync_service_interiors()

    halls = search_object_by_tag(GUILD_HALL_TAG)
    stores = search_object_by_tag(GENERAL_STORE_TAG)
    hall = halls[0] if halls else None
    store = stores[0] if stores else None
    if hall is None or store is None:
        raise AssertionError("services fixture: service interiors missing")

    def _make_host(key: str, room) -> NPC:
        host = next(
            (obj for obj in room.contents if obj.key == key),
            None,
        )
        if host is None:
            host = create_object(NPC, key=key, location=room)
            ensure_npc_canonical_age(host)
            host.save()
        return host

    def _ensure_component(host, component_cls, **fields):
        slot = component_cls.get_component_slot()
        if not host.components.has(component_cls.name):
            host.components.add(component_cls.create(host, **fields))
        return host.components.get(slot)

    # Authored host names are free-form fixture identity; the branch/shop
    # identity is the kit rows. service_binding stays unset (co-presence).
    staff = _make_host("合成公會職員", hall)
    _ensure_component(staff, GuildStaff, branch_key=SYNTH_GUILD_BRANCH_KEY)
    merchant_host = _make_host("合成商店店員", store)
    _ensure_component(
        merchant_host,
        Merchant,
        shop_key=SYNTH_SHOP_KEY,
        merchant_stock={
            rule.item_key: rule.initial_stock
            for rule in catalog.shop_configs[SYNTH_SHOP_KEY].offers
        },
    )
    examiner = _make_host("合成公會考官", hall)
    _ensure_component(examiner, GuildExaminer, branch_key=SYNTH_GUILD_BRANCH_KEY)

    def place(room):
        character.location = room
        character.save()

    inventory = SYNTH_INVENTORY_BY_MODE.get(mode)
    if mode == "guild_hall":
        place(hall)
        character.db.wallet = 1000
        character.save()
    elif mode == "guild_registered_board":
        place(hall)
        register_adventurer(character, staff=staff)
        character.db.wallet = 1000
        character.db.inventory = list(inventory)
        character.save()
    elif mode == "guild_active_quest":
        place(hall)
        register_adventurer(character, staff=staff)
        character.db.wallet = 1000
        from web.browser_support.browser_fixtures_data import (
            SYNTH_GUILD_OFFER_QUEST_KEY,
        )

        accept_guild_offer(character, staff, SYNTH_GUILD_OFFER_QUEST_KEY)
        character.save()
    elif mode == "guild_completed_quest":
        place(hall)
        register_adventurer(character, staff=staff)
        character.db.wallet = 1000
        from web.browser_support.browser_fixtures_data import (
            SYNTH_GUILD_OFFER_QUEST_KEY,
        )

        accept_guild_offer(character, staff, SYNTH_GUILD_OFFER_QUEST_KEY)
        from world.quests.runtime import (
            definition_for,
            fulfill_record,
            read_records,
            to_storage,
        )

        record = read_records(character)[0]
        completed = fulfill_record(record, definition_for(record))
        character.db.quest_log = [to_storage(completed)]
        character.save()
    elif mode == "guild_exam":
        place(hall)
        register_adventurer(character, staff=staff)
        write_counter_trait(character, "guild_merit", 50)
        character.db.wallet = 1000
        character.save()
    elif mode == "quest_away_from_clerk":
        from web.browser_support.browser_fixtures_data import (
            SYNTH_GUILD_OFFER_QUEST_KEY,
        )

        original_room = character.location
        place(hall)
        register_adventurer(character, staff=staff)
        character.db.wallet = 1000
        accept_guild_offer(character, staff, SYNTH_GUILD_OFFER_QUEST_KEY)
        place(original_room)
        character.save()
    elif mode in ("store_open", "store_closed"):
        place(store)
        character.db.wallet = 1000
        character.db.inventory = list(inventory)
        get_world_clock()._persist(
            12 * 3600 if mode == "store_open" else 3 * 3600
        )
        character.save()
    elif mode == "inventory_only":
        character.db.wallet = 42
        character.db.inventory = list(inventory)
        character.save()
    elif mode == "inventory_actions":
        character.db.wallet = 42
        character.db.inventory = list(inventory)
        maximum = int(character.traits.hp.max)
        character.traits.hp.current = maximum - 20
        character.save()
    print(f"seeded services fixture (synth): {mode}")


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
        SOUTH_GATE_XYZ,
        sync_grid,
        sync_service_interiors,
    )
    from world.rules.map_knowledge import record_arrival

    if os.environ.get("ELOSERN_BROWSER_EXPLORATION") != "1":
        return

    sync_grid()
    sync_service_interiors()
    south_gate = XYZRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
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


def _titles_fixture(character) -> None:
    """Deterministically prepare a title-codex fixture (title-codex-removal).

    Opted-in with ``ELOSERN_BROWSER_TITLES=1``. Banks two unlocked guild fixed
    titles (leaving others locked), two epithets — the first auto-equips, the
    newer one is removable — and persists one nomination ballot, so the codex
    window renders locked/unlocked rows, the ★ mark, the server-computed
    ``can_remove`` flags, and the 提名中 tab without any LLM call.
    """
    import os

    if os.environ.get("ELOSERN_BROWSER_TITLES", "") != "1":
        return

    from world.rules.clock import get_world_clock
    from world.rules.titles import (
        bank_epithet,
        bank_fixed,
        persist_nomination_ballot,
    )
    from web.browser_support.browser_fixtures_data import (
        SHIPPED_TITLE_RANK_E_KEY,
        SHIPPED_TITLE_RANK_F_KEY,
        SYNTH_TITLE_BANKED_KEYS,
    )

    tick = get_world_clock().tick
    synth = os.environ.get("ELOSERN_BROWSER_SYNTH_CATALOGS") == "1"
    for banked in (SYNTH_TITLE_BANKED_KEYS if synth else (SHIPPED_TITLE_RANK_F_KEY, SHIPPED_TITLE_RANK_E_KEY)):
        bank_fixed(character, banked, tick)
    bank_epithet(character, "南門新客", "初入南門。", tick)
    bank_epithet(character, "破城先鋒", "率先破門。", tick + 1)
    persist_nomination_ballot(
        character,
        [{"display": "夜襲之人", "basis": "夜半三度出入敵陣。"}],
    )
    print("seeded titles fixture: fixed 2 banked, epithets 2, one ballot")


def main() -> None:
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE", "web.tests.browser.browser_settings"
    )

    import django

    django.setup()

    import evennia

    evennia._init()

    # Synthetic-catalog process install (kit design D2b): the kit imports
    # Evennia contrib code that needs evennia._init() first, so the flag
    # check lives here rather than in settings load. The harness shares ONE
    # install path with the server process (``browser_startstop``): import the
    # shipped-rulebook cross-validators BEFORE the swap, install the kit,
    # redirect the boot quest catalog, graft the entry rank, and assign the
    # shared synthetic guild-economy catalog.
    from web.tests.browser.browser_startstop import _install_synthetic_catalogs_if_flagged

    _install_synthetic_catalogs_if_flagged()

    from evennia.utils.create import create_account, create_object

    from typeclasses.accounts import Account
    from typeclasses.characters import PlayerCharacter
    from typeclasses.monsters import Monster
    from typeclasses.rooms import Room
    from world.rules.character_creation import (
        CharacterCreationRequest,
        activate_player_character,
        resolve_starting_profile,
    )

    def balanced_allocations(race_key: str, subrace_key: str | None = None) -> dict[str, int]:
        """Spend the exact starting budget deterministically from the profile bounds."""
        profile = resolve_starting_profile(race_key, subrace_key)
        remaining = profile.budget
        result: dict[str, int] = {}
        for key, (lower, upper) in profile.bounds:
            value = min(upper - lower, remaining)
            result[key] = value
            remaining -= value
        if remaining != 0:
            raise AssertionError("starting profile budget exceeds allocatable spans")
        return result

    account = create_account(
        BROWSER_ACCOUNT_USERNAME,
        BROWSER_ACCOUNT_EMAIL,
        BROWSER_ACCOUNT_PASSWORD,
        typeclass=Account,
        is_superuser=True,
    )

    if os.environ.get("ELOSERN_BROWSER_CREATION") == "1":
        # A pending-creation account (webclient-character-creation-ui): the
        # auto-created shell is creation-pending with an empty trait set and no
        # activation, exactly as a freshly registered account sees it.
        # Optionally a validated custom draft is saved so browser journeys can
        # resume at the custom_filled stage. The South Gate and world clock are
        # created by the managed server's own at_server_start bootstrap.
        # Evennia's initial setup assumes ObjectDB #1 is the superuser
        # character and #2 is 虛境 (the renamed starting room): it locks #1 with
        # ``puppet:false()`` and
        # wipes the superuser account's attributes. So #1 is a dedicated dummy
        # superuser character and the pending shell is #3, owned by a
        # non-superuser account the initial setup never touches.
        superuser_character = create_object(
            PlayerCharacter, key=BROWSER_CHARACTER_NAME, nohome=True
        )
        account.at_post_create_character(superuser_character)
        superuser_character.db_account = account
        room = create_object(Room, key=BROWSER_ROOM_NAME, nohome=True)
        superuser_character.location = room
        superuser_character.home = room
        superuser_character.save()
        account.db._last_puppet = superuser_character

        pending = create_object(PlayerCharacter, key="creation-shell", nohome=True)
        creator = create_account(
            CREATION_ACCOUNT_USERNAME,
            CREATION_ACCOUNT_EMAIL,
            CREATION_ACCOUNT_PASSWORD,
            typeclass=Account,
        )
        creator.at_post_create_character(pending)
        pending.db_account = creator
        pending.location = room
        pending.home = room
        pending.save()
        creator.db._last_puppet = pending
        if os.environ.get("ELOSERN_BROWSER_CREATION_PRESET_DRAFT") == "1":
            from world.rules.creation_wizard import save_preset_draft

            from web.browser_support.browser_fixtures_data import SHIPPED_PRESET_KEY

            save_preset_draft(
                creator,
                pending,
                "t_pale_wren"
                if os.environ.get("ELOSERN_BROWSER_SYNTH_CATALOGS") == "1"
                else SHIPPED_PRESET_KEY,
            )
            pending.save()
        elif os.environ.get("ELOSERN_BROWSER_CREATION_DRAFT") == "1":
            from world.rules.creation_wizard import save_custom_draft

            _synth = os.environ.get("ELOSERN_BROWSER_SYNTH_CATALOGS") == "1"
            from web.browser_support.browser_fixtures_data import (
                SHIPPED_DRAFT_RACE,
                SHIPPED_DRAFT_SUBRACE,
            )

            save_custom_draft(
                creator,
                pending,
                CharacterCreationRequest(
                    mode="custom",
                    display_name="草稿角色",
                    age=21,
                    apparent_age=21,
                    race="t_duskmari" if _synth else SHIPPED_DRAFT_RACE,
                    subrace="t_duskmari_evensong" if _synth else SHIPPED_DRAFT_SUBRACE,
                    allocations=balanced_allocations(
                        "t_duskmari" if _synth else SHIPPED_DRAFT_RACE,
                        "t_duskmari_evensong" if _synth else SHIPPED_DRAFT_SUBRACE,
                    ),
                ),
            )
            pending.save()
        print(
            f"seeded pending creation account={creator.key} "
            f"character={pending.key} pending=True"
        )
        return

    character = create_object(PlayerCharacter, key=BROWSER_CHARACTER_NAME, nohome=True)
    account.at_post_create_character(character)
    account.db._last_puppet = character

    room = create_object(Room, key=BROWSER_ROOM_NAME, nohome=True)
    character.location = room
    character.home = room
    character.save()

    if os.environ.get("ELOSERN_BROWSER_SYNTH_CATALOGS") == "1":
        # Under the synthetic install every shipped catalog is t_-only, so the
        # base character activates from the kit's own preset card (its race,
        # subrace, skills, and starting items are all t_-keyed). The
        # shipped-prose fixtures below are not synthetic-aware; the flag is
        # documented as combinable with no other fixture flag.
        request = CharacterCreationRequest(
            mode="preset",
            preset_key="t_pale_wren",
            skip_portrait=True,
        )
    else:
        from web.browser_support.browser_fixtures_data import (
            SHIPPED_BASE_RACE,
            SHIPPED_BASE_SUBRACE,
        )

        request = CharacterCreationRequest(
            mode="custom",
            display_name=BROWSER_CHARACTER_NAME,
            age=20,
            apparent_age=20,
            race=SHIPPED_BASE_RACE,
            subrace=SHIPPED_BASE_SUBRACE,
            allocations=balanced_allocations(SHIPPED_BASE_RACE, SHIPPED_BASE_SUBRACE),
            # The art fixture below settles classic records deterministically;
            # the automatic gallery request (gallery-autogen-retrofit) must never
            # race it, so the seeded activation carries the explicit skip flag.
            skip_portrait=True,
        )
    result = activate_player_character(account, character, request)

    if os.environ.get("ELOSERN_BROWSER_MINIMAP") == "1":
        _minimap_fixture(character)

    _services_fixture(character)

    _art_fixture(character, room)
    _exploration_fixture(character)
    _options_surface_fixture(character)
    _titles_fixture(character)

    # Deterministic combat fixtures (webclient-combat-menu): grant active
    # skills covering every TargetSpec and spawn two living monsters in the
    # start room so browser tests can ``engage`` one through the real server.
    # The mastery passive additionally activates the freeform scale step for
    # the ladder skill (element-mastery-freeform-casting), exercised by the
    # scaled cast acceptance test.  ``grant_lineage`` closes the skill lineage
    # and seeds prerequisite proficiency so every requested ACTIVE skill is
    # actually castable under the lineage gate.  ``rungs`` raises the ladder
    # skill's OWN proficiency to the ladder's top level
    # (use-driven-skill-lineage DC5).  The grant set is mode-derived: the kit
    # rows under the synthetic install, the shipped rows otherwise.
    from world.rules.tests.combat_fixtures import grant_lineage
    from web.browser_support.browser_fixtures_data import (
        SHIPPED_COMBAT_ACTIVE_SKILLS,
        SHIPPED_COMBAT_DEBUFF_KEY,
        SHIPPED_COMBAT_LADDER_LEVEL,
        SHIPPED_COMBAT_LADDER_SKILL,
        SHIPPED_COMBAT_MONSTERS,
        SHIPPED_COMBAT_PASSIVE_SKILLS,
        SHIPPED_MONSTER_TIER_ATTR,
        SHIPPED_MONSTER_TIER_KEY,
        SYNTH_COMBAT_ACTIVE_SKILLS,
        SYNTH_COMBAT_DEBUFF_KEY,
        SYNTH_COMBAT_LADDER_LEVEL,
        SYNTH_COMBAT_LADDER_SKILL,
        SYNTH_COMBAT_MONSTERS,
        SYNTH_COMBAT_PASSIVE_SKILLS,
        first_live_monster_tier_key,
    )

    synth = os.environ.get("ELOSERN_BROWSER_SYNTH_CATALOGS") == "1"
    grant_lineage(
        character,
        list(SYNTH_COMBAT_ACTIVE_SKILLS if synth else SHIPPED_COMBAT_ACTIVE_SKILLS),
        list(SYNTH_COMBAT_PASSIVE_SKILLS if synth else SHIPPED_COMBAT_PASSIVE_SKILLS),
        rungs={
            (SYNTH_COMBAT_LADDER_SKILL if synth else SHIPPED_COMBAT_LADDER_SKILL): (
                SYNTH_COMBAT_LADDER_LEVEL if synth else SHIPPED_COMBAT_LADDER_LEVEL
            )
        },
    )
    # A persistent buff gives the status panel a deterministic
    # applied-modifier condition for viewport assertions.
    from world.rules.buffs import _add_buff

    if synth:
        # The kit debuff stacks unique_per_source; a fixture source key names
        # the seed itself (free-form data, never a catalog key).
        _add_buff(character, SYNTH_COMBAT_DEBUFF_KEY, source_key="browser-seed")
    else:
        _add_buff(character, SHIPPED_COMBAT_DEBUFF_KEY)
    for monster_key, hp in (SYNTH_COMBAT_MONSTERS if synth else SHIPPED_COMBAT_MONSTERS):
        monster = create_object(Monster, key=monster_key, nohome=True)
        monster.threat_tier = first_live_monster_tier_key() if synth else SHIPPED_MONSTER_TIER_ATTR
        monster.apply_monster_tier(SHIPPED_MONSTER_TIER_KEY)
        monster.traits.hp.base = hp
        monster.traits.hp.current = hp
        monster.location = room
        monster.save()
    print(
        f"seeded account={account.key} character={result.display_name} "
        f"race={result.race} magic_power={result.magic_power}"
    )


if __name__ == "__main__":
    main()
