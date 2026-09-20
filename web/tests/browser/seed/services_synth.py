"""Synthetic-install variant of the services fixture.

Slice of the former ``web/tests/browser/seed.py`` module;
every body ships verbatim."""

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
        sync_grid,
        sync_service_interiors,
    )
    from world.lore.settlements.places import PLACE_REGISTRY

    # The shared catalog was assigned process-globally by the harness install
    # (same builder the server calls), so the board offer and shop rows are
    # already registered when the seed reaches this fixture.
    from world.rules import guild_config

    catalog = guild_config.get_catalog()

    sync_grid()
    sync_service_interiors()

    halls = search_object_by_tag(PLACE_REGISTRY["altoria_guild_hall"].key)
    stores = search_object_by_tag(PLACE_REGISTRY["altoria_general_store"].key)
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

