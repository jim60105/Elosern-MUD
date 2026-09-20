"""Guild/quest/shop/inventory seeding fixture.

Slice of the former ``web/tests/browser/seed.py`` module;
every body ships verbatim."""

import os

from web.tests.browser.seed.services_synth import _services_fixture_synth


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

