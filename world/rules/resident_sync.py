"""Idempotent authoring sync for chat-only persistent residents.

The adventurer sync's general core (find-or-create ``LLMNPC`` by canonical
identity, assemble the profile card and canonical ages, write literal traits and
sex, place the person, assign a schedule) without the guild, rank, sword-skill,
equipment or examiner baggage. A resident never receives a managed service
capability: the only component it may carry is an unbound ``scripted_dialogue``
table, and even that only when the authored row declares a ``dialogue_key``.

Validation is all-or-nothing before the first write: every profile, dialogue
table, schedule target, home room and public node is resolved first. The whole
write runs in one transaction; a failure evicts the objects this batch created
so a rolled-back residency is never served from the identity map. A reused
resident is left wholly untouched -- never renamed, relocated, re-carded or
re-scheduled -- so a player edit survives every restart.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from django.db import transaction
from evennia.utils.create import create_object

from typeclasses.npcs import NPC, LLMNPC, ensure_npc_canonical_age
from world.art.official_refs import NPC_PROFILE_PROVENANCE_ATTRIBUTE
from world.lore.dialogue import DIALOGUE_ROWS
from world.lore.npc_card import normalize_card, normalize_offline_greeting
from world.lore.npc_profiles import NPC_PROFILE_REGISTRY
from world.lore.residents import RESIDENT_PUBLIC_NODES, RESIDENT_REGISTRY
from world.lore.settlements.capability_declarations import capability
from world.maps.bootstrap import resolve_public_route
from world.observability import log_info
from world.rules.identity import ensure_entity_sex
from world.rules.npc_capabilities import assemble_capabilities, validate_capabilities
from world.rules.npc_identity import live_key_taken_by_other, validate_npc_name
from world.rules.npc_persona import initialize_npc_persona
from world.rules.npc_schedules import get_rulebook, set_npc_schedule
from world.rules.social_identity import set_social_identities
from world.rules.surfaces import flush_idmapper_cache, flush_orphan_instances
from world.rules.traits import _trait_config

#: The canonical authored identity every created resident records. It is never a
#: display name, a location or a component order.
RESIDENT_ATTRIBUTE = "resident_key"
#: The source-ownership tag a normal resident sync applies.
RESIDENT_TAG = "resident"

#: Template move target -> the route key it binds. The shipped ``resident``
#: template names ``market_square`` (the village public node) and ``residence``
#: (the home); the remaining roles keep a custom template usable without a
#: second authoring vocabulary.
SCHEDULE_TARGET_ROLES: dict[str, str] = {
    "residence": "home",
    "home": "home",
    "market_square": "public",
    "public": "public",
    "frontage": "frontage",
}


class ResidentSyncError(ValueError):
    """An authored or persistent resident identity cannot be synchronized."""


def _declared_name(row: Any) -> str:
    try:
        return validate_npc_name(row.name)
    except ValueError as error:
        raise ResidentSyncError(f"resident {row.key!r} has an invalid name: {error}") from error


def _validate_voice(row: Any, profile: Any, dialogue_key: str | None, dialogue_rows: Mapping) -> None:
    if dialogue_key is not None:
        table = dialogue_rows.get(dialogue_key)
        if table is None:
            raise ResidentSyncError(
                f"resident {row.key!r} references missing dialogue table {dialogue_key!r}"
            )
        greeting = getattr(table, "greeting", None)
        if not isinstance(greeting, str) or not greeting.strip():
            raise ResidentSyncError(
                f"resident {row.key!r} dialogue table {dialogue_key!r} authors no greeting"
            )
        if getattr(table, "services", ()):
            raise ResidentSyncError(
                f"resident {row.key!r} dialogue table {dialogue_key!r} advertises a service"
            )
        if profile.voice.greeting is not None:
            raise ResidentSyncError(
                f"resident {row.key!r} profile authors a greeting beside its dialogue table"
            )
    else:
        greeting = profile.voice.greeting
        if not isinstance(greeting, str) or not greeting.strip():
            raise ResidentSyncError(
                f"resident {row.key!r} profile needs an offline greeting without a dialogue table"
            )
    misunderstood = profile.voice.misunderstood
    if not isinstance(misunderstood, str) or not misunderstood.strip():
        raise ResidentSyncError(
            f"resident {row.key!r} profile needs a misunderstanding reply"
        )
    try:
        normalize_offline_greeting(misunderstood)
    except ValueError as error:
        raise ResidentSyncError(
            f"resident {row.key!r} misunderstanding reply is malformed: {error}"
        ) from error


def _bound_schedule(row: Any, route: Mapping[str, Any]) -> dict:
    template = get_rulebook().template_by_key(row.schedule_template)
    if template is None:
        raise ResidentSyncError(
            f"resident {row.key!r} has unknown schedule template {row.schedule_template!r}"
        )
    rooms = {role: route[role] for role in ("home", "public", "frontage")}
    overrides: dict[str, dict[str, str]] = {}
    moves = 0
    for index, entry in enumerate(template.entries):
        if entry.kind != "move":
            continue
        moves += 1
        role = SCHEDULE_TARGET_ROLES.get(entry.target)
        if role is None:
            raise ResidentSyncError(
                f"resident {row.key!r} schedule target {entry.target!r} has no route role"
            )
        overrides[str(index)] = {"target": rooms[role].dbref}
    if moves == 0:
        raise ResidentSyncError(
            f"resident {row.key!r} schedule template {row.schedule_template!r} has no move entry"
        )
    return {
        "schema_version": 1,
        "template": row.schedule_template,
        "overrides": overrides,
    }


def _existing_residents() -> dict[str, NPC]:
    residents: dict[str, NPC] = {}
    for npc in NPC.objects.all_family():
        key = npc.attributes.get(RESIDENT_ATTRIBUTE)
        if key is None:
            continue
        if key in residents:
            raise ResidentSyncError(
                f"resident identity {key!r} is claimed by more than one NPC"
            )
        residents[key] = npc
    return residents


def _validate_reserved_profiles(
    residents: Mapping[str, Any],
) -> None:
    from world.lore.guild_adventurers import ADVENTURER_REGISTRY
    from world.lore.settlements.places import PLACE_REGISTRY, place_dialogue_keys

    reserved = {
        place.host_profile_key
        for place in PLACE_REGISTRY.values()
        if place.host_profile_key
    }
    reserved.update(person.profile_key for person in ADVENTURER_REGISTRY.values())
    hosted_tables = {
        dialogue_key: place.host_profile_key
        for place in PLACE_REGISTRY.values()
        if place.host_profile_key
        for dialogue_key in place_dialogue_keys(place)
    }
    seen: dict[str, str] = {}
    table_owners: dict[str, str] = {}
    for key, row in residents.items():
        if row.profile_key in reserved:
            raise ResidentSyncError(
                f"resident {key!r} profile {row.profile_key!r} already belongs to another source"
            )
        holder = seen.get(row.profile_key)
        if holder is not None:
            raise ResidentSyncError(
                f"resident profile {row.profile_key!r} is shared by {holder!r} and {key!r}"
            )
        seen[row.profile_key] = key
        if not row.dialogue_key:
            continue
        host_profile = hosted_tables.get(row.dialogue_key)
        if host_profile is not None:
            raise ResidentSyncError(
                f"resident {key!r} dialogue table {row.dialogue_key!r} already "
                f"belongs to place host profile {host_profile!r}"
            )
        table_holder = table_owners.get(row.dialogue_key)
        if table_holder is not None:
            raise ResidentSyncError(
                f"dialogue table {row.dialogue_key!r} is shared by residents "
                f"{table_holder!r} and {key!r}"
            )
        table_owners[row.dialogue_key] = key


def _reject_managed_capabilities(key: str, host: NPC) -> None:
    """A reused resident must still be chat-only and owned by the resident sync."""
    from world.rules.guild_economy import (
        CONTENT_SOURCE_TAG_CATEGORY,
        MANAGED_TYPE_KEYS,
        SERVICE_HOST_TAG,
    )
    from world.rules.npc_capabilities import COMPONENT_TYPES

    if host.tags.has(SERVICE_HOST_TAG, category=CONTENT_SOURCE_TAG_CATEGORY):
        raise ResidentSyncError(f"resident identity {key!r} is tagged as a service host")
    for type_key in sorted(MANAGED_TYPE_KEYS - {"scripted_dialogue"}):
        slot = COMPONENT_TYPES[type_key].get_component_slot()
        if host.components.get(slot) is not None:
            raise ResidentSyncError(
                f"resident identity {key!r} carries managed service component {type_key!r}"
            )


def _preflight(
    *,
    residents: Mapping[str, Any],
    profiles: Mapping,
    dialogue_rows: Mapping,
    public_nodes: Mapping[str, str],
) -> tuple[dict[str, NPC], dict[str, dict], dict[str, Any], dict[str, Any]]:
    from world.lore.races import SUBRACE_REGISTRY

    _validate_reserved_profiles(residents)
    existing = _existing_residents()

    holders: dict[str, list[NPC]] = {}
    for npc in NPC.objects.all_family():
        profile_key = npc.attributes.get(NPC_PROFILE_PROVENANCE_ATTRIBUTE)
        if profile_key:
            holders.setdefault(profile_key, []).append(npc)

    routes: dict[str, dict] = {}
    schedules: dict[str, dict] = {}
    plans: dict[str, Any] = {}
    for key, row in residents.items():
        if row.key != key:
            raise ResidentSyncError(f"resident {key!r} declares key {row.key!r}")
        _declared_name(row)
        profile = profiles.get(row.profile_key)
        if profile is None:
            raise ResidentSyncError(
                f"resident {key!r} references missing profile {row.profile_key!r}"
            )
        for field in ("age", "apparent_age"):
            value = getattr(profile, field)
            if type(value) is not int or not 0 <= value <= 10000:
                raise ResidentSyncError(
                    f"resident {key!r} profile {row.profile_key!r} has invalid {field}"
                )
        try:
            normalize_card(profile.card.to_record())
        except ValueError as error:
            raise ResidentSyncError(
                f"resident {key!r} profile {row.profile_key!r} has an invalid card: {error}"
            ) from error
        _validate_voice(row, profile, row.dialogue_key, dialogue_rows)

        for other in holders.get(row.profile_key, ()):
            if other.attributes.get(RESIDENT_ATTRIBUTE) != key:
                raise ResidentSyncError(
                    f"resident {key!r} profile {row.profile_key!r} is already owned by NPC "
                    f"{other.pk}"
                )
        host = existing.get(key)
        if host is not None:
            from world.rules.guild_economy import CONTENT_SOURCE_TAG_CATEGORY

            if not isinstance(host, LLMNPC) or not host.tags.has(
                RESIDENT_TAG, category=CONTENT_SOURCE_TAG_CATEGORY
            ):
                raise ResidentSyncError(
                    f"resident identity {key!r} names an object this sync does not own"
                )
            if host.attributes.get(NPC_PROFILE_PROVENANCE_ATTRIBUTE) != row.profile_key:
                raise ResidentSyncError(
                    f"resident identity {key!r} carries another profile provenance"
                )
            _reject_managed_capabilities(key, host)

        settlement = SUBRACE_REGISTRY[row.subrace].home_anchor_key
        if not settlement:
            raise ResidentSyncError(
                f"resident {key!r} subrace {row.subrace!r} names no settlement"
            )
        public_node = public_nodes.get(settlement)
        if public_node is None:
            raise ResidentSyncError(
                f"resident {key!r} settlement {settlement!r} declares no public node"
            )
        routes[key] = resolve_public_route(row.home_room, settlement, public_node)
        schedules[key] = _bound_schedule(row, routes[key])
        if row.dialogue_key is None:
            plans[key] = None
        else:
            plans[key] = validate_capabilities(
                [capability("scripted_dialogue", dialogue_key=row.dialogue_key)]
            )
    return existing, routes, schedules, plans


def sync_residents(
    *,
    residents: Mapping[str, Any] | None = None,
    profiles: Mapping | None = None,
    dialogue_rows: Mapping | None = None,
    public_nodes: Mapping[str, str] | None = None,
) -> tuple[NPC, ...]:
    """Create each authored resident once; an existing resident is untouched.

    Returns every resident host, in authored registry order. The same call is
    idempotent: a second sync creates nothing and moves nobody.
    """
    residents = RESIDENT_REGISTRY if residents is None else residents
    profiles = NPC_PROFILE_REGISTRY if profiles is None else profiles
    dialogue_rows = DIALOGUE_ROWS if dialogue_rows is None else dialogue_rows
    public_nodes = RESIDENT_PUBLIC_NODES if public_nodes is None else public_nodes

    existing, routes, schedules, plans = _preflight(
        residents=residents,
        profiles=profiles,
        dialogue_rows=dialogue_rows,
        public_nodes=public_nodes,
    )

    from world.rules.guild_economy import CONTENT_SOURCE_TAG_CATEGORY

    created: list[NPC] = []
    try:
        with transaction.atomic():
            for key, row in residents.items():
                if existing.get(key) is not None:
                    continue
                route = routes[key]
                profile = profiles[row.profile_key]
                host = create_object(
                    LLMNPC, key=_declared_name(row), location=route["home"]
                )
                created.append(host)
                host.attributes.add(RESIDENT_ATTRIBUTE, key)
                host.attributes.add(
                    NPC_PROFILE_PROVENANCE_ATTRIBUTE, row.profile_key
                )
                host.tags.add(RESIDENT_TAG, category=CONTENT_SOURCE_TAG_CATEGORY)
                host.race = row.race
                host.subrace = row.subrace
                ensure_entity_sex(host, row.sex)
                host._apply_trait_config(
                    _trait_config({**dict(row.stats), "guild_merit": 0})
                )
                ensure_npc_canonical_age(
                    host, age=profile.age, apparent_age=profile.apparent_age
                )
                initialize_npc_persona(
                    host,
                    profile.card.to_record(),
                    {"kind": "profile", "profile": row.profile_key},
                )
                if profile.social_identities:
                    set_social_identities(host, profile.social_identities)
                if plans[key] is not None:
                    assemble_capabilities(host, plans[key])
                set_npc_schedule(host, schedules[key])
                if live_key_taken_by_other(host):
                    host.key = f"{_declared_name(row)}-{host.pk}"
                host.save()
                transaction.on_commit(
                    lambda context={
                        "host": host.pk,
                        "resident": key,
                        "profile": row.profile_key,
                        "home": route["home"].pk,
                        "public": route["public"].pk,
                    }: log_info("resident_created", context=context)
                )
    except Exception:
        # The atomic block has rolled back; evict the instances this batch
        # created so the next read loads the persisted baseline instead of a
        # dead in-process object.
        flush_orphan_instances()
        flush_idmapper_cache()
        raise
    by_key = {host.attributes.get(RESIDENT_ATTRIBUTE): host for host in created}
    return tuple(existing.get(key) or by_key[key] for key in residents)


__all__ = [
    "RESIDENT_ATTRIBUTE",
    "RESIDENT_TAG",
    "SCHEDULE_TARGET_ROLES",
    "ResidentSyncError",
    "sync_residents",
]
