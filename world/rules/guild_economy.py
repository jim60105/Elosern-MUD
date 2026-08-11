"""Server-startup composition root for the deterministic guild economy (D-11).

``sync_guild_economy()`` is the single idempotent entry point called after
quest synchronization. It reloads the validated catalog against the current
quest definition registry, installs service content (interiors, NPC hosts,
components, and initial merchant stock), registers the clock event sources,
and restores or terminates persisted combat/examination sessions.
"""

from evennia.utils.create import create_object
from evennia.utils.logger import log_warn

from typeclasses.components import (
    GuildExaminer,
    GuildStaff,
    Merchant,
    ScriptedDialogue,
)
from typeclasses.npcs import NPC, ensure_npc_adult_identity
from world.maps.bootstrap import (
    GENERAL_STORE_TAG,
    GUILD_HALL_TAG,
    sync_service_interiors,
)
from world.rules.guild_config import get_catalog, load_catalog_into_cache

GUILD_SERVICE_KEY = "altoria_guild_master"
MERCHANT_SERVICE_KEY = "altoria_merchant"


def _room_by_tag(tag):
    from evennia.utils.search import search_object_by_tag

    rooms = search_object_by_tag(tag)
    return rooms[0] if rooms else None


def _sync_service_host(key, room, component_specs) -> NPC:
    """Create or update one stable adult NPC service host with components.

    ``component_specs`` is a tuple of ``(ComponentClass, kwargs)`` pairs; each
    component instance is created against the host AFTER it exists so its
    ``.host`` binding matches the NPC being registered.
    """
    host = NPC.objects.filter(db_key=key).first()
    if host is None:
        host = create_object(NPC, key=key, location=room)
    elif host.location is not room:
        host.location = room
    if host.race is None:
        host.race = "human"
        host.apply_race_baseline()
    ensure_npc_adult_identity(host)
    for component_class, kwargs in component_specs:
        if not host.components.has(component_class.name):
            host.components.add(component_class.create(host, **kwargs))
    return host


def sync_service_content() -> None:
    """Install the permanent guild-hall and general-store service content.

    The guild hall hosts one adult NPC carrying ``GuildStaff`` and
    ``GuildExaminer`` for the Altoria branch; the general store hosts one adult
    NPC carrying ``Merchant`` for the general-store shop. Components carry
    stable identities; repeated startup attaches by name and never duplicates.
    Merchant stock is initialized only when absent (task 3.4).
    """
    catalog = get_catalog()
    guild_hall = _room_by_tag(GUILD_HALL_TAG)
    general_store = _room_by_tag(GENERAL_STORE_TAG)
    if guild_hall is None or general_store is None:
        log_warn(
            "sync_guild_economy: service interiors are missing; "
            "running sync_service_interiors first."
        )
        sync_service_interiors()
        guild_hall = _room_by_tag(GUILD_HALL_TAG)
        general_store = _room_by_tag(GENERAL_STORE_TAG)
        if guild_hall is None or general_store is None:
            log_warn(
                "sync_guild_economy: service interiors still missing; "
                "skipping service content."
            )
            return

    _sync_service_host(
        GUILD_SERVICE_KEY,
        guild_hall,
        (
            (GuildStaff, {"service_id": GUILD_SERVICE_KEY, "branch_key": "guild_branch_altoria"}),
            (GuildExaminer, {"service_id": GUILD_SERVICE_KEY, "branch_key": "guild_branch_altoria"}),
            (ScriptedDialogue, {"dialogue_key": "guild_staff"}),
        ),
    )
    _sync_service_host(
        MERCHANT_SERVICE_KEY,
        general_store,
        (
            (Merchant, {"service_id": MERCHANT_SERVICE_KEY, "shop_key": "altoria_general_store"}),
        ),
    )
    _initialize_merchant_stock()


def _initialize_merchant_stock() -> None:
    """Initialize each shop's merchant stock only where absent (task 3.4).

    Existing live stock is preserved verbatim; only missing stock keys are
    seeded from the catalog's initial quantities.
    """
    catalog = get_catalog()
    for host in NPC.objects.all_family():
        merchant = host.components.get(Merchant.get_component_slot())
        if merchant is None:
            continue
        shop_key = merchant.shop_key
        shop_config = catalog.shop_configs.get(shop_key)
        if shop_config is None:
            log_warn(f"sync_guild_economy: merchant {host.key} has unknown shop {shop_key!r}")
            continue
        current = dict(merchant.merchant_stock or {})
        changed = False
        for offer in shop_config.offers:
            if offer.item_key not in current:
                current[offer.item_key] = offer.initial_stock
                changed = True
        if changed:
            merchant.merchant_stock = current


def sync_guild_economy() -> None:
    """Run the full idempotent guild-economy startup synchronization."""
    catalog = load_catalog_into_cache()
    from world.rules.guild_config import register_catalog_offers

    register_catalog_offers(catalog)
    sync_service_content()
    _register_clock_sources()
    _restore_persisted_sessions()


def _register_clock_sources() -> None:
    """Register the caravan and shop-hours clock sources once (task 10.4)."""
    from world.rules.caravan_arrivals import register_caravan_arrivals
    from world.rules.shop_hours import register_shop_hours

    register_caravan_arrivals()
    register_shop_hours()


def _restore_persisted_sessions() -> None:
    """Restore or diagnostically terminate persisted combat/exam sessions (tasks 7.11/8.x)."""
    from typeclasses.characters import PlayerCharacter

    for player in PlayerCharacter.objects.all_family():
        if player.db.active_combat is None:
            continue
        from world.rules.combat_session import restore_active_session

        try:
            restore_active_session(player)
        except Exception as error:
            log_warn(f"guild_economy: could not restore session for {player.key}: {error}")