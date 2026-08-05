"""Frozen read-only art-panel view model (design D2/D3).

The art panel (WebClient ``art``) is built from canonical state by this module:
the actor's current location's validated ``scene_archetype`` and the bounded,
deterministic set of currently present focusable entities. In combat mode the
entity set comes from the shared roster query
``world.rules.combat_view.combat_participants`` so the ``context_actions`` and
``art`` panels can never drift on membership or order; in exploration mode it
comes from the current room's ``contents`` filtered to dialogue hosts and
characters carrying an explicit named portrait policy, in deterministic
room-contents order.

The module performs no writes, never lazily constructs a trait/buff/sexual
handler, never reads ``disguised_stats`` or persona, and returns frozen values.
The single catalog-key mapper ``portrait_catalog_key`` is shared with the
combat view so a focus lookup can never silently miss because of an ``42`` vs
``"42"`` mismatch.
"""

from dataclasses import dataclass
from typing import Any, Callable

from world.art.subjects import ArtSubjectError, character_subject_for
from world.lore.monsters import MONSTER_TIER_REGISTRY
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


class ArtViewError(ValueError):
    """The art panel cannot read required canonical data without mutation."""


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
        scene_archetype: The actor's current location's validated
            ``scene_archetype``, or ``None`` when unresolved or invalid.
        entities: The bounded, deterministic, currently present focusable set.
    """

    scene_archetype: str | None
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

    Classification is explicit and registry-backed: a monster whose
    ``threat_tier`` resolves in ``MONSTER_TIER_REGISTRY`` is a generic monster;
    a character carrying an explicit named ``portrait_policy`` is a named
    character; anything else is ``none``. It is never inferred from display
    name, key shape, or LLM authorship.
    """
    threat_tier = getattr(entity, "threat_tier", None)
    if threat_tier in MONSTER_TIER_REGISTRY:
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
    order, capped at ``MAX_PORTRAIT_CATALOG``. The actor itself is never a
    present focusable subject of their own exploration catalog.
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
    return tuple(candidates[:MAX_PORTRAIT_CATALOG])


def build_art_view(
    actor: Any,
    *,
    resolver: Callable[[Any], Any] = _default_resolver,
) -> ArtView:
    """Build the frozen art panel view for ``actor``.

    In combat mode the entity set comes from the shared roster query; in
    exploration mode it comes from the current room's present contents. The
    scene archetype is the actor's current location's validated
    ``scene_archetype``; an unresolvable or invalid archetype is ``None`` (the
    scene payload then degrades to the unavailable placeholder). Never writes
    state and never reads ``disguised_stats`` or persona.
    """
    location = getattr(actor, "location", None)
    scene_archetype = None
    if location is not None:
        archetype = getattr(location, "scene_archetype", None)
        if archetype in SCENE_ARCHETYPE_REGISTRY:
            scene_archetype = archetype
    if is_in_active_session(actor):
        entities = _combat_entities(actor, resolver)
    else:
        entities = _exploration_entities(location, actor)
    return ArtView(scene_archetype=scene_archetype, entities=entities)


__all__ = [
    "ArtEntityView",
    "ArtView",
    "ArtViewError",
    "MAX_PORTRAIT_CATALOG",
    "ROLE_ALLY",
    "ROLE_DIALOGUE",
    "ROLE_FOE",
    "ROLE_PERSON",
    "SUBJECT_CHARACTER",
    "SUBJECT_MONSTER",
    "SUBJECT_NONE",
    "build_art_view",
    "portrait_catalog_key",
]
