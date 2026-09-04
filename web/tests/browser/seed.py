"""Deterministic account/character seeding for browser acceptance tests.

Run as a one-off process against a freshly migrated browser-test database:

    ELOSERN_BROWSER_* uv run --locked python -m web.tests.browser.seed

The harness runs ``evennia migrate`` first. This process then creates Account
#1 (the superuser Evennia's launcher requires), an activated adult
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
        from world.lore.wilderness_entry import WILDERNESS_ENTRY_REGISTRY
        from world.maps.wilderness_provider import WILDERNESS_NAME

        entry = WILDERNESS_ENTRY_REGISTRY["capital_altoria"]
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
    if not mode:
        return

    from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY

    archetype = "tavern_interior"
    if archetype not in SCENE_ARCHETYPE_REGISTRY:
        raise AssertionError("art fixture archetype must be a registered scene")

    art_room = create_object(
        GridRoom, key="art 酒館場景", nohome=True, location=None
    )
    art_room.scene_archetype = archetype
    character.location = art_room
    character.db.portrait_policy = {
        "mode": "named",
        "stable_key": f"browser-{character.pk}",
    }
    # A present named-policy NPC and a living monster so combat catalog tests
    # have both a dialogue host and a generic monster in the room.
    from typeclasses.npcs import NPC, ensure_npc_adult_identity

    host = create_object(NPC, key="酒館老闆", location=art_room)
    from typeclasses.components import ScriptedDialogue
    from world.rules.dialogue import GUILD_STAFF_DIALOGUE_KEY

    host.components.add(ScriptedDialogue.create(host, dialogue_key=GUILD_STAFF_DIALOGUE_KEY))
    # A named portrait policy on the dialogue host: the actor is excluded from
    # its own exploration-mode portrait catalog (art_view), so the focusable
    # catalog entry is the host's; settling it done gives the ArtPanel's
    # portrait full-view control (v-if="entry.url") a URL to render.
    host.db.portrait_policy = {
        "mode": "named",
        "stable_key": "browser-host",
    }
    # The host must pass the portrait adult gate (age/apparent_age >= 18),
    # or the presenter resolves its catalog entry to the unavailable
    # placeholder (status/url both None) even when its art record is done.
    ensure_npc_adult_identity(host)
    host.save()
    monster = create_object(Monster, key="酒館灰狼", location=art_room, nohome=True)
    monster.threat_tier = "low"
    monster.apply_monster_tier("floor")
    character.save()

    art_root = os.environ.get("ELOSERN_BROWSER_ART_ROOT")
    if not art_root:
        return
    root = Path(art_root)
    (root / "scene").mkdir(parents=True, exist_ok=True)

    scene = ArtSubject(ArtSubjectKind.SCENE, archetype)
    ensure(scene, "desc")
    if mode == "done":
        identity = "scene/tavern_interior.png"
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
        claim(50)
        settle(scene, status=ArtAssetStatus.DONE, output_identity=identity, error=None)
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
            settle(subject, status=ArtAssetStatus.DONE, output_identity=portrait_identity, error=None)
    elif mode == "failed":
        from world.art.queue import claim

        claim(10)
        settle(scene, status=ArtAssetStatus.FAILED, output_identity=None, error="fixture")
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
        character.db.inventory = ["healing_potion"]
        character.save()
    elif mode == "guild_active_quest":
        place(hall)
        register_adventurer(character, staff=staff)
        character.db.wallet = 1000
        accept_guild_offer(character, staff, "introductory_hunt")
        character.save()
    elif mode == "guild_completed_quest":
        place(hall)
        register_adventurer(character, staff=staff)
        character.db.wallet = 1000
        accept_guild_offer(character, staff, "introductory_hunt")
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
    elif mode == "store_open":
        place(store)
        character.db.wallet = 1000
        character.db.inventory = ["meal", "meal", "healing_potion"]
        get_world_clock()._persist(12 * 3600)
        character.save()
    elif mode == "store_closed":
        place(store)
        character.db.wallet = 1000
        character.db.inventory = ["meal"]
        get_world_clock()._persist(3 * 3600)
        character.save()
    elif mode == "inventory_only":
        character.db.wallet = 42
        character.db.inventory = ["meal", "meal", "plain_sword", "healing_potion"]
        character.save()
    elif mode == "inventory_actions":
        # add-inventory-item-actions browser journeys: one injured holder of
        # two healing potions and one sword — use is enabled until the first
        # use closes the HP gap, then the stable hp_full refusal governs.
        character.db.wallet = 42
        character.db.inventory = ["healing_potion", "healing_potion", "plain_sword"]
        maximum = int(character.traits.hp.max)
        character.traits.hp.current = maximum - 20
        character.save()
    print(f"seeded services fixture: {mode}")


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

    # The scripted-talk host: an ordinary NPC carrying the guild_staff
    # ScriptedDialogue table (created before the bard so it is the first
    # present interact/look entity), affinity-seeded so a look renders the
    # stage line.
    host = create_object(NPC, key="公會職員", location=south_gate)
    host.components.add(ScriptedDialogue.create(host, dialogue_key="guild_staff"))
    from world.rules.affinity import AffinitySource, apply_affinity_change

    apply_affinity_change(host, character, AffinitySource.QUEST_COMPLETION, 50)

    bard = create_object(LLMNPC, key="吟遊詩人", location=south_gate)
    bard.components.add(
        ScriptedDialogue.create(bard, dialogue_key="guild_staff")
    )

    goblin = create_object(Monster, key="哥布林", location=south_gate)
    goblin.threat_tier = "low"
    goblin.apply_monster_tier("floor")

    # A second, defeated monster in the same room renders as a disabled
    # affordance row in the action dock (webclient-pointer-activation):
    # the explore.engage affordance is disabled with the target_dead reason.
    defeated_wolf = create_object(Monster, key="狼", location=south_gate)
    defeated_wolf.threat_tier = "low"
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

    plaza = create_object(
        Room,
        key="選項測試廣場",
        nohome=True,
        location=None,
    )
    plaza.db.desc = "選項測試的廣場，四周牆上掛著未點亮的燈籠。"
    plaza.save()
    create_object(Exit, key="進入測試廣場", location=south_gate, destination=plaza)
    create_object(Exit, key="離開廣場", location=plaza, destination=south_gate)

    empty_ground = create_object(
        Room,
        key="選項測試空地",
        nohome=True,
        location=None,
    )
    empty_ground.db.desc = "選項測試的空地，地面鋪著乾淨的石板。"
    empty_ground.save()
    create_object(Exit, key="前往測試空地", location=plaza, destination=empty_ground)
    create_object(Exit, key="回到廣場", location=empty_ground, destination=plaza)

    create_object(LLMNPC, key="廣場夥伴", location=plaza)

    wolf = create_object(Monster, key="廣場野狼", location=plaza)
    wolf.threat_tier = "low"
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

    tick = get_world_clock().tick
    bank_fixed(character, "g_f_rank", tick)
    bank_fixed(character, "g_e_rank", tick)
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
        # auto-created adult shell is creation-pending with an empty trait set
        # and no activation, exactly as a freshly registered account sees it.
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

            save_preset_draft(creator, pending, "human_wanderer")
            pending.save()
        elif os.environ.get("ELOSERN_BROWSER_CREATION_DRAFT") == "1":
            from world.rules.creation_wizard import save_custom_draft

            save_custom_draft(
                creator,
                pending,
                CharacterCreationRequest(
                    mode="custom",
                    display_name="草稿角色",
                    age=21,
                    apparent_age=21,
                    race="beastfolk",
                    subrace="foxkin",
                    allocations=balanced_allocations("beastfolk", "foxkin"),
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

    request = CharacterCreationRequest(
        mode="custom",
        display_name=BROWSER_CHARACTER_NAME,
        age=20,
        apparent_age=20,
        race="human",
        subrace="human_commoner",
        allocations=balanced_allocations("human", "human_commoner"),
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
    # wind_mastery additionally activates the freeform scale step for
    # wind_blade (element-mastery-freeform-casting), exercised by the scaled
    # cast acceptance test.  ``grant_lineage`` closes the skill lineage and
    # seeds prerequisite proficiency so every requested ACTIVE skill is
    # actually castable under the lineage gate (fire_ball pulls fire_arrow).
    # ``rungs`` raises wind_blade's OWN proficiency to the ladder's top level
    # (use-driven-skill-lineage DC5: the skill-anchored ladder unlocks
    # 0.25/0.5/1/2/4 at its own levels 0/1/3/6/10; wind_blade has no
    # consuming edges, so its derived tip cap is the full 10).
    from world.rules.tests.combat_fixtures import grant_lineage

    grant_lineage(
        character,
        ["fire_ball", "wind_blade", "status_disguise", "concentration"],
        ["defense_instinct", "wind_mastery"],
        rungs={"wind_blade": 10},
    )
    # A persistent poisoned buff gives the status panel a deterministic
    # applied-modifier condition (agility -10%) for viewport assertions.
    from world.rules.buffs import _add_buff

    _add_buff(character, "poisoned")
    for index, (monster_key, hp) in enumerate(
        (("goblin", 200), ("wolf", 200)), start=1
    ):
        monster = create_object(Monster, key=monster_key, nohome=True)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
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
