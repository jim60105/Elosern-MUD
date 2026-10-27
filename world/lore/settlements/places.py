"""Place identity registry (settlement-shops design §3.2).

A place is the single authored record of one service location: its interior
room's identity and description, the qualified settlement-node identity of the
exterior room the interior attaches to, the doorway naming, its host's
identity, the host's explicit capability declarations, and the assortments the
place sells. Nothing a place declares is declared anywhere else. The exterior
address is derived from the current settlement graph at the consumer boundary
(``world/maps/static_references.py``); the row stores no coordinate.

``host_race`` / ``host_subrace`` / ``host_sex`` are creation-time authored
identity: ``sync_service_content`` writes them once when it creates the host
and never rewrites them on a later sync, so an authored edit takes effect
through roster convergence rather than a backfill.

A place's host is optional as ONE indivisible group: a place either authors
the complete host (name, race, sex, profile key — with a subrace and
capability declarations as its optional parts) or authors none of it,
describing a place that simply exists: a plaza, a forecourt, a quay. A
partially authored host is a load error, not a half-built NPC. A hosted place
may declare zero capabilities: the person exists without offering a service.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Mapping

from elosern_map_core.documents import QualifiedRef
from elosern_map_core.references import settlement_node_ref

from world.lore.races import RACE_REGISTRY, SUBRACE_REGISTRY
from world.lore.registry_refs import ref, ref_many
from world.lore.sex import SEX_VALUES
from world.lore.settlements.capability_declarations import CapabilityDeclaration

from world.lore.settlements.settlements import SETTLEMENT_REGISTRY

class PlaceKind(StrEnum):
    """Closed vocabulary of what a place's location IS in the world.

    A kind names the location itself — the room, the ground, the building —
    never a capability its host happens to carry. The worked example is the
    four elven homes: every one of them trades, and every one of them is
    ``HOME``, because in the village a blade-maker's dwelling is a dwelling
    and the fact that you can buy a blade there is a property of who lives
    in it. A location type the vocabulary cannot name is a reason to extend
    this enum, not to approximate with an existing member.

    Nothing is permitted to branch on ``kind`` at runtime: it is descriptive
    metadata for the registry and for whoever eventually reads it, and
    giving a mechanism permission to gate on it would repeat the mistake
    ``professions.yaml`` warns about for professions.
    """

    GUILD_HALL = "guild_hall"
    GENERAL_STORE = "general_store"
    WEAPONSMITH = "weaponsmith"
    OUTFITTER = "outfitter"
    EATERY = "eatery"
    HOME = "home"
    # The settlement build's location types (altoria-* / ciaran-* content
    # changes author rows against these; none of them changes a shipped row).
    JEWELLER = "jeweller"
    ALCHEMIST = "alchemist"
    TEMPLE = "temple"
    SANCTUM_SHOP = "sanctum_shop"
    TAVERN = "tavern"
    LODGING = "lodging"
    BATHHOUSE = "bathhouse"
    PALACE = "palace"
    WATCH_POST = "watch_post"
    TRAINING_GROUND = "training_ground"
    ACADEMY = "academy"
    MERCHANT_HALL = "merchant_hall"
    MARKET = "market"
    COMMONS = "commons"
    COURIER_STATION = "courier_station"


@dataclass(frozen=True)
class PlaceDefinition:
    """Immutable identity of one service location."""

    key: str  # also the interior room tag
    settlement_key: str = field(metadata=ref("settlements", inverse="places"))
    kind: PlaceKind
    room_name_zh: str
    room_desc_zh: str
    exterior: QualifiedRef  # settlement_node; map scope equals settlement_key
    doorway_key_zh: str
    doorway_aliases: tuple[str, ...]
    # The host is one optional group: every scalar below is None exactly when
    # the place authors no host at all (validate_place_registry enforces the
    # all-or-nothing set; host_subrace stays outside the count because None is
    # a legitimate authored value even for a place with a host).
    host_name: str | None = None
    host_race: str | None = field(  # RACE_REGISTRY key
        default=None, metadata=ref("races", inverse="host_places", nullable=True)
    )
    host_subrace: str | None = field(  # SUBRACE_REGISTRY key under host_race
        default=None, metadata=ref("subraces", inverse="host_places", nullable=True)
    )
    host_sex: str | None = None  # SEX_VALUES member
    # The host's capabilities, declared directly and explicitly: each entry is
    # exactly the JSON ``{type, kwargs, binding}`` shape (npc-capability-
    # declarations). () reads as "declares no capability" and keeps the derived
    # scans working against a host-less row without a guard.
    components: tuple[CapabilityDeclaration, ...] = ()
    # The dataclass has no kw_only: every field after the first default needs
    # one.
    assortment_keys: tuple[str, ...] = field(
        default=(), metadata=ref_many("assortments", inverse="places")
    )
    # Per-place assortment adjustments (settlement-shops design §4). Additions
    # stock items outside the referenced assortments — each addition MUST
    # carry a complete override in the shop row (the commerce rulebook slice) because it has
    # no assortment base rule. Removals decline items the referenced
    # assortments contain. Both are shop-only concepts: a place without a
    # shop identity may declare neither.
    extra_item_keys: tuple[str, ...] = field(
        default=(), metadata=ref_many("items", inverse="extra_at_places")
    )
    excluded_item_keys: tuple[str, ...] = field(
        default=(), metadata=ref_many("items", inverse="excluded_at_places")
    )
    # The optional authored reference to this place's host's NPC persona
    # profile, by profile key (npc-persona-profile-registry D2). Resolving it
    # is mandatory only once every owning slice has filled its rows
    # (npc-persona-host-examiner-producers adds that rule); this field counts
    # as host material, so a hostless place carrying one is never hostless.
    host_profile_key: str | None = field(
        default=None, metadata=ref("npc_profiles", inverse="host_places", nullable=True)
    )
    # A place capability, independent of descriptive kind or host profession.
    letter_service: bool = False
    # The venue flag (church-ordination §5.1): a PLACE-level authored fact the
    # derived church venue set reads. It is not a capability and not a host
    # datum; a church host's venue identity is its own ``church_host`` kwarg.
    church: bool = False


def place_capabilities(place: PlaceDefinition, type_key: str) -> tuple[CapabilityDeclaration, ...]:
    """The declarations of one capability type this place authors."""
    return tuple(
        declaration
        for declaration in place.components
        if declaration.type == type_key
    )


def place_capability_kwargs(place: PlaceDefinition, type_key: str) -> Mapping[str, str]:
    """The authored kwargs of one declared capability (empty when undeclared)."""
    declarations = place_capabilities(place, type_key)
    return {} if not declarations else declarations[0].kwargs


def place_shop_identity(place: PlaceDefinition) -> str | None:
    """The shop identity this place's merchant capability authors, if any."""
    shop_key = place_capability_kwargs(place, "merchant").get("shop_key")
    return shop_key if isinstance(shop_key, str) else None


def place_dialogue_keys(place: PlaceDefinition) -> tuple[str, ...]:
    """Every dialogue table this place's dialogue capability answers from."""
    keys: list[str] = []
    for declaration in place_capabilities(place, "scripted_dialogue"):
        key = declaration.kwargs.get("dialogue_key")
        if isinstance(key, str):
            keys.append(key)
    return tuple(keys)


def place_service_ids(place: PlaceDefinition) -> tuple[str, ...]:
    """Every authored service id this place's capabilities declare."""
    service_ids: list[str] = []
    for declaration in place.components:
        service_id = declaration.kwargs.get("service_id")
        if isinstance(service_id, str):
            service_ids.append(service_id)
    return tuple(service_ids)


# The scalar host fields counted by the all-or-nothing rule. host_subrace is
# deliberately outside the count: None is a legitimate authored value for it
# even on a host-declaring place (every capital host authors None today).
HOST_IDENTITY_FIELDS: tuple[str, ...] = (
    "host_name",
    "host_race",
    "host_sex",
    "host_profile_key",
)

_HOST_SCALARS_WITHOUT_PROFILE: tuple[str, ...] = tuple(
    field for field in HOST_IDENTITY_FIELDS if field != "host_profile_key"
)


def place_is_hostless(place: PlaceDefinition) -> bool:
    """True when this place authors no host at all.

    The single definition of the group's ABSENCE, shared by the record
    validator and the roster derivation so the two never drift. A partially
    authored host is NOT hostless — malformed material must fall through to
    validation, never to a silently empty room. A stray capability declaration
    on an otherwise host-less row is likewise not hostless, and so is a stray
    ``host_profile_key`` (npc-persona-profile-registry D2): naming a host
    profile is host material, even alone.
    """
    return (
        all(getattr(place, field) is None for field in HOST_IDENTITY_FIELDS)
        and place.host_subrace is None
        and place.components == ()
    )


def _validate_host_group(place: PlaceDefinition) -> None:
    """Reject a partially authored host, naming the fields that break the set.

    Reached only when the row is NOT hostless, so the legal shapes here are
    exactly: every scalar authored (optionally with a subrace and capability
    declarations), or a row whose only offence is a stray subrace / capability
    on an otherwise wholly absent group — each of which names the offending
    fields.
    """
    found = [field for field in HOST_IDENTITY_FIELDS if getattr(place, field) is not None]
    missing = [field for field in HOST_IDENTITY_FIELDS if getattr(place, field) is None]
    if place.host_subrace is not None:
        found.append("host_subrace")
    if place.components != ():
        found.append("components")
    if not missing:
        return
    raise ValueError(
        f"place {place.key!r} authors a partial host: the host is one "
        f"all-or-nothing group, found {found} but missing {missing} "
        "(author the complete host or none of it)"
    )


def validate_place_registry(
    places: Mapping[str, PlaceDefinition],
    *,
    check_capabilities: bool = True,
    index=None,
) -> None:
    """Fail closed on a malformed place record, naming the place and rule.

    Record validity (design §3.2): the settlement must exist, the host race
    and sex must be registry members, a subrace must exist and belong to the
    authored race, the exterior must be a qualified settlement node in the
    place's own settlement, every
    capability declaration is shape/vocabulary/reference-validated by the one
    capability core, and a place declares assortments iff it declares a
    merchant (shop) capability.

    The host is optional as one indivisible group (hostless-places): either
    every scalar host field is authored or none is, and a place authoring no
    host may declare no goods. A half-authored host names the fields found
    and the fields missing — that message is the point of the rule, because
    the failure mode it replaces is a half-authored host reaching the roster
    derivation several layers away.

    A hosted place anchors every capability it declares at itself: the row
    that derives from the place spawns the host here, so a capability bound to
    another room (or to the person) has no authored meaning on a place record.
    A hosted place MAY declare zero capabilities.

    A named ``host_profile_key`` (npc-persona-profile-registry D2) is
    rejected on a hostless place, and otherwise must resolve in the NPC
    profile registry.

    The record loop is followed by one cross-record rule (altoria-place-slices,
    born with the replan's shared exteriors): two places MAY share an exterior
    — a craft alley with a forge and a tailor on it is one street with two
    doors — but never a doorway name on it, because two identical doorway
    keys on one exterior produce a single exit where two were authored,
    silently losing a location rather than failing.
    """
    from elosern_map_core.references import ReferenceError, settlement_position

    if index is None:
        from world.maps.static_references import settlement_reference_index

        index = settlement_reference_index()

    for place_key, place in places.items():
        if type(place.letter_service) is not bool:
            raise ValueError(f"place {place_key!r} letter_service must be a boolean")
        if place_key != place.key:
            raise ValueError(f"place {place_key!r} key mismatch (declared {place.key!r})")
        if place.settlement_key not in SETTLEMENT_REGISTRY:
            raise ValueError(
                f"place {place.key!r} names unknown settlement {place.settlement_key!r}"
            )
        hostless = place_is_hostless(place)
        if place.host_profile_key is not None:
            if all(getattr(place, field) is None for field in _HOST_SCALARS_WITHOUT_PROFILE):
                raise ValueError(
                    f"place {place.key!r} names host_profile_key "
                    f"{place.host_profile_key!r} but authors no host (a hostless "
                    "place cannot name a host profile)"
                )
            # Function-local import keeps lore import order acyclic (the
            # guild.py validate_guild_npc_identities precedent).
            from world.lore.npc_profiles import NPC_PROFILE_REGISTRY

            if place.host_profile_key not in NPC_PROFILE_REGISTRY:
                raise ValueError(
                    f"place {place.key!r} names host_profile_key "
                    f"{place.host_profile_key!r} which is absent from the NPC "
                    "profile registry"
                )
        if not hostless:
            _validate_host_group(place)
        # Per-field host validation is reachable only for an authored host:
        # an absent race must never be reported as unknown race ``None``.
        if not hostless and place.host_race not in RACE_REGISTRY:
            raise ValueError(
                f"place {place.key!r} names unknown host_race {place.host_race!r}"
            )
        if not hostless and place.host_sex not in SEX_VALUES:
            raise ValueError(
                f"place {place.key!r} names unknown host_sex {place.host_sex!r}"
            )
        if not hostless and place.host_subrace is not None:
            subrace = SUBRACE_REGISTRY.get(place.host_subrace)
            if subrace is None:
                raise ValueError(
                    f"place {place.key!r} names unknown host_subrace {place.host_subrace!r}"
                )
            if subrace.race_key != place.host_race:
                raise ValueError(
                    f"place {place.key!r} host_subrace {place.host_subrace!r} belongs to "
                    f"race {subrace.race_key!r}, not {place.host_race!r}"
                )
        if not isinstance(place.exterior, QualifiedRef) or place.exterior.domain != "settlement_node":
            raise ValueError(
                f"place {place.key!r} exterior must be a settlement_node reference, "
                f"got {place.exterior!r}"
            )
        expected_map = SETTLEMENT_REGISTRY[place.settlement_key].zcoord
        if place.exterior.map_id != expected_map:
            raise ValueError(
                f"place {place.key!r} exterior names map {place.exterior.map_id!r}, "
                f"not its settlement's coordinate space {expected_map!r}"
            )
        try:
            settlement_position(index, place.exterior, source=f"place {place.key!r}")
        except ReferenceError as error:
            raise ValueError(str(error)) from error
        if type(place.church) is not bool:
            raise ValueError(f"place {place.key!r} church must be a boolean")
        if check_capabilities:
            # The declaration vocabulary/configuration is validated by the one
            # capability owner; this import is deferred so the place registry
            # stays importable without an Evennia environment (the import-time
            # self-check passes ``check_capabilities=False`` and the roster/
            # catalog load owns the full check before any write).
            from world.rules.npc_capabilities import (
                CapabilityValidationError,
                validate_capabilities,
            )

            try:
                validate_capabilities(place.components)
            except CapabilityValidationError as error:
                raise ValueError(f"place {place.key!r} {error}") from error
        for declaration in place.components:
            binding = declaration.binding
            if binding is None or binding.kind != "place":
                raise ValueError(
                    f"place {place.key!r} declares {declaration.type!r} without a "
                    "place binding; an authored host anchors every capability at "
                    f"its own room {place.key!r}"
                )
            if binding.anchor_room != place.key:
                raise ValueError(
                    f"place {place.key!r} declares {declaration.type!r} anchored at "
                    f"{binding.anchor_room!r}; a place host anchors at its own room "
                    f"{place.key!r}"
                )
        if hostless and (
            place.assortment_keys or place.extra_item_keys or place.excluded_item_keys
        ):
            raise ValueError(
                f"place {place.key!r} authors no host and declares goods "
                "(assortment_keys/extra_item_keys/excluded_item_keys); "
                "goods require a merchant to sell them"
            )
        has_shop_identity = place_shop_identity(place) is not None
        if bool(place.assortment_keys) != has_shop_identity:
            if place.assortment_keys:
                raise ValueError(
                    f"place {place.key!r} declares assortments without a shop identity "
                    "(a merchant capability authoring shop_key)"
                )
            raise ValueError(
                f"place {place.key!r} declares a shop identity (merchant shop_key) "
                "without assortments"
            )
        for field_name in ("extra_item_keys", "excluded_item_keys"):
            keys = getattr(place, field_name)
            if not isinstance(keys, tuple) or any(
                not isinstance(key, str) or not key.strip() for key in keys
            ):
                raise ValueError(
                    f"place {place.key!r} {field_name} must be a tuple of "
                    "non-empty item keys"
                )
            if len(set(keys)) != len(keys):
                raise ValueError(f"place {place.key!r} {field_name} has duplicate item keys")
        if (place.extra_item_keys or place.excluded_item_keys) and not has_shop_identity:
            raise ValueError(
                f"place {place.key!r} declares extra_item_keys/excluded_item_keys "
                "without a shop identity (a merchant capability authoring shop_key)"
            )

    # Cross-record pass: one doorway name per exterior. Keyed by
    # (settlement_key, exterior identity, doorway_key_zh) because the interior's
    # z derives from the settlement — the same node id in two settlements is
    # two streets, not one. The exterior reference is already validated by the
    # record loop above.
    first_holder: dict[tuple[str, QualifiedRef, str], str] = {}
    for place in places.values():
        doorway = (
            place.settlement_key,
            place.exterior,
            place.doorway_key_zh,
        )
        if doorway in first_holder:
            raise ValueError(
                f"places {first_holder[doorway]!r} and {place.key!r} both declare "
                f"doorway {place.doorway_key_zh!r} on the exterior at "
                f"{place.exterior.object_id} of {place.settlement_key!r}; "
                "two places on one exterior must name their doorways differently"
            )
        first_holder[doorway] = place.key


# The registry is assembled from the per-settlement slices in fixed order (the
# world/lore/items assembly precedent). Slice order is load-bearing: the
# derived service-host roster and the derived SHOP_REGISTRY both iterate this
# dict, and sync_service_content processes roster rows in this order. The
# capital's own slices run in terrace order — lower, middle, upper — because
# the terraces are how the city is described and a place's terrace is the
# first thing that locates it; the village slice stays last so every capital
# row keeps its place ahead of the village homes' in the derived registries.
from world.lore.settlements.places_altoria_lower import ROWS as ALTORIA_LOWER_ROWS  # noqa: E402
from world.lore.settlements.places_altoria_middle import ROWS as ALTORIA_MIDDLE_ROWS  # noqa: E402
from world.lore.settlements.places_altoria_upper import ROWS as ALTORIA_UPPER_ROWS  # noqa: E402
from world.lore.settlements.places_ciaran import ROWS as CIARAN_ROWS  # noqa: E402

PLACE_REGISTRY: dict[str, PlaceDefinition] = {
    definition.key: definition
    for definition in (
        *ALTORIA_LOWER_ROWS,
        *ALTORIA_MIDDLE_ROWS,
        *ALTORIA_UPPER_ROWS,
        *CIARAN_ROWS,
        PlaceDefinition(
            key="altoria_silverfeather",
            settlement_key="capital_altoria",
            kind=PlaceKind.COURIER_STATION,
            room_name_zh="銀羽驛站・王都分站",
            room_desc_zh="銀羽驛行的櫃檯備有信紙與封蠟，牆上列著各地分站。旅人可在此寄信，或領取寄給自己的信件。",
            exterior=settlement_node_ref("capital_altoria", "market_street"),
            doorway_key_zh="銀羽驛站",
            doorway_aliases=("courier",),
            letter_service=True,
        ),
        PlaceDefinition(
            key="ciaran_silverfeather",
            settlement_key="village_ciaran",
            kind=PlaceKind.COURIER_STATION,
            room_name_zh="銀羽驛站・精靈村分站",
            room_desc_zh="樹蔭下的銀羽驛行收存各地來信，木架上擱著公用信紙與封蠟。旅人可在此寄信，或領取寄給自己的信件。",
            exterior=settlement_node_ref("village_ciaran", "old_tree_north"),
            doorway_key_zh="銀羽驛站",
            doorway_aliases=("courier",),
            letter_service=True,
        ),
    )
}

validate_place_registry(PLACE_REGISTRY, check_capabilities=False)