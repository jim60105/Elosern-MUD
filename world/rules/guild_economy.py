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

A synchronized host is identified by its canonical authored profile identity —
the place's ``host_profile_key``, recorded on the live NPC as its profile
provenance — never by a capability, a capability order, a display name, a
location or a component-level service identifier (npc-service-host-identity).
"""

from copy import deepcopy
from typing import Any

from django.db import transaction
from evennia.utils.create import create_object

from world.art.official_refs import NPC_PROFILE_PROVENANCE_ATTRIBUTE
from world.observability import log_info, log_warn
from world.lore.npc_profiles import NPC_PROFILE_REGISTRY
from world.rules.npc_persona import initialize_npc_persona
from typeclasses.npcs import NPC, ensure_npc_canonical_age
from world.lore.settlements.places import PLACE_REGISTRY
from world.maps.bootstrap import sync_service_interiors
from world.rules.guild_config import get_catalog, load_catalog_into_cache
from world.rules.profession_assembly import (
    assemble_profession_components,
    component_attribute_keys,
    converge_managed_components,
    project_row_kwargs,
    resolve_component_plan,
)
from world.rules.profession_config import PROFESSION_COMPONENT_TYPES
from world.rules.surfaces import (
    restore_component_state,
    snapshot_attributes,
)

#: Source ownership recorded on every host this sync applies: the tag alone
#: authorizes whole-row retirement, and only in the source-owned category. It
#: never authorizes any component-level inference.
SERVICE_HOST_TAG = "service_host"
CONTENT_SOURCE_TAG_CATEGORY = "content_source"

#: The managed capability set this owner reconciles is the closed capability
#: vocabulary itself — one declaration of the managed slots, not a second list.
MANAGED_TYPE_KEYS: frozenset[str] = frozenset(PROFESSION_COMPONENT_TYPES)

#: Host-level attributes the source batch may write on a reused host: the
#: component slot list, the canonical age pair the existing age owner fills,
#: and the authored arousal seed the church component may apply once.
_HOST_ATTRIBUTE_SURFACES = ("age", "apparent_age", "component_names", "sexual")


def _host_attribute_surfaces() -> tuple[str, ...]:
    """Every host attribute this batch may write, derived from the vocabulary."""
    keys = list(_HOST_ATTRIBUTE_SURFACES)
    for type_key in sorted(MANAGED_TYPE_KEYS):
        keys.extend(component_attribute_keys(type_key))
    return tuple(keys)


#: Snapshot/restore surface list for one reused host (component fields are
#: derived from the vocabulary so a new field can never be forgotten here).
HOST_ATTRIBUTE_SURFACES: tuple[str, ...] = _host_attribute_surfaces()


def _room_by_tag(tag):
    from evennia.utils.search import search_object_by_tag

    rooms = search_object_by_tag(tag)
    return rooms[0] if rooms else None


class ServiceHostIntegrityError(RuntimeError):
    """Canonical host identity is duplicated or owned by another author."""


def _find_service_host(host_key: str) -> NPC | None:
    """Return the one NPC carrying this canonical authored host identity.

    The identity is the profile provenance every created host records — never
    a component order, a component service id, a display name or a location.
    More than one claimant violates the one-person invariant and fails closed
    before any write. A single claimant that is an authored persistent
    adventurer is an ownership conflict: the roster never takes over a person
    another source owns, even when that source reuses the same profile key.
    """
    from world.rules.human_guild_hosts import PERSON_ATTRIBUTE

    matches = [
        npc
        for npc in NPC.objects.all_family()
        if npc.attributes.get(NPC_PROFILE_PROVENANCE_ATTRIBUTE) == host_key
    ]
    if len(matches) > 1:
        raise ServiceHostIntegrityError(
            f"canonical host identity {host_key!r} is claimed by {len(matches)} NPCs"
        )
    if not matches:
        return None
    host = matches[0]
    if host.attributes.has(PERSON_ATTRIBUTE):
        raise ServiceHostIntegrityError(
            f"canonical host identity {host_key!r} belongs to an authored "
            "persistent adventurer, which no service roster may take over"
        )
    return host


def _authored_shop_identity(authored_map) -> str | None:
    """The shop or branch the row's components author, if any (no order tie)."""
    for kwargs in authored_map.values():
        identity = kwargs.get("shop_key") or kwargs.get("branch_key")
        if identity:
            return identity
    return None


def _apply_authored_initial_arousal(host: NPC, authored_map, attached: list[str]) -> None:
    """Seed a clergy host's spawn-data arousal from its authored kwarg.

    The church design authors a small raised initial arousal on clergy hosts
    through the ``initial_arousal`` identity kwarg of the ``church_host``
    component (design §5.3: sanctuary NPCs start already-aroused). The seed
    applies exactly when this sync newly attached a ``church_host`` — host
    creation and the converged reuse of a pre-change host alike — and never
    overwrites an existing raw baseline (an imported or previously authored
    ``db.sexual`` wins), so a second sync changes nothing.
    """
    if "church_host" not in attached:
        return
    level = authored_map.get("church_host", {}).get("initial_arousal")
    if level is None:
        return
    if getattr(host, "db", None) is None or getattr(host.db, "sexual", None) is not None:
        return
    from world.rules.church import build_initial_arousal_baseline

    host.db.sexual = build_initial_arousal_baseline(level)


def _sync_service_host(row, room, host=None, *, created: list[NPC]) -> NPC:
    """Create or converge one source-managed host from a roster row.

    A reused host keeps its dbref, name, title, persona, traits, inventory,
    relationships and location: this sync never relocates, renames, retitles or
    rebuilds anything identity-shaped. What it does converge is the declaration:
    the managed capability set (add missing, remove obsolete) and the authored
    configuration allowlist the shared assembly writes. Components attach ONLY
    through the shared profession-assembly helper.

    ``created`` receives a newly created instance as soon as the object exists,
    before the rest of its initialization can fail, so the surrounding batch can
    evict it if it has to roll back.
    """
    authored_map = project_row_kwargs(row.profession, row.service_id, row.authored_kwargs)
    profile = NPC_PROFILE_REGISTRY.get(row.profile_key)
    prof_age = profile.age if profile else None
    prof_app_age = profile.apparent_age if profile else None
    if host is None:
        host = _create_and_initialize_host(
            row, room, authored_map, profile, created=created
        )
    else:
        # The existing canonical-age owner fills only absent values; it never
        # resets a live identity.
        ensure_npc_canonical_age(host, age=prof_age, apparent_age=prof_app_age)
    attached = assemble_profession_components(
        host, row.profession, authored_map, anchor_room=room
    )
    declared = frozenset(
        type_key
        for type_key, _kwargs in resolve_component_plan(row.profession, authored_map)
    )
    converge_managed_components(
        host,
        managed_type_keys=MANAGED_TYPE_KEYS,
        declared_type_keys=declared,
    )
    _apply_authored_initial_arousal(host, authored_map, attached)
    # Normal sync is what marks a host source-owned: from here on the roster
    # lifecycle owner may retire it once its whole declaration is gone.
    host.tags.add(SERVICE_HOST_TAG, category=CONTENT_SOURCE_TAG_CATEGORY)
    return host


def _create_and_initialize_host(
    row, room, authored_map, profile=None, *, created: list[NPC]
) -> NPC:
    """Build, baseline, initialize persona, and schedule creation event."""
    from world.rules.npc_identity import validate_npc_name, validate_npc_title

    host = create_object(NPC, key=validate_npc_name(row.name), location=room)
    created.append(host)
    host.npc_title = validate_npc_title(row.title)
    place = PLACE_REGISTRY.get(row.anchor_room)
    if place is None:
        raise RuntimeError(
            f"roster row {row.service_id!r} anchors at {row.anchor_room!r}, "
            "which has no place registry row"
        )
    host.race = place.host_race
    host.subrace = place.host_subrace
    host.sex = place.host_sex
    host.apply_race_baseline()
    if profile is None:
        profile = NPC_PROFILE_REGISTRY[row.profile_key]
    ensure_npc_canonical_age(host, age=profile.age, apparent_age=profile.apparent_age)
    initialize_npc_persona(
        host,
        profile.card.to_record(),
        {"kind": "profile", "profile": row.profile_key},
    )
    if profile.social_identities:
        from world.rules.social_identity import set_social_identities
        set_social_identities(host, profile.social_identities)

    # Authored official-content provenance (official-content-provenance): the
    # host's stable authored profile key, written once at creation inside the
    # same transaction as every other authored attribute, so the official
    # reference layer can resolve ``(npc, <profile key>)`` without consulting
    # the numeric role tier, the display key, or a service anchor. Creation
    # only: a reused host is never rewritten (never-rename/never-retitle), and
    # this attribute is the canonical identity every later sync reuses.
    host.attributes.add(NPC_PROFILE_PROVENANCE_ATTRIBUTE, row.profile_key)
    # Commit-bound: sync runs inside startup transactions; a creation event
    # must never describe a host a later rollback destroyed.
    transaction.on_commit(
        lambda context={
            "char": host.key,
            "service": row.service_id,
            "shop": _authored_shop_identity(authored_map),
            "profession": row.profession.key,
            "profile": row.profile_key,
        }: log_info("guild_service_host_created", context=context)
    )
    return host


def _host_service_ids(host: NPC) -> list[str]:
    """The service ids this host currently declares, in vocabulary order."""
    service_ids: list[str] = []
    for type_key in sorted(MANAGED_TYPE_KEYS):
        slot = PROFESSION_COMPONENT_TYPES[type_key].get_component_slot()
        component = host.components.get(slot)
        service_id = getattr(component, "service_id", None) if component else None
        if service_id is not None:
            service_ids.append(service_id)
    return service_ids


def _undeclared_source_hosts(declared_host_keys: frozenset[str]) -> list[NPC]:
    """Live source-managed hosts whose complete declaration is gone.

    Retirement authority is the source-ownership tag and nothing else: an NPC
    without it survives whatever components, service ids or titles it carries,
    and a tagged host whose canonical identity is still declared survives even
    when every capability was removed from its row.
    """
    return [
        host
        for host in NPC.objects.all_family()
        if host.tags.has(SERVICE_HOST_TAG, category=CONTENT_SOURCE_TAG_CATEGORY)
        and host.attributes.get(NPC_PROFILE_PROVENANCE_ATTRIBUTE)
        not in declared_host_keys
    ]


def _capture_retirement(host: NPC) -> dict[str, Any]:
    """Capture the state a whole-row retirement mutates outside the host.

    The existing deletion hooks purge party bindings (and possession control)
    on the owner side; those writes are not transaction-aware in process, so the
    batch that retires a host must be able to put them back if a later row
    fails.
    """
    from world.rules.party import membership_owner, party_ids, party_meta

    state: dict[str, Any] = {
        "pk": host.pk,
        "char": host.key,
        "service_ids": _host_service_ids(host),
    }
    owner = membership_owner(host)
    if owner is None:
        return state
    state["owner"] = owner
    state["party"] = party_ids(owner)
    state["meta"] = deepcopy(party_meta(owner))
    state["member"] = host.db.party_member
    if host.db.possessed_by is not None:
        from world.rules.possession import snapshot_party_control

        state["control"] = snapshot_party_control(owner, host)
    return state


def _retire_source_hosts(hosts: list[NPC], retired: list[dict[str, Any]]) -> None:
    """Delete each retired host through the existing lifecycle and hooks.

    Each retirement leaves the idmapper before it deletes, so a rollback makes
    the next read load the restored rows instead of a dead cached instance.
    ``retired`` receives each host's captured owner-side state BEFORE the next
    deletion can fail, so the caller's rollback path can put back what a
    partially completed retirement already changed.
    """
    for host in hosts:
        state = _capture_retirement(host)
        host.flush_from_cache(force=True)
        context = {
            "char": state["char"],
            "service": state["service_ids"][0] if state["service_ids"] else None,
            "services": state["service_ids"],
        }
        if not host.delete():
            log_warn("guild_service_host_retirement_refused", context=context)
            continue
        retired.append(state)
        transaction.on_commit(
            lambda context=context: log_info(
                "guild_service_host_convergence_removed", context=context
            )
        )


def _restore_retirements(states: list[dict[str, Any]]) -> None:
    """Put back the owner-side surfaces a rolled-back retirement changed."""
    for state in states:
        owner = state.get("owner")
        if owner is None:
            continue
        from world.rules.party import restore_membership_surfaces

        try:
            restore_membership_surfaces(
                owner,
                state["party"],
                {state["pk"]: state["member"]},
                state["meta"],
            )
        except Exception as error:
            log_warn(
                "rollback_restore_failed",
                exc=error,
                context={"stage": "retired_host_party", "obj": state["char"]},
            )
        control = state.get("control")
        if control is None:
            continue
        restored = NPC.objects.filter(pk=state["pk"]).first()
        if restored is None:
            continue
        from world.rules.possession import restore_party_control

        try:
            restore_party_control(owner, restored, control)
        except Exception as error:
            log_warn(
                "rollback_restore_failed",
                exc=error,
                context={"stage": "retired_host_control", "obj": state["char"]},
            )


def _restore_batch(
    *,
    created: list[NPC],
    reused: list[tuple[NPC, dict]],
    retired: list[dict[str, Any]],
) -> None:
    """Restore every in-process surface a rolled-back batch may have changed."""
    for host in created:
        try:
            host.flush_from_cache(force=True)
        except Exception as error:
            log_warn(
                "rollback_restore_failed",
                exc=error,
                context={"stage": "created_host_idmapper", "obj": "?"},
            )
    for host, snapshots in reused:
        restore_component_state(host, snapshots)
    _restore_retirements(retired)


def _validate_roster(roster) -> None:
    """Reject an unusable roster before any persistent write."""
    seen: set[str] = set()
    for row in roster:
        if row.profile_key not in NPC_PROFILE_REGISTRY:
            raise ServiceHostIntegrityError(
                f"service {row.service_id!r} names profile_key {row.profile_key!r} "
                "which is absent from the NPC profile registry"
            )
        prof = NPC_PROFILE_REGISTRY[row.profile_key]
        for field_name in ("age", "apparent_age"):
            val = getattr(prof, field_name, None)
            if type(val) is not int or not (0 <= val <= 10000):
                raise ServiceHostIntegrityError(
                    f"service {row.service_id!r} profile {row.profile_key!r} has invalid "
                    f"{field_name} {val!r}; must be an integer in 0..10000"
                )
        if row.host_key in seen:
            raise ServiceHostIntegrityError(
                f"canonical host identity {row.host_key!r} is declared by more "
                "than one roster row"
            )
        seen.add(row.host_key)


def sync_service_content() -> None:
    """Install the roster-declared permanent service content (design D7).

    The place-derived roster is the single truth for which hosts exist and what
    they carry; this is its pure interpreter: per row, resolve the anchor room
    by tag, find-or-create the host on its canonical authored identity, and
    assemble the profession blueprint through the shared helper — never through
    a code-side component literal.

    Order is the contract. Every row's authored identities are validated and
    every canonical identity is resolved (duplicate and person-ownership
    conflicts fail closed) BEFORE the first persistent write, including the
    interiors repair. The row operation then runs as ONE transaction: root
    component convergence for every resolvable row, the stock initializer for
    hosts that are still uninitialized, and whole-row retirement of source-owned
    hosts whose declaration is gone. Any failure rolls the database back and
    restores the in-process attribute, tag and component caches of every reused
    host, evicts every object this batch created, and puts back the owner-side
    party/possession surfaces a retirement had already touched.

    A row whose room tag resolves to no room emits the named per-row warning
    and is skipped alone (the existing interiors-missing retry still runs
    first). An empty or wholly unresolvable roster still retires the hosts it
    no longer authorizes.
    """
    catalog = get_catalog()
    roster = catalog.service_hosts
    _validate_roster(roster)
    # Room- and write-independent identity preflight for EVERY roster row.
    hosts = {row.host_key: _find_service_host(row.host_key) for row in roster}
    declared = frozenset(row.host_key for row in roster)
    rooms = {row.host_key: _room_by_tag(row.anchor_room) for row in roster}
    if any(room is None for room in rooms.values()):
        log_warn(
            "guild_economy_service_interiors_missing",
            context={"action": "sync_service_interiors_first"},
        )
        sync_service_interiors()
        rooms = {row.host_key: _room_by_tag(row.anchor_room) for row in roster}
    for row in roster:
        if rooms[row.host_key] is None:
            log_warn(
                "guild_service_host_anchor_room_missing",
                context={
                    "service": row.service_id,
                    "anchor_room": row.anchor_room,
                    "action": "skip_service_host_row",
                },
            )
    processable = [row for row in roster if rooms[row.host_key] is not None]
    retirement_candidates = _undeclared_source_hosts(declared)
    reused = [
        (host, snapshot_attributes(host, HOST_ATTRIBUTE_SURFACES))
        for host in hosts.values()
        if host is not None
    ]
    created: list[NPC] = []
    retired: list[dict[str, Any]] = []
    try:
        with transaction.atomic():
            synced: list[NPC] = []
            for row in processable:
                synced.append(
                    _sync_service_host(
                        row,
                        rooms[row.host_key],
                        hosts[row.host_key],
                        created=created,
                    )
                )
            _initialize_merchant_stock(synced)
            _retire_source_hosts(retirement_candidates, retired)
    except Exception:
        _restore_batch(created=created, reused=reused, retired=retired)
        raise
    if not processable:
        log_warn(
            "guild_economy_service_interiors_still_missing",
            context={"action": "skip_service_content"},
        )


def _initialize_merchant_stock(hosts: list[NPC]) -> None:
    """Seed a merchant's stock exactly once, when it is still uninitialized.

    Live stock, restock progress and a sold-out-but-initialized dictionary are
    never touched: only an uninitialized (``None``) stock surface is seeded from
    the catalog's initial quantities, so a shop-identity edit converges the
    authored fields while leaving commerce progress exactly as it was. Hosts
    skipped for an unresolved anchor are never passed here.
    """
    catalog = get_catalog()
    merchant_slot = PROFESSION_COMPONENT_TYPES["merchant"].get_component_slot()
    for host in hosts:
        merchant = host.components.get(merchant_slot)
        if merchant is None or merchant.merchant_stock is not None:
            continue
        shop_key = merchant.shop_key
        shop_config = catalog.shop_configs.get(shop_key)
        if shop_config is None:
            log_warn(
                "guild_economy_unknown_shop",
                context={"host": host.key, "shop_key": shop_key},
            )
            continue
        merchant.merchant_stock = {
            offer.item_key: offer.initial_stock for offer in shop_config.offers
        }


def sync_guild_economy() -> None:
    """Run the full idempotent guild-economy startup synchronization."""
    from world.rules.human_guild_hosts import (
        sync_persistent_adventurers, validate_adventurers,
    )
    from world.lore.guild_adventurers import ADVENTURER_REGISTRY, EXAM_QUALIFICATIONS

    validate_adventurers(ADVENTURER_REGISTRY, NPC_PROFILE_REGISTRY, EXAM_QUALIFICATIONS)
    catalog = load_catalog_into_cache()
    from world.rules.guild_config import register_catalog_offers

    register_catalog_offers(catalog)
    sync_service_content()
    sync_persistent_adventurers()
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
