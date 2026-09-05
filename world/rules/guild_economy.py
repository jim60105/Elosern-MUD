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

from django.db import transaction
from evennia.utils.create import create_object

from world.observability import log_info, log_warn
from typeclasses.npcs import NPC, ensure_npc_adult_identity
from world.maps.bootstrap import sync_service_interiors
from world.rules.guild_config import get_catalog, load_catalog_into_cache
from world.rules.profession_assembly import (
    assemble_profession_components,
    project_row_kwargs,
)
from world.rules.profession_config import PROFESSION_COMPONENT_TYPES


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
    on the named integrity error before any mutation, including convergence.
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


def _row_anchor_class(row):
    """Return the component class anchoring reuse for one roster row.

    The anchor slot is the row's profession blueprint's FIRST component (the
    service-bearing class the row's ``service_id`` is recorded on).
    """
    first_type_key = row.profession.components[0].type_key
    return PROFESSION_COMPONENT_TYPES[first_type_key]


def _sync_service_host(row, room) -> NPC:
    """Create or reuse one stable adult NPC service host from a roster row.

    Reuse anchors on the component ``service_id``; a found host is never
    renamed and never has its authored title rewritten (runtime identity
    writes are forbidden — roster convergence deletes hosts instead of
    backfilling, design D8/D9). Creation persists the authored ``name`` as the
    entity key and the validated ``title`` once. Components attach ONLY
    through the shared profession-assembly helper: the row's blueprint plus
    its projected per-component identity kwargs (design D7).
    """
    from world.rules.npc_identity import validate_npc_name, validate_npc_title

    authored_map = project_row_kwargs(row.profession, row.service_id, row.authored_kwargs)
    anchor_slot = _row_anchor_class(row).get_component_slot()
    host = _find_service_host(row.service_id, anchor_slot)
    if host is None:
        host = create_object(NPC, key=validate_npc_name(row.name), location=room)
        host.npc_title = validate_npc_title(row.title)
        first_kwargs = authored_map[row.profession.components[0].type_key]
        # Commit-bound: sync runs inside startup transactions; a creation event
        # must never describe a host a later rollback destroyed.
        transaction.on_commit(
            lambda context={
                "char": host.key,
                "service": row.service_id,
                "shop": first_kwargs.get("shop_key") or first_kwargs.get("branch_key"),
                "profession": row.profession.key,
            }: log_info("guild_service_host_created", context=context)
        )
    elif host.location is not room:
        host.location = room
    if host.race is None:
        host.race = "human"
        host.apply_race_baseline()
    ensure_npc_adult_identity(host)
    assemble_profession_components(host, row.profession, authored_map)
    return host


def _converge_service_hosts(roster_service_ids: set[str]) -> None:
    """Delete live service hosts the roster no longer authorises (design D9).

    Roster membership is the component ``service_id``, never the entity key:
    an NPC is a convergence candidate when ANY service-bearing component
    (vocabulary class defining ``service_id``) carries an id absent from the
    roster. Deletion stays under the legacy cleanup's identity-shape
    discipline: a TITLELESS candidate is unambiguous development residue and
    is deleted (the following roster pass recreates a titleless malformed
    host from its row); a TITLED candidate that still holds at least one
    roster-matching anchor is ambiguous residue — deleting it would destroy a
    host the roster still wants, and a hand-authored NPC sharing a stale id
    cannot be distinguished — so it is kept with a named warning for manual
    repair. A titled candidate whose EVERY service anchor is roster-absent is
    a shrunk-away roster host and is deleted. An NPC carrying no service
    component is never touched, exactly as the pre-change cleanup. Each
    deletion emits one commit-bound info event (party bindings purge through
    the existing ``NPC.at_object_delete`` hook).
    """
    service_classes = [
        component_class
        for component_class in PROFESSION_COMPONENT_TYPES.values()
        if "service_id" in component_class._fields
    ]
    for host in list(NPC.objects.all_family()):
        claimed = []
        for component_class in service_classes:
            component = host.components.get(component_class.get_component_slot())
            if component is not None:
                claimed.append(component.service_id)
        if not claimed:
            continue
        stale = [service_id for service_id in claimed if service_id not in roster_service_ids]
        if not stale:
            continue
        if host.npc_title and any(service_id in roster_service_ids for service_id in claimed):
            log_warn(
                "guild_service_host_convergence_ambiguous",
                context={
                    "char": host.key,
                    "service": stale[0],
                    "services": list(claimed),
                },
            )
            continue
        host.delete()
        transaction.on_commit(
            lambda context={
                "char": host.key,
                "service": stale[0],
                "services": list(claimed),
            }: log_info("guild_service_host_convergence_removed", context=context)
        )


def sync_service_content() -> None:
    """Install the roster-declared permanent service content (design D7).

    ``world/rules/rulebook/guild_economy.yaml``'s ``service_hosts`` roster is
    the single truth for which hosts exist and what they carry; this is its
    pure interpreter: per row, resolve the anchor room by tag, find-or-create
    the adult host on the ``service_id`` anchor, and assemble the profession
    blueprint through the shared helper — never through a code-side component
    literal. A row whose room tag resolves to no room emits the named
    per-row warning and is skipped alone (the existing interiors-missing
    retry still runs first). Roster convergence runs before creation/reuse so
    a titleless malformed host is deleted and rebuilt from its row. Merchant
    stock is initialized only for merchants whose roster row completed sync.
    """
    catalog = get_catalog()
    roster = catalog.service_hosts
    rooms = {row.service_id: _room_by_tag(row.anchor_room) for row in roster}
    if any(room is None for room in rooms.values()):
        log_warn(
            "guild_economy_service_interiors_missing",
            context={"action": "sync_service_interiors_first"},
        )
        sync_service_interiors()
        rooms = {row.service_id: _room_by_tag(row.anchor_room) for row in roster}
    for row in roster:
        if rooms[row.service_id] is None:
            log_warn(
                "guild_service_host_anchor_room_missing",
                context={
                    "service": row.service_id,
                    "anchor_room": row.anchor_room,
                    "action": "skip_service_host_row",
                },
            )
    processable = [row for row in roster if rooms[row.service_id] is not None]
    if not processable:
        log_warn(
            "guild_economy_service_interiors_still_missing",
            context={"action": "skip_service_content"},
        )
        return
    # Fail closed on duplicate anchors BEFORE any mutation, convergence
    # deletion included — the unchanged single-host invariant: a named
    # integrity error means nothing is created, renamed, or deleted.
    for row in processable:
        _find_service_host(row.service_id, _row_anchor_class(row).get_component_slot())
    _converge_service_hosts({row.service_id for row in roster})
    synced_service_ids: set[str] = set()
    for row in processable:
        _sync_service_host(row, rooms[row.service_id])
        synced_service_ids.add(row.service_id)
    _initialize_merchant_stock(synced_service_ids)


def _initialize_merchant_stock(synced_service_ids: set[str]) -> None:
    """Initialize each synced shop's merchant stock only where absent (task 3.4).

    Existing live stock is preserved verbatim; only missing stock keys are
    seeded from the catalog's initial quantities. Only merchants whose roster
    row completed sync this run are seeded: a row skipped for an unresolved
    anchor mutates no live stock.
    """
    catalog = get_catalog()
    merchant_slot = PROFESSION_COMPONENT_TYPES["merchant"].get_component_slot()
    for host in NPC.objects.all_family():
        merchant = host.components.get(merchant_slot)
        if merchant is None:
            continue
        if merchant.service_id not in synced_service_ids:
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