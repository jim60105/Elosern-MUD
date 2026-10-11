"""Normalized deterministic quest definitions (quest-runtime D-1).

This module owns the closed, immutable runtime input consumed by the quest
state machine. It is deliberately distinct from change 20's future AI
``QuestBlueprint`` proposal: raw mappings are never accepted here, and the
same structural vocabulary (type / objectives / destination layers) is the
narrow conversion target that change 20's guardrail will compile to.
"""

from dataclasses import dataclass, field
from enum import StrEnum

from world.lore.anchor_placement import ANCHOR_PLACEMENT_REGISTRY
from world.lore.items import ITEM_REGISTRY
from world.lore.monster_placement import MONSTER_SITE_REGISTRY
from world.lore.monster_species import (
    MONSTER_SPECIES_REGISTRY,
    MONSTER_VARIANT_REGISTRY,
)
from world.lore.monsters import MONSTER_TIER_REGISTRY
from world.lore.registry_refs import ref, ref_many
from world.lore.wilderness_regions import WILDERNESS_REGION_REGISTRY
from world.maps.map_data import XYMAP_DATA_LIST


class QuestType(StrEnum):
    """The complete quest's classification; it does not restrict stage mechanics."""

    GATHER = "採集"
    DEFEAT = "討伐"
    ESCORT = "護衛"
    EXPLORE = "探索"
    EMERGENCY = "緊急"


class ObjectiveKind(StrEnum):
    """The deterministic progress mechanic of one stage."""

    DEFEAT = "defeat"
    REACH = "reach"
    ESCORT = "escort"
    ACQUIRE = "acquire"
    DELIVER = "deliver"


class DestinationKind(StrEnum):
    """Where a static or generated destination lives."""

    ANCHOR = "anchor"
    GRID = "grid"
    BOUND_INSTANCE = "bound_instance"


class EscortCompletion(StrEnum):
    """The closed escort completion discriminator (escort-rendezvous §6).

    An escort objective declares exactly one of these: ``DESTINATION`` (every
    exact protected identity living at a validated locator) or ``RENDEZVOUS``
    (exact protected and meeting identities living at the same authoritative
    position, with any published typed relation satisfied). The quest
    classification (``QuestType.ESCORT``) stays independent of this predicate.
    """

    DESTINATION = "destination"
    RENDEZVOUS = "rendezvous"


#: The closed typed-relationship vocabulary shared with the scene package's
#: relationship contract. ``parent_child`` is directed (``from_role`` is the
#: parent, ``to_role`` the child); a rendezvous relation must name declared
#: role references and one of these kinds.
RELATIONSHIP_KINDS: tuple[str, ...] = ("parent_child",)


class QuestDefinitionError(ValueError):
    """A definition violates the closed runtime input contract."""


#: The authored-prose bounds of ``rating_rationale_zh`` /
#: ``background_flavor_zh``. Both fields render *verbatim* into ``guild show``
#: and into the frozen web quest-detail field, whose shared bound is 512 code
#: points (``MAX_DETAIL_CODE_POINTS`` in the webclient presentation contract,
#: which this change deliberately leaves untouched). The fixed detail sections —
#: name, state, stage, objective line, progress, grade, deadline, reward —
#: reserve roughly 230 of that, so the authored prose may spend 240 per field
#: and 280 together; anything larger could not be displayed by those panels at
#: all, which is why the bound is enforced at registration instead of silently
#: truncating the authored text at render time.
MAX_DEFINITION_PROSE_LENGTH = 240

#: The combined bound of the two prose fields, for the same reason.
MAX_DEFINITION_PROSE_TOTAL = 280

#: The shared bound on a published scene-role reference (mirrors the scene
#: package's own ``MAX_ID_LENGTH``), so an objective's role references cannot
#: exceed the identifiers a validated package can declare.
MAX_ROLE_REF_LENGTH = 64

#: The CJK Unified Ideographs block: an authored player-facing prose field must
#: contain at least one, so an ASCII placeholder cannot masquerade as zh-TW text.
_CJK_START = "\u4e00"
_CJK_END = "\u9fff"


KNOWN_GRID_MAP_KEYS: frozenset[str] = frozenset(
    map_data["zcoord"]
    for map_data in XYMAP_DATA_LIST
)


@dataclass(frozen=True)
class RoomLocator:
    """A destination that needs no room dbref at definition time.

    ANCHOR carries exactly ``anchor_key``; GRID carries exactly ``xyz``;
    BOUND_INSTANCE carries neither and resolves only through an accepted
    record's ``stage_room_id``.
    """

    kind: DestinationKind
    anchor_key: str | None = field(
        default=None, metadata=ref("anchors", inverse="quest_destinations", nullable=True)
    )
    xyz: tuple[int, int, str] | None = None


@dataclass(frozen=True)
class QuestObjective:
    """One stage's typed, fully deterministic progress criterion."""

    kind: ObjectiveKind
    quantity: int = 1
    monster_tier: str | None = field(
        default=None, metadata=ref("monster_tiers", inverse="quest_objectives", nullable=True)
    )
    destination: RoomLocator | None = None
    requires_bound_targets: bool = False
    item_key: str | None = field(
        default=None, metadata=ref("items", inverse="quest_objectives", nullable=True)
    )
    #: The regional species-hunt selector (design D-Q1/D-Q2): a region key, a
    #: species key, and the countable variant keys owned by that species. The
    #: three are legal only together, mutually exclusive with ``monster_tier``
    #: and ``requires_bound_targets``, and at least one countable variant must be
    #: an ordinary baseline variant, so the acceptance-time guarantee about
    #: ordinary-eligible living targets is always expressible.
    region_key: str | None = field(
        default=None,
        metadata=ref("wilderness_regions", inverse="quest_objectives", nullable=True),
    )
    species_key: str | None = field(
        default=None, metadata=ref("monster_species", inverse="quest_objectives", nullable=True)
    )
    countable_variant_keys: tuple[str, ...] = field(
        default=(), metadata=ref_many("monster_variants", inverse="quest_objectives")
    )
    #: The bound site clear-out selector (design D-C1): the key of an authored
    #: site in ``MONSTER_SITE_REGISTRY``. Legal only together with
    #: ``requires_bound_targets=True`` and mutually exclusive with every other
    #: selector family. The objective binds the site's own living individuals —
    #: the site is a source, never a spawn — and ``quantity`` may not exceed the
    #: site's authored capacity. It is a hand-written-only field: the
    #: deterministic compile boundary never authors it, and the stored payload
    #: round-trips it with an absent-key default.
    site_key: str | None = field(
        default=None, metadata=ref("monster_sites", inverse="quest_objectives", nullable=True)
    )
    #: The escort completion discriminator (escort-rendezvous §6). Legal only on
    #: an ESCORT objective, which must declare exactly one mode.
    completion: EscortCompletion | None = None
    #: The exact published package roles this stage protects (escort-rendezvous
    #: §3): resolved to the same live entity at acceptance and at every
    #: completion evaluation. Nonempty on every ESCORT objective.
    protected_role_refs: tuple[str, ...] = ()
    #: The exact published package roles a rendezvous stage meets
    #: (escort-rendezvous §6.2). Empty for destination mode; nonempty for
    #: rendezvous mode.
    meeting_role_refs: tuple[str, ...] = ()
    #: The optional typed relation a rendezvous requires, as
    #: ``(kind, from_role, to_role)`` with ``kind`` in :data:`RELATIONSHIP_KINDS`
    #: and both endpoints declared role references. ``None`` when undeclared.
    relation: tuple[str, str, str] | None = None


@dataclass(frozen=True)
class QuestStage:
    """One explicit, zero-based stage index plus its objective."""

    index: int
    objective: QuestObjective


@dataclass(frozen=True)
class QuestDefinition:
    """The immutable runtime definition of one hand-written quest."""

    key: str
    display_name: str
    quest_type: QuestType
    rank: str = field(metadata=ref("guild_ranks", inverse="quest_definitions"))
    stages: tuple[QuestStage, ...]
    deadline_hours: int | None = None
    #: The two separately authored prose fields beside the guild grade
    #: (``rank``): why the authored arrangement, abilities, or terrain are
    #: risky, and the issuer's motivation with the local events. Both are
    #: readable offline and neither participates in completion, failure, or
    #: progress (design D-Q5).
    rating_rationale_zh: str | None = None
    background_flavor_zh: str | None = None


def _reject(definition: QuestDefinition, message: str) -> None:
    raise QuestDefinitionError(f"{definition.key}: {message}")


def _declared_hunt_fields(objective: QuestObjective) -> tuple[str, ...]:
    """The species-hunt selector fields the objective declares, by name."""
    declared = []
    if objective.region_key is not None:
        declared.append("region_key")
    if objective.species_key is not None:
        declared.append("species_key")
    if objective.countable_variant_keys:
        declared.append("countable_variant_keys")
    return tuple(declared)


def _validate_hunt_selector(
    definition: QuestDefinition,
    objective: QuestObjective,
) -> None:
    """Validate the complete regional species-hunt selector.

    Every reference is a stable registry key (a display name is never a
    selector), every countable variant is owned by the declared species, and at
    least one countable variant is an ordinary baseline variant: without that,
    the acceptance-time guarantee about ordinary-eligible living targets could
    not be expressed (design D-Q2).
    """
    region_key = objective.region_key
    if not isinstance(region_key, str) or not region_key:
        _reject(definition, "species hunt requires a non-empty region_key")
    if region_key not in WILDERNESS_REGION_REGISTRY:
        _reject(
            definition,
            f"species hunt names unknown wilderness region {region_key!r}",
        )
    species_key = objective.species_key
    if not isinstance(species_key, str) or not species_key:
        _reject(definition, "species hunt requires a non-empty species_key")
    if species_key not in MONSTER_SPECIES_REGISTRY:
        _reject(
            definition,
            f"species hunt names unknown monster species {species_key!r}",
        )
    variant_keys = objective.countable_variant_keys
    if not isinstance(variant_keys, tuple) or not variant_keys:
        _reject(
            definition,
            "species hunt requires a non-empty tuple of countable variant keys",
        )
    seen: set[str] = set()
    has_ordinary = False
    for variant_key in variant_keys:
        if not isinstance(variant_key, str) or not variant_key:
            _reject(definition, "countable variant keys must be non-empty strings")
        if variant_key in seen:
            _reject(definition, f"duplicate countable variant key {variant_key!r}")
        seen.add(variant_key)
        variant = MONSTER_VARIANT_REGISTRY.get(variant_key)
        if variant is None:
            _reject(
                definition,
                f"species hunt names unknown monster variant {variant_key!r}",
            )
        if variant.species_key != species_key:
            _reject(
                definition,
                f"countable variant {variant_key!r} belongs to species "
                f"{variant.species_key!r}, not {species_key!r}",
            )
        if variant.ordinary_variant:
            has_ordinary = True
    if not has_ordinary:
        _reject(
            definition,
            "species hunt requires at least one ordinary baseline variant "
            "among its countable variants",
        )


def _validate_site_clear_out(
    definition: QuestDefinition,
    objective: QuestObjective,
) -> None:
    """Validate the bound site clear-out selector (design D-C1/D-C2).

    The selector names one authored site and the quantity may never exceed that
    site's authored capacity: the bound set is the site's own living
    individuals, so no acceptance could ever bind more than the site owns. An
    empty or non-string key is rejected as such rather than reaching the
    registry lookup, so every rejection is a named
    :class:`QuestDefinitionError`.
    """
    site_key = objective.site_key
    if not isinstance(site_key, str) or not site_key:
        _reject(definition, "a site clear-out requires a non-empty site_key")
    site = MONSTER_SITE_REGISTRY.get(site_key)
    if site is None:
        _reject(
            definition,
            f"site clear-out names unknown authored site {site_key!r}",
        )
    if objective.quantity > site.capacity:
        _reject(
            definition,
            f"site clear-out quantity {objective.quantity} exceeds the authored "
            f"capacity {site.capacity} of site {site_key!r}",
        )


def _validate_prose(
    definition: QuestDefinition,
    field: str,
    value: object,
) -> None:
    """Reject a prose field that is not bounded Traditional Chinese player text."""
    if value is None:
        return
    if not isinstance(value, str) or not value.strip():
        _reject(definition, f"{field} must be a non-empty string or None")
    if len(value) > MAX_DEFINITION_PROSE_LENGTH:
        _reject(
            definition,
            f"{field} exceeds the {MAX_DEFINITION_PROSE_LENGTH}-character bound",
        )
    if not any(_CJK_START <= character <= _CJK_END for character in value):
        _reject(
            definition,
            f"{field} carries no CJK Unified Ideograph and is not Traditional Chinese",
        )


def ordinary_countable_variant_keys(objective: QuestObjective) -> tuple[str, ...]:
    """The objective's countable variants that are ordinary baseline variants.

    Ordinary-eligibility is derived, countability is authored (design D-Q2):
    the acceptance-time guarantee covers only ordinary variants, and
    registration guarantees at least one countable variant is ordinary, so a
    registered hunt selector never yields an empty tuple here. An objective
    that was never validated degrades to an empty tuple instead of raising.
    """
    ordinary: list[str] = []
    for variant_key in objective.countable_variant_keys:
        variant = MONSTER_VARIANT_REGISTRY.get(variant_key)
        if variant is not None and variant.ordinary_variant:
            ordinary.append(variant_key)
    return tuple(ordinary)


def _validate_destination(
    definition: QuestDefinition,
    destination: RoomLocator | None,
    kind: ObjectiveKind,
) -> None:
    if destination is None:
        _reject(definition, f"{kind.value} objective requires a destination")
    if not isinstance(destination, RoomLocator):
        _reject(definition, "destination must be a RoomLocator")
    if destination.kind is DestinationKind.ANCHOR:
        if destination.xyz is not None:
            _reject(definition, "ANCHOR locator cannot carry XYZ coordinates")
        if not destination.anchor_key:
            _reject(definition, "ANCHOR locator requires an anchor_key")
        if destination.anchor_key not in ANCHOR_PLACEMENT_REGISTRY:
            _reject(
                definition,
                f"anchor {destination.anchor_key!r} has no reachable AnchorRoom "
                "in ANCHOR_PLACEMENT_REGISTRY",
            )
    elif destination.kind is DestinationKind.GRID:
        if destination.anchor_key is not None:
            _reject(definition, "GRID locator cannot carry an anchor_key")
        xyz = destination.xyz
        if not isinstance(xyz, tuple) or len(xyz) != 3:
            _reject(definition, "GRID locator requires an (x, y, z) tuple")
        x, y, z = xyz
        if (
            isinstance(x, bool)
            or isinstance(y, bool)
            or not isinstance(x, int)
            or not isinstance(y, int)
        ):
            _reject(definition, "GRID locator x/y must be integers")
        if not isinstance(z, str) or not z:
            _reject(definition, "GRID locator z must be a non-empty map key")
        if z not in KNOWN_GRID_MAP_KEYS:
            _reject(definition, f"grid map key {z!r} is not known to the xyzgrid")
    elif destination.kind is DestinationKind.BOUND_INSTANCE:
        if destination.anchor_key is not None or destination.xyz is not None:
            _reject(definition, "BOUND_INSTANCE locator cannot carry static location fields")
    else:
        _reject(definition, f"unknown DestinationKind {destination.kind!r}")


def _escort_fields_declared(objective: QuestObjective) -> tuple[str, ...]:
    """The escort completion fields this objective declares, by name."""
    declared: list[str] = []
    if objective.completion is not None:
        declared.append("completion")
    if objective.protected_role_refs:
        declared.append("protected_role_refs")
    if objective.meeting_role_refs:
        declared.append("meeting_role_refs")
    if objective.relation is not None:
        declared.append("relation")
    return tuple(declared)


def _validate_role_refs(
    definition: QuestDefinition,
    refs: object,
    field_name: str,
) -> None:
    """Reject a malformed, empty, or duplicated published role reference tuple."""
    if not isinstance(refs, tuple) or not refs:
        _reject(
            definition,
            f"ESCORT objective requires a non-empty tuple in {field_name}",
        )
    seen: set[str] = set()
    for ref_value in refs:
        if not isinstance(ref_value, str) or not ref_value:
            _reject(
                definition,
                f"{field_name} entries must be non-empty role references",
            )
        if len(ref_value) > MAX_ROLE_REF_LENGTH:
            _reject(
                definition,
                f"{field_name} role reference {ref_value!r} exceeds the "
                f"{MAX_ROLE_REF_LENGTH}-character bound",
            )
        if ref_value in seen:
            _reject(
                definition,
                f"{field_name} contains duplicate role reference {ref_value!r}",
            )
        seen.add(ref_value)


def _validate_relation(
    definition: QuestDefinition,
    relation: object,
    declared_roles: frozenset[str],
) -> None:
    """Validate one optional rendezvous typed relation against declared roles."""
    if relation is None:
        return
    if not isinstance(relation, tuple) or len(relation) != 3:
        _reject(
            definition,
            "a rendezvous typed relation must be a (kind, from_role, to_role) tuple",
        )
    kind, from_role, to_role = relation
    if not isinstance(kind, str) or kind not in RELATIONSHIP_KINDS:
        _reject(definition, f"unknown rendezvous relation kind {kind!r}")
    for endpoint, value in (("from_role", from_role), ("to_role", to_role)):
        if not isinstance(value, str) or not value:
            _reject(
                definition,
                f"rendezvous relation {endpoint} must be a non-empty role reference",
            )
        if value not in declared_roles:
            _reject(
                definition,
                f"rendezvous relation {endpoint} {value!r} is not a declared "
                "protected or meeting role reference",
            )
    if from_role == to_role:
        _reject(
            definition,
            "a rendezvous typed relation must connect two distinct roles",
        )


def _validate_escort_completion(
    definition: QuestDefinition,
    objective: QuestObjective,
) -> None:
    """Validate the closed escort completion discriminator (escort-rendezvous §6)."""
    _validate_role_refs(
        definition, objective.protected_role_refs, "protected_role_refs"
    )
    completion = objective.completion
    if not isinstance(completion, EscortCompletion):
        _reject(
            definition,
            "ESCORT objective requires exactly one completion discriminator "
            "(destination or rendezvous)",
        )
    declared_roles = frozenset(
        (*objective.protected_role_refs, *objective.meeting_role_refs)
    )
    if completion is EscortCompletion.DESTINATION:
        if objective.meeting_role_refs:
            _reject(
                definition,
                "destination ESCORT objective cannot declare meeting role references",
            )
        if objective.relation is not None:
            _reject(
                definition,
                "destination ESCORT objective cannot declare a typed relation",
            )
        _validate_destination(definition, objective.destination, ObjectiveKind.ESCORT)
        return
    if objective.destination is not None:
        _reject(
            definition,
            "rendezvous ESCORT objective declares no destination locator",
        )
    _validate_role_refs(definition, objective.meeting_role_refs, "meeting_role_refs")
    overlap = set(objective.protected_role_refs) & set(objective.meeting_role_refs)
    if overlap:
        _reject(
            definition,
            f"ESCORT role references {sorted(overlap)} appear as both protected "
            "and meeting roles",
        )
    _validate_relation(definition, objective.relation, declared_roles)


def _validate_objective(
    definition: QuestDefinition,
    objective: QuestObjective,
) -> None:
    if not isinstance(objective, QuestObjective):
        _reject(definition, "stages must carry QuestObjective values")
    if isinstance(objective.quantity, bool) or (
        not isinstance(objective.quantity, int) or objective.quantity < 1
    ):
        _reject(definition, "objective quantity must be a positive integer")
    if objective.kind is not ObjectiveKind.ESCORT and _escort_fields_declared(
        objective
    ):
        _reject(
            definition,
            f"{objective.kind.value} objective cannot declare escort completion "
            f"fields {list(_escort_fields_declared(objective))}",
        )
    if objective.kind is ObjectiveKind.DEFEAT:
        if objective.destination is not None:
            _reject(definition, "DEFEAT objective cannot declare a destination")
        has_tier = objective.monster_tier is not None
        has_bound = objective.requires_bound_targets is True
        has_hunt = bool(_declared_hunt_fields(objective))
        has_site = objective.site_key is not None
        if has_hunt:
            if has_tier or has_bound or has_site:
                _reject(
                    definition,
                    "DEFEAT objective declares a regional species hunt beside "
                    "monster_tier, requires_bound_targets, or a site key; a hunt "
                    "declares exactly one selector family",
                )
            _validate_hunt_selector(definition, objective)
        elif has_site:
            if not has_bound:
                _reject(
                    definition,
                    "a site clear-out requires requires_bound_targets=True; a "
                    "site key alone is not a selector family",
                )
            if has_tier:
                _reject(
                    definition,
                    "DEFEAT objective declares a site key beside monster_tier; "
                    "a site clear-out declares exactly one selector family",
                )
            _validate_site_clear_out(definition, objective)
        elif has_tier == has_bound:
            _reject(
                definition,
                "DEFEAT objective must declare exactly one of a known "
                "monster_tier, requires_bound_targets=True (optionally naming a "
                "known site_key), or the complete regional species-hunt selector",
            )
        elif has_tier and objective.monster_tier not in MONSTER_TIER_REGISTRY:
            _reject(
                definition,
                f"unknown monster tier {objective.monster_tier!r}",
            )
    elif objective.kind is ObjectiveKind.REACH:
        if (
            objective.monster_tier is not None
            or objective.requires_bound_targets
            or objective.site_key is not None
        ):
            _reject(
                definition,
                "REACH objective cannot declare defeat selectors or a site "
                "clear-out",
            )
        if _declared_hunt_fields(objective):
            _reject(
                definition,
                "REACH objective cannot declare a regional species-hunt selector",
            )
        if objective.quantity != 1:
            _reject(
                definition,
                "REACH objective quantity must be exactly 1; arrival observation "
                "cannot accumulate repeated visits",
            )
        _validate_destination(definition, objective.destination, ObjectiveKind.REACH)
    elif objective.kind is ObjectiveKind.ESCORT:
        if (
            objective.monster_tier is not None
            or objective.requires_bound_targets
            or objective.site_key is not None
        ):
            _reject(
                definition,
                "ESCORT objective cannot declare defeat selectors or a site "
                "clear-out",
            )
        if _declared_hunt_fields(objective):
            _reject(
                definition,
                "ESCORT objective cannot declare a regional species-hunt selector",
            )
        if objective.quantity != 1:
            _reject(
                definition,
                "ESCORT objective quantity must be exactly 1; arrival observation "
                "cannot accumulate repeated visits",
            )
        _validate_escort_completion(definition, objective)
    elif objective.kind is ObjectiveKind.ACQUIRE:
        if (
            objective.monster_tier is not None
            or objective.destination is not None
            or objective.requires_bound_targets
            or objective.site_key is not None
        ):
            _reject(
                definition,
                "ACQUIRE objective cannot declare defeat selectors, a destination, "
                "bound-target requirements, or a site clear-out",
            )
        if _declared_hunt_fields(objective):
            _reject(
                definition,
                "ACQUIRE objective cannot declare a regional species-hunt selector",
            )
        item_key = objective.item_key
        if not isinstance(item_key, str) or not item_key:
            _reject(definition, "ACQUIRE objective requires exactly one known item_key")
        if item_key not in ITEM_REGISTRY:
            _reject(definition, f"ACQUIRE objective references unknown item {item_key!r}")
    elif objective.kind is ObjectiveKind.DELIVER:
        if objective.destination is not None:
            _reject(definition, "DELIVER objective cannot declare a destination")
        if objective.monster_tier is not None:
            _reject(definition, "DELIVER objective cannot declare a monster_tier")
        if objective.site_key is not None:
            _reject(
                definition,
                "DELIVER objective cannot declare a site clear-out; its bound "
                "targets are its delivery recipients",
            )
        if _declared_hunt_fields(objective):
            _reject(
                definition,
                "DELIVER objective cannot declare a regional species-hunt selector",
            )
        if objective.requires_bound_targets is not True:
            _reject(definition, "DELIVER objective requires requires_bound_targets to be True")
        item_key = objective.item_key
        if not isinstance(item_key, str) or not item_key:
            _reject(definition, "DELIVER objective requires an item_key")
        if item_key not in ITEM_REGISTRY:
            _reject(definition, f"DELIVER objective references unknown item_key {item_key!r}")
    else:
        _reject(definition, f"unknown ObjectiveKind {objective.kind!r}")


def validate_escort_predicate(
    definition: QuestDefinition,
    objective: QuestObjective,
) -> None:
    """Validate one escort objective's closed completion contract (public seam).

    The scene-package boundary declares an exclusive outcome group's concrete
    final result as the same closed predicate an ESCORT objective declares, so
    it validates through this one seam rather than a second copy of the grammar.
    Raises :class:`QuestDefinitionError` naming ``definition`` on any violation.
    """
    _validate_objective(definition, objective)


def validate_definition(definition: QuestDefinition) -> None:
    """Raise ``QuestDefinitionError`` unless ``definition`` is fully valid."""
    if not isinstance(definition, QuestDefinition):
        raise QuestDefinitionError(
            "quest definitions must be QuestDefinition values, not raw mappings"
        )
    if not isinstance(definition.key, str) or not definition.key:
        _reject(definition, "definition key must be a non-empty string")
    if not isinstance(definition.display_name, str) or not definition.display_name:
        _reject(definition, "display_name must be a non-empty string")
    if not isinstance(definition.quest_type, QuestType):
        _reject(definition, "quest_type must be a QuestType value")
    if not isinstance(definition.rank, str) or not definition.rank:
        _reject(definition, "rank must be a non-empty string")
    _validate_prose(definition, "rating_rationale_zh", definition.rating_rationale_zh)
    _validate_prose(definition, "background_flavor_zh", definition.background_flavor_zh)
    prose_total = len(definition.rating_rationale_zh or "") + len(
        definition.background_flavor_zh or ""
    )
    if prose_total > MAX_DEFINITION_PROSE_TOTAL:
        _reject(
            definition,
            f"authored prose totals {prose_total} characters, above the "
            f"{MAX_DEFINITION_PROSE_TOTAL}-character bound the rendered quest "
            "detail (and the frozen web detail field) can carry",
        )
    if not isinstance(definition.stages, tuple) or not definition.stages:
        _reject(definition, "stages must be a non-empty tuple of QuestStage values")
    deadline = definition.deadline_hours
    if deadline is not None and (
        isinstance(deadline, bool) or not isinstance(deadline, int) or deadline < 1
    ):
        _reject(
            definition,
            "deadline_hours must be None (no deadline) or a positive integer",
        )
    indices = [stage.index for stage in definition.stages]
    expected = list(range(len(definition.stages)))
    if not all(isinstance(stage, QuestStage) for stage in definition.stages):
        _reject(definition, "stages must carry QuestStage values")
    if indices != expected:
        _reject(
            definition,
            f"stage indices must be contiguous starting at zero, got {indices}",
        )
    for stage in definition.stages:
        _validate_objective(definition, stage.objective)


QUEST_DEFINITION_REGISTRY: dict[str, QuestDefinition] = {}


def _declared_site_keys(definition: QuestDefinition) -> frozenset[str]:
    """Every authored site key this definition's stages declare."""
    return frozenset(
        stage.objective.site_key
        for stage in definition.stages
        if stage.objective.site_key is not None
    )


def _reject_site_collisions(definition: QuestDefinition) -> None:
    """Reject a second definition over one site (design D-C6).

    Two clear-outs over one site would both bind the same living individuals, so
    two records would credit the same defeats once. Registration rejects the
    later definition and names the colliding key and definition rather than
    leaving a silent double-count to the planner. Only definitions registered
    under a *different* definition key are compared, so the equal-content
    idempotent re-registration path never collides with itself; every stage of
    both definitions is compared, not the stage-zero objective alone.
    """
    declared = _declared_site_keys(definition)
    if not declared:
        return
    for other_key, other in QUEST_DEFINITION_REGISTRY.items():
        if other_key == definition.key:
            continue
        collided = declared & _declared_site_keys(other)
        if collided:
            raise QuestDefinitionError(
                f"{definition.key}: site {sorted(collided)[0]!r} is already "
                f"declared by registered definition {other_key!r}"
            )


def register_quest_definition(definition: QuestDefinition) -> None:
    """Register one validated, immutable definition idempotently.

    Registering equal content under an existing key is a no-op; conflicting
    content under an existing key raises before replacing anything. A definition
    declaring a site another registered definition already declares is rejected
    before it is stored.
    """
    validate_definition(definition)
    current = QUEST_DEFINITION_REGISTRY.get(definition.key)
    if current is not None:
        if current == definition:
            return
        raise QuestDefinitionError(
            f"{definition.key}: conflicting content already registered"
        )
    _reject_site_collisions(definition)
    QUEST_DEFINITION_REGISTRY[definition.key] = definition