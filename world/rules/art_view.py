"""Frozen read-only art-panel view model (design D2/D3).

The art panel (WebClient ``art``) is built from canonical state by this module:
the actor's current location's complete read-only scene metadata — its logical
place identity, its validated ``scene_archetype`` and its optional registered
``room_art_key`` — and the bounded, deterministic set of currently present
focusable entities. In combat mode the entity set comes from the shared roster query
``world.rules.combat_view.combat_participants`` so the ``context_actions`` and
``art`` panels can never drift on membership or order; in exploration mode it
comes from the current room's ``contents`` filtered to dialogue hosts and
characters carrying an explicit named portrait policy, then co-located party
companions in party order.

The module performs no writes, never lazily constructs a trait/buff/sexual
handler, never reads ``disguised_stats`` or persona, and returns frozen values.
The single catalog-key mapper ``portrait_catalog_key`` is shared with the
combat view so a focus lookup can never silently miss because of an ``42`` vs
``"42"`` mismatch.
"""

from dataclasses import dataclass
from typing import Any, Callable

from world.art.subjects import ArtSubjectError, character_subject_for
from world.art.subjects import is_valid_subject_key
from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY
from world.rules.combat_session import is_in_active_session
from world.rules.combat_view import MAX_DISPLAY_NAME_CODE_POINTS, combat_participants
from world.rules.dialogue import is_dialogue_host

# The bounded portrait-catalog ceiling (matches the inventory row bound).
MAX_PORTRAIT_CATALOG = 32

# Stable role labels for the portrait-catalog display context.
ROLE_ALLY = "隊友"
ROLE_FOE = "敵方"
ROLE_DIALOGUE = "對話對象"
ROLE_PERSON = "人物"

# Subject-kind classification values carried by each catalog entry.
SUBJECT_CHARACTER = "character"
SUBJECT_MONSTER = "monster"
SUBJECT_NONE = "none"

# Presentation bounds owned by the art view (equal or below wire limits).
MAX_ROLE_CODE_POINTS = 16

# The bounded logical identity of a puppet that is in no location at all: a
# constant, because there is no logical place to name, and deliberately never a
# retention-authorized identity (no authored metadata backs it).
UNLOCATED_SCENE_IDENTITY = "room:none"

# The bounded placeholder a per-room binding that fails even the shared
# stable-key contract is named by. The raw attribute value is never echoed onto
# the wire, so a malformed stored value can neither leak nor exceed a bound.
INVALID_ROOM_BINDING_KEY = "invalid"


class ArtViewError(ValueError):
    """The art panel cannot read required canonical data without mutation."""


@dataclass(frozen=True)
class SceneTarget:
    """The complete read-only logical scene input one scene resolution reads.

    Attributes:
        identity: The bounded logical place identity the descriptor is keyed
            by. ``scene_identity`` when the map owner declared one; otherwise a
            bounded runtime fallback (never an authored-place identity).
        trusted_identity: True exactly when ``identity`` came from the map
            owner's authored metadata. Only a trusted identity may authorize
            retained display content, so a fallback identity can never make two
            different places look like one.
        archetype: The registered scene archetype the room renders from, or
            ``None`` when the room's authored metadata cannot be honored (an
            absent or unregistered value) — the malformed case the scene
            resolution states explicitly instead of hiding.
        room_art_key: The registered per-room operator override key, or
            ``None`` when the room declares none (or declares an unusable one
            that cannot be safely named).
        room_binding_invalid: True when the room DOES declare a room-art key
            that cannot be honored. It is deliberately distinct from "declares
            none": an authored override that cannot resolve is a
            configuration-failure fact, never an expected absence.

    Nothing here is written anywhere: the target is a frozen read of the
    room's already-stored attributes.
    """

    identity: str
    trusted_identity: bool
    archetype: str | None
    room_art_key: str | None
    room_binding_invalid: bool


@dataclass(frozen=True)
class ArtEntityView:
    """One currently present focusable entity in the portrait catalog.

    Attributes:
        identity: The positive opaque ObjectDB dbref used as the catalog key.
        display_name: The bounded display name.
        role: The stable role label (ally/foe/dialogue/person).
        subject_kind: The portrait subject decision: ``character`` for an
            explicit named portrait policy, ``monster`` for a bestiary
            ``threat_tier`` archetype, or ``none``.
    """

    identity: int
    display_name: str
    role: str
    subject_kind: str


@dataclass(frozen=True)
class ArtView:
    """The complete frozen read-only art panel inputs.

    Attributes:
        scene: The actor's current location's complete read-only logical scene
            input — its logical place identity, its validated archetype and its
            optional registered room-art key, with the invalid-metadata facts
            the scene resolution states rather than hides.
        entities: The bounded, deterministic, currently present focusable set.
    """

    scene: SceneTarget
    entities: tuple[ArtEntityView, ...]


def portrait_catalog_key(identity: Any) -> str:
    """Return the single bounded decimal-string form of a catalog key.

    Both ``build_art_view`` (to key the catalog) and
    ``world.rules.combat_view`` (to fill ``portrait_ref``) use exactly this
    mapper, so a combat participant's ``portrait_ref`` is guaranteed to match
    the art catalog key for the same identity.
    """
    return str(int(identity))


def _default_resolver(identity: Any):
    """Resolve one dbref to a live entity through the default ObjectDB query."""
    from evennia.objects.models import ObjectDB

    return ObjectDB.objects.filter(id=int(identity)).first()


def _bounded_identity(value: Any, maximum: int) -> str | None:
    """One non-empty authored identity inside its code-point bound, or ``None``."""
    if not isinstance(value, str) or not value:
        return None
    if sum(1 for _ in value) > maximum:
        return None
    return value


def _room_art_binding(value: Any) -> tuple[str | None, bool]:
    """Read one room's authored ``room_art_key`` as ``(key, invalid)``.

    A registered key is a binding the room-art chain presents. A value that is
    not a registered key is an authored override that cannot be honored: it is
    reported as ``invalid`` and is named only when it satisfies the shared
    stable-key contract, so an arbitrary stored value never reaches the wire.
    """
    from world.art.scene_definitions import is_registered_room_art_key

    if value is None:
        return None, False
    if is_registered_room_art_key(value):
        return value, False
    return (value if is_valid_subject_key(value) else None), True


def scene_target_for(location: Any) -> SceneTarget:
    """Read one location's authored scene metadata into the frozen scene target.

    Every fact is read, never inferred: the archetype and the room-art key are
    honored only when they are registered values, and the logical identity is
    the map owner's ``scene_identity`` or a bounded runtime fallback that never
    authorizes retained content. A room that is not a location at all (a puppet
    in Limbo, a creation-pending shell) resolves the same way as a room whose
    metadata cannot be honored: an explicit malformed-metadata target, never a
    silently missing scene.
    """
    from world.maps.room_art import MAX_SCENE_IDENTITY_CODE_POINTS

    if location is None:
        return SceneTarget(
            identity=UNLOCATED_SCENE_IDENTITY,
            trusted_identity=False,
            archetype=None,
            room_art_key=None,
            room_binding_invalid=False,
        )
    archetype = getattr(location, "scene_archetype", None)
    if not isinstance(archetype, str) or archetype not in SCENE_ARCHETYPE_REGISTRY:
        archetype = None
    room_art_key, room_binding_invalid = _room_art_binding(
        getattr(location, "room_art_key", None)
    )
    identity = _bounded_identity(
        getattr(location, "scene_identity", None), MAX_SCENE_IDENTITY_CODE_POINTS
    )
    if identity is not None:
        return SceneTarget(
            identity=identity,
            trusted_identity=True,
            archetype=archetype,
            room_art_key=room_art_key,
            room_binding_invalid=room_binding_invalid,
        )
    try:
        runtime_identity = str(int(location.pk))
    except (AttributeError, TypeError, ValueError):
        runtime_identity = "none"
    return SceneTarget(
        identity=f"room:{runtime_identity}",
        trusted_identity=False,
        archetype=archetype,
        room_art_key=room_art_key,
        room_binding_invalid=room_binding_invalid,
    )


def _bound(value: str, maximum: int, field: str) -> str:
    if sum(1 for _ in value) > maximum:
        raise ArtViewError(f"{field} exceeds {maximum} code points")
    return value


def _role_for(entity: Any, *, party: frozenset[int] | None = None) -> str:
    if party is not None:
        return ROLE_ALLY if int(entity.pk) in party else ROLE_FOE
    if is_dialogue_host(entity):
        return ROLE_DIALOGUE
    return ROLE_PERSON


def _classify_subject(entity: Any) -> str:
    """Classify one present entity's portrait subject decision.

    Classification is explicit: an entity of typeclass ``Monster`` is a monster;
    a character carrying an explicit named ``portrait_policy`` is a named
    character; anything else is ``none``. It is never inferred from display
    name, key shape, or LLM authorship.
    """
    from typeclasses.monsters import Monster

    if isinstance(entity, Monster):
        return SUBJECT_MONSTER
    try:
        subject = character_subject_for(entity)
    except ArtSubjectError:
        subject = None
    if subject is not None:
        return SUBJECT_CHARACTER
    return SUBJECT_NONE


def _entity_view(entity: Any, party: frozenset[int] | None) -> ArtEntityView:
    return ArtEntityView(
        identity=int(entity.pk),
        display_name=_bound(
            str(entity.key), MAX_DISPLAY_NAME_CODE_POINTS, "display_name"
        ),
        role=_role_for(entity, party=party),
        subject_kind=_classify_subject(entity),
    )


def _combat_entities(actor: Any, resolver: Callable[[Any], Any]) -> tuple[ArtEntityView, ...]:
    """Build the combat-mode entity set from the shared roster query."""
    from world.rules.combat_session import read_session

    record = read_session(actor)
    if record is None:
        raise ArtViewError("no active combat session")
    party = frozenset(record.player_ids)
    entities: list[ArtEntityView] = []
    for identity in combat_participants(actor):
        entity = resolver(identity)
        if entity is None:
            # A no-longer-present participant is not currently focusable.
            continue
        entities.append(_entity_view(entity, party=party))
        if len(entities) >= MAX_PORTRAIT_CATALOG:
            break
    return tuple(entities)


def _exploration_entities(location: Any, actor: Any) -> tuple[ArtEntityView, ...]:
    """Build the exploration-mode entity set from the current room's contents.

    Filters ``location.contents`` to dialogue hosts and characters carrying an
    explicit named portrait policy, sorted by numeric database ID so the
    catalog order never depends on the database's content-cache iteration
    order, then appends live co-located owner-party companions in party order,
    deduplicated and capped at ``MAX_PORTRAIT_CATALOG``. A controlled companion
    remains a catalog member while possessing; ordinary player actors do not.
    """
    if location is None:
        return ()
    actor_id = int(actor.pk)
    candidates: list[ArtEntityView] = []
    for entity in getattr(location, "contents", ()):
        if int(entity.pk) == actor_id:
            continue
        if not is_dialogue_host(entity) and _classify_subject(entity) != SUBJECT_CHARACTER:
            continue
        candidates.append(_entity_view(entity, party=None))
    candidates.sort(key=lambda view: view.identity)
    from typeclasses.npcs import NPC
    from world.rules.party import bound_owner_of, live_companions

    owner = bound_owner_of(actor) if isinstance(actor, NPC) else actor
    seen = {view.identity for view in candidates}
    for companion in live_companions(owner) if owner is not None else ():
        identity = int(companion.pk)
        if companion.location != location or identity in seen:
            continue
        # The controlled NPC's party ref must resolve beside status.actor.
        candidates.append(_entity_view(companion, party=frozenset({identity})))
        seen.add(identity)
    return tuple(candidates[:MAX_PORTRAIT_CATALOG])


def build_art_view(
    actor: Any,
    *,
    resolver: Callable[[Any], Any] = _default_resolver,
) -> ArtView:
    """Build the frozen art panel view for ``actor``.

    In combat mode the entity set comes from the shared roster query; in
    exploration mode it comes from the current room's present contents. The
    scene input is the actor's current location's complete read-only metadata
    (its logical place identity, its validated archetype and its optional
    registered room-art key), so the scene resolution downstream can state a
    malformed override explicitly instead of hiding it. Never writes state and
    never reads ``disguised_stats`` or persona.
    """
    location = getattr(actor, "location", None)
    if is_in_active_session(actor):
        entities = _combat_entities(actor, resolver)
    else:
        entities = _exploration_entities(location, actor)
    return ArtView(scene=scene_target_for(location), entities=entities)


__all__ = [
    "ArtEntityView",
    "ArtView",
    "ArtViewError",
    "INVALID_ROOM_BINDING_KEY",
    "MAX_PORTRAIT_CATALOG",
    "ROLE_ALLY",
    "ROLE_DIALOGUE",
    "ROLE_FOE",
    "ROLE_PERSON",
    "SceneTarget",
    "SUBJECT_CHARACTER",
    "SUBJECT_MONSTER",
    "SUBJECT_NONE",
    "UNLOCATED_SCENE_IDENTITY",
    "build_art_view",
    "portrait_catalog_key",
    "scene_target_for",
]
