"""The runtime kind registry: one dispatch point for list/detail/raw/search.

``kind`` is resolved explicitly (never guessed from the identity), because the
same numeric id is a valid character, NPC or monster depending on the route.
Object-backed kinds resolve their kind once (with a ``kind_mismatch`` for an
object of another kind) and record-backed kinds use the owning model's stable
identifier: quest ids are owner-scoped, memories use their primary key,
snapshots and dialogue use the narrative identity, and narrative detail carries
its subtype in the identifier itself.
"""

from __future__ import annotations

from typing import Any, Callable

from web.gm import pagination
from web.gm.readers import (
    accounts,
    art,
    characters,
    monsters,
    narrative,
    npcs,
    quests,
    raw,
    rooms,
    search,
)
from web.gm.readers.errors import KindMismatch, ObjectNotFound, UnsupportedKind
from web.gm.readers._entities import object_kind

#: Every kind the runtime API serves, in navigation order.
KIND_ORDER = (
    "accounts",
    "characters",
    "npcs",
    "monsters",
    "rooms",
    "quests",
    "narrative",
    "art",
    "memories",
    "snapshots",
    "dialogue",
)

KIND_LABELS = {
    "accounts": "帳號",
    "characters": "玩家角色",
    "npcs": "NPC",
    "monsters": "魔物",
    "rooms": "房間",
    "quests": "任務",
    "narrative": "敘事",
    "art": "美術資產",
    "memories": "記憶",
    "snapshots": "情境快照",
    "dialogue": "對話",
    "object": "物件",
}

#: The filters a kind's fingerprint is computed from (order-independent).
FILTER_KEYS = (
    "owner",
    "subtype",
    "location",
    "species",
    "region",
    "status",
    "state",
    "kind",
    "category",
    "tier",
    "scope",
    "visibility",
    "event_type",
    "outcome",
    "thread",
    "sender",
    "recipient",
    "generated",
    "include_superseded",
    "include_inactive",
)


def filters_of(params: Any) -> dict[str, Any]:
    """The normalized filter set of one query (also the cursor's fingerprint)."""
    result: dict[str, Any] = {}
    for key in FILTER_KEYS:
        value = params.get(key)
        if value in (None, ""):
            continue
        result[key] = str(value)
    return result


def _object_queryset(model: Any) -> Any:
    return model.objects.all_family().order_by("id")


def _object_rows(kind: str, model: Any, item_of: Callable[[Any], dict], filters: dict[str, Any]) -> list[dict]:
    queryset = _object_queryset(model)
    if kind == "npcs" and filters.get("location"):
        location = str(filters["location"]).strip().lstrip("#")
        if not location.isdigit():
            from web.gm.readers.errors import InvalidFilter

            raise InvalidFilter("location 必須是房間的 dbref（例如 ?location=#12）。")
        queryset = queryset.filter(db_location_id=int(location))
    entities = list(queryset)
    species = filters.get("species")
    region = filters.get("region")
    if kind == "monsters" and (species or region):
        entities = [
            entity
            for entity in entities
            if _monster_matches(entity, species, region)
        ]
    return [item_of(entity) for entity in entities]


def _monster_matches(entity: Any, species: Any, region: Any) -> bool:
    """Species/region are identity reads on the individual, not SQL columns."""
    from web.gm.readers._entities import read_attr

    if species:
        wanted = str(species)
        if wanted not in {
            str(read_attr(entity, "species_key", default="")),
            str(read_attr(entity, "variant_key", default="")),
        }:
            return False
    if region and str(monsters.region_of(entity)) != str(region):
        return False
    return True


def list_rows(kind: str, filters: dict[str, Any]) -> list[dict[str, Any]]:
    """Every filtered summary row of one kind, in the kind's stable order."""
    if kind == "accounts":
        from typeclasses.accounts import Account

        return _object_rows(kind, Account, accounts.item_of, filters)
    if kind == "characters":
        from typeclasses.characters import PlayerCharacter

        return _object_rows(kind, PlayerCharacter, characters.character_list_item, filters)
    if kind == "npcs":
        from typeclasses.npcs import NPC

        return _object_rows(kind, NPC, npcs.item_of, filters)
    if kind == "monsters":
        from typeclasses.monsters import Monster

        return _object_rows(kind, Monster, monsters.item_of, filters)
    if kind == "rooms":
        from typeclasses.rooms import Room

        return _object_rows(kind, Room, rooms.item_of, filters)
    if kind == "quests":
        if str(filters.get("generated", "")).lower() in {"1", "true", "yes", "on"}:
            return [
                quests.generated_item_of(payload, index)
                for index, payload in enumerate(quests.generated_payloads())
            ]
        owner = filters.get("owner")
        records = quests.owner_records(owner)
        actor = quests.resolve_owner(owner)
        return [quests.item_of(record, actor) for record in records]
    if kind == "narrative":
        subtype = str(filters.get("subtype") or "event")
        return narrative.list_items(subtype, filters)
    if kind == "art":
        return art.list_items(filters)
    if kind == "memories":
        return npcs.memory_list_items(filters)
    if kind == "snapshots":
        return npcs.snapshot_list_items(filters)
    if kind == "dialogue":
        return npcs.dialogue_list_items(filters)
    raise UnsupportedKind(kind)


def build_list(kind: str, params: Any) -> dict[str, Any]:
    """The paginated list payload for one kind."""
    limit = pagination.parse_limit(params.get("limit"))
    filters = filters_of(params)
    offset = pagination.decode_cursor(params.get("cursor"), filters) if params.get("cursor") else 0
    rows = list_rows(kind, filters)
    return pagination.envelope(rows, offset, limit, filters)


def object_detail(kind: str, identity: str) -> dict[str, Any]:
    """Resolve a curated object and project its summary, or raise."""
    from evennia.objects.models import ObjectDB

    text = str(identity).strip().lstrip("#")
    if not text.isdigit():
        raise ObjectNotFound()
    entity = ObjectDB.objects.filter(pk=int(text)).first()
    if entity is None:
        raise ObjectNotFound()
    if object_kind(entity) != kind:
        raise KindMismatch()
    if kind == "characters":
        return characters.character_detail(entity)
    if kind == "npcs":
        return npcs.detail(entity)
    if kind == "monsters":
        return monsters.detail(entity)
    if kind == "rooms":
        return rooms.detail(entity)
    raise UnsupportedKind(kind)


def detail(kind: str, identity: str, filters: dict[str, Any]) -> dict[str, Any]:
    """The curated detail payload of one entity."""
    if kind in {"accounts", "characters", "npcs", "monsters", "rooms", "object"}:
        if kind == "accounts":
            from evennia.accounts.models import AccountDB

            text = str(identity).strip().lstrip("#")
            if not text.isdigit():
                raise ObjectNotFound()
            account = AccountDB.objects.filter(pk=int(text)).first()
            if account is None:
                raise ObjectNotFound()
            return accounts.detail(account)
        if kind == "object":
            raise KindMismatch()
        return object_detail(kind, identity)
    if kind == "quests":
        text = str(identity)
        if text.startswith("generated:"):
            index = text.split(":", 1)[1]
            if not index.isdigit():
                raise ObjectNotFound()
            payloads = quests.generated_payloads()
            position = int(index)
            if position >= len(payloads):
                raise ObjectNotFound()
            return quests.generated_detail(payloads[position])
        owner = filters.get("owner")
        actor = quests.resolve_owner(owner)
        records = quests.owner_records(owner)
        from world.quests.runtime import find_record

        record = find_record(records, text)
        if record is None:
            raise ObjectNotFound()
        return quests.detail_for_record(record, actor)
    if kind == "narrative":
        subtype, narrative_id = narrative.split_identity(identity)
        return narrative.detail(subtype, narrative_id)
    if kind == "art":
        for record in art.records():
            if record.key == str(identity):
                return art.detail(record)
        raise ObjectNotFound()
    if kind == "memories":
        return npcs.memory_detail(identity, filters)
    if kind == "snapshots":
        return npcs.snapshot_detail(identity, filters)
    if kind == "dialogue":
        return npcs.dialogue_detail(identity, filters)
    raise UnsupportedKind(kind)


def raw_object(dbref: str) -> dict[str, Any]:
    """The universal raw inventory of any Evennia object."""
    from evennia.objects.models import ObjectDB

    text = str(dbref).strip().lstrip("#")
    if not text.isdigit():
        raise ObjectNotFound()
    entity = ObjectDB.objects.filter(pk=int(text)).first()
    if entity is None:
        raise ObjectNotFound()
    return {**raw.raw_identity(entity), "raw": raw.raw_object(entity)}


def search_items(query: Any) -> dict[str, Any]:
    return search.search(query)


def recall_preview(owner: Any, body: Any) -> dict[str, Any]:
    return npcs.recall(owner, body if isinstance(body, dict) else {})


__all__ = [
    "FILTER_KEYS",
    "KIND_LABELS",
    "KIND_ORDER",
    "build_list",
    "detail",
    "filters_of",
    "list_rows",
    "object_detail",
    "raw_object",
    "recall_preview",
    "search_items",
]
