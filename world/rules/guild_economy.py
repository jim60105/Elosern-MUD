"""Server-startup composition root for the deterministic guild economy (D-11).

``sync_guild_economy()`` is the single idempotent entry point called after
quest synchronization. It reloads the validated catalog against the current
quest definition registry, installs service content (interiors, NPC hosts,
components, and initial merchant stock), and registers the clock event
sources.

``restore_persisted_sessions()`` restores or terminates persisted
combat/examination sessions. It is owned by this module but called from
``at_server_start`` BEFORE wilderness population reconciliation, so a defeated
population monster is never deleted or respawned before its committed session
outcome is settled (fix-startup-session-restore-order D1).
"""

from evennia.utils.create import create_object

from world.observability import log_info, log_warn
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

# Stable service ANCHORS recorded on the service components. They are no
# longer entity keys: the host's key is its authored registry name
# (npc-title-authored-identities D3). Legacy hosts carrying these strings as
# db_key are stale development state discarded by the one-time cleanup below.
GUILD_SERVICE_KEY = "altoria_guild_master"
MERCHANT_SERVICE_KEY = "altoria_merchant"
_LEGACY_HOST_KEYS = (GUILD_SERVICE_KEY, MERCHANT_SERVICE_KEY)


def _room_by_tag(tag):
    from evennia.utils.search import search_object_by_tag

    rooms = search_object_by_tag(tag)
    return rooms[0] if rooms else None


class ServiceAnchorIntegrityError(RuntimeError):
    """Two live NPCs claim one service anchor; sync refuses to guess."""


def _find_service_host(service_id: str, component_slot: str) -> NPC | None:
    """Locate the host owning the service component with this ``service_id``.

    The component anchor — never the display ``key`` — is the reuse identity,
    so a registry name change can never orphan or duplicate a host (design
    D3). Scan shape follows ``_initialize_merchant_stock``. More than one live
    host on one anchor violates the single-host invariant; sync fails closed
    on the named integrity error instead of mutating an arbitrary pick.
    """
    matches = [
        host
        for host in NPC.objects.all_family()
        if (component := host.components.get(component_slot)) is not None
        and component.service_id == service_id
    ]
    if len(matches) > 1:
        raise ServiceAnchorIntegrityError(
            f"service anchor {service_id!r} is claimed by {len(matches)} hosts"
        )
    return matches[0] if matches else None


def _sync_service_host(service_id, host_name, host_title, room, component_specs) -> NPC:
    """Create or reuse one stable adult NPC service host with components.

    Reuse anchors on the component ``service_id``; a found host is never
    renamed and never has its authored title rewritten (runtime identity
    writes are forbidden — the cleanup path deletes stale pre-identity hosts
    instead of backfilling, design D3). Creation persists the authored
    ``host_name`` as the entity key and the validated ``host_title`` once.

    ``component_specs`` is a tuple of ``(ComponentClass, kwargs)`` pairs; each
    component instance is created against the host AFTER it exists so its
    ``.host`` binding matches the NPC being registered.
    """
    from world.rules.npc_identity import validate_npc_name, validate_npc_title

    anchor_slot = component_specs[0][0].get_component_slot()
    host = _find_service_host(service_id, anchor_slot)
    if host is None:
        host = create_object(NPC, key=validate_npc_name(host_name), location=room)
        host.npc_title = validate_npc_title(host_title)
        first_kwargs = component_specs[0][1]
        log_info(
            "guild_service_host_created",
            context={
                "char": host.key,
                "service": service_id,
                "shop": first_kwargs.get("shop_key") or first_kwargs.get("branch_key"),
            },
        )
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


def _cleanup_legacy_service_hosts() -> None:
    """Discard pre-identity hosts keyed by the retired ASCII service anchors.

    One-time cleanup for the unreleased development database (clean cutover,
    no backfill): the next sync recreates these hosts under their full authored
    identity. Idempotent — once removed, later syncs find nothing.

    Deletion is anchored on the retired host's *identity shape*, never the key
    alone: the NPC must still be titleless and carry the anchor component whose
    ``service_id`` equals the retired key (exactly what the pre-feature sync
    created). An unrelated NPC that merely shares a retired key (no component)
    is left untouched, and a titled same-key NPC is ambiguous residue the
    cleanup refuses to guess about (named warning, manual repair).
    """
    anchor_slots = {
        GUILD_SERVICE_KEY: GuildStaff.get_component_slot(),
        MERCHANT_SERVICE_KEY: Merchant.get_component_slot(),
    }
    for legacy_key in _LEGACY_HOST_KEYS:
        for host in NPC.objects.filter(db_key=legacy_key):
            component = host.components.get(anchor_slots[legacy_key])
            if component is None or component.service_id != legacy_key:
                continue  # Not the retired service host — unrelated same-key NPC.
            if host.npc_title:
                log_warn(
                    "guild_service_host_legacy_cleanup_ambiguous",
                    context={"char": legacy_key, "service": legacy_key},
                )
                continue
            log_info(
                "guild_service_host_legacy_cleanup",
                context={"char": legacy_key, "service": legacy_key},
            )
            host.delete()


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
            "guild_economy_service_interiors_missing",
            context={"action": "sync_service_interiors_first"},
        )
        sync_service_interiors()
        guild_hall = _room_by_tag(GUILD_HALL_TAG)
        general_store = _room_by_tag(GENERAL_STORE_TAG)
        if guild_hall is None or general_store is None:
            log_warn(
                "guild_economy_service_interiors_still_missing",
                context={"action": "skip_service_content"},
            )
            return

    from world.lore.guild import GUILD_BRANCH_REGISTRY
    from world.lore.shops import SHOP_REGISTRY

    _cleanup_legacy_service_hosts()
    branch = GUILD_BRANCH_REGISTRY["guild_branch_altoria"]
    store = SHOP_REGISTRY["altoria_general_store"]

    _sync_service_host(
        GUILD_SERVICE_KEY,
        branch.host_name,
        branch.host_title,
        guild_hall,
        (
            (GuildStaff, {"service_id": GUILD_SERVICE_KEY, "branch_key": "guild_branch_altoria"}),
            (GuildExaminer, {"service_id": GUILD_SERVICE_KEY, "branch_key": "guild_branch_altoria"}),
            (ScriptedDialogue, {"dialogue_key": "guild_staff"}),
        ),
    )
    _sync_service_host(
        MERCHANT_SERVICE_KEY,
        store.host_name,
        store.host_title,
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
            log_warn(
                "guild_economy_unknown_shop",
                context={"host": host.key, "shop_key": shop_key},
            )
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


def _register_clock_sources() -> None:
    """Register the caravan and shop-hours clock sources once (task 10.4)."""
    from world.rules.caravan_arrivals import register_caravan_arrivals
    from world.rules.shop_hours import register_shop_hours

    register_caravan_arrivals()
    register_shop_hours()


def restore_persisted_sessions() -> None:
    """Restore or diagnostically terminate persisted combat/exam sessions (tasks 7.11/8.x)."""
    from typeclasses.characters import PlayerCharacter

    for player in PlayerCharacter.objects.all_family():
        if player.db.active_combat is None:
            continue
        from world.rules.combat_session import restore_active_session

        try:
            restore_active_session(player)
        except Exception as error:
            log_warn(
                "rollback_restore_failed",
                exc=error,
                context={
                    "stage": "guild_economy_session",
                    "obj": str(player),
                    "key": "active_combat",
                },
            )