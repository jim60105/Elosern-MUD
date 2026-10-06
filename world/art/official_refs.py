"""Typed official content references and the provenance rules that derive them.

``official-content-provenance`` (source design §6): resolution against the
mounted official-artwork catalog needs to know *which* authored content an
entity is. That identity is a separate thing from the entity's runtime art
subject: the runtime subject keys mutable gallery state and generated artwork,
while the official content reference names reusable authored images in the
official directory. This module is the one owner of that second identity.

A reference is a validated ``(kind, key)`` pair. The content kind is exactly
``monster``, ``preset``, or ``npc`` — the closed vocabulary
``world.art.official`` indexes (``OFFICIAL_CONTENT_KINDS``). The vocabulary is
duplicated here as literals BY DESIGN, the ``world/art/gallery_kinds.py``
discipline: this module is a leaf the presenter and spawn sides may import, and
it may not drag the catalog's Pillow/Django/no-follow chain behind it. The
contract test ``test_official_refs.py`` fails if the two tuples ever diverge.
The key grammar is *not* duplicated: it is the published shared predicate
``world.art.subjects.is_valid_subject_key``, which the catalog admission check
also calls, so a key the catalog indexed can never be refused here.

**Derived only from provenance.** ``official_content_reference_for_entity``
reads exactly three entity attributes — ``creation_preset_key`` (written by the
preset activation and companion-build paths), ``npc_profile_key`` (written at
the settlement-host and guild-examiner creation paths) and ``species_key``
(``typeclasses.monsters.Monster``, written by ``monster-identity-construction``,
the sibling change that owns the field). It reads no display name, translated
label, quest role, database row identity, service anchor, threat tier, variant
key, or free text, and its read surface is pinned to exactly those three names
by a test, so no inference path can exist. A declared key that is malformed or
absent from the owning registry resolves to nothing and emits one bounded
``official_content_reference_unresolved`` warning (deduped per distinct key,
capped per process). A caller-supplied key — the preset-preview entry point —
resolves silently: a direct authored-channel lookup is not a named entity's
stored provenance.

**Provenance writes are owned elsewhere, one writer per path.** This module
never writes: no record, no card, no store copy, no attribute. The writers are
the creation/import/spawn paths that already establish an NPC's other authored
attributes. Two populations deliberately record nothing, because their shapes
carry no authored profile identity and a generated channel is never an authored
one: blueprint-characterized quest occupants (their persona provenance is
``generated_quest``) and imported NPC records (their provenance is ``import``).
Neither infers a profile identity from a display name, an entity key, a tier, a
role, or a service anchor.

**Monsters: one official image per species key** (``species-portrait-identity``).
The ``monster`` kind's membership authority is
``world.lore.monster_species.MONSTER_SPECIES_REGISTRY``; the single producer,
``_species_content_reference``, reads the individual's own stored ``species_key``
and answers that species' reference, so a species-backed monster presents the
mounted ``monster/<species-key>/`` artwork as its official default and every
variant of one species shares that one image identity. No code path here maps a
threat tier, a display name, or a variant key to a species: a present-but-bad
stored value is refused exactly like any other unregistered key, and a tier-only
individual (no stored species identity) resolves no reference at all. An
unmounted species directory is pure fall-through — the chain continues with
runtime artwork or the built-in silhouette — and the tier-validated
``portrait:monster:<tier>`` subject keeps serving the generic silhouette/gallery
layer unchanged, so the two identity layers can never be confused. A
tier-named ``monster/<tier>/`` directory may be indexed by the catalog, but it
is unreachable through this layer: a threat tier is not a registered species
key, and no alias table exists.

Two operator-facing statements of this layer belong to other owners and are
recorded here as the pointer rather than restated: authoring a
``monster/<tier>/`` directory does not select artwork, and species-specific
official monster art presents only for a registered species key whose directory
the mounted catalog holds. The deployment guide
(``docs/development/official-artwork-deployment.md``, owned by the
``official-artwork-deployment`` change) carries the operator-facing layout
statement, and ``docs/development/settings-and-environment.md`` carries the
``ART_OFFICIAL_ROOT`` contract.

**Entity identity is a hash input only.** An entity with no named portrait
subject is never manufactured into one here: this module installs no
``portrait_policy``, creates no gallery record, and enqueues no generation, and
its runtime identity never becomes an official content reference.

Import discipline: stdlib, the shared subject-key predicate and its bounds, the
two immutable lore registries, and the observability facade. There is no direct
import of ``world.art.official`` (the catalog's Pillow/Django/no-follow chain
is what the duplicated vocabulary exists to avoid), of any ``world.rules.*``
module, of ``typeclasses``, or of Evennia/Django; the boundary test pins that
import set so no cycle or transport dependency can creep in.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from world.art.subjects import MAX_SUBJECT_KEY_LENGTH, is_valid_subject_key
from world.lore.monster_species import MONSTER_SPECIES_REGISTRY
from world.lore.npc_profiles import NPC_PROFILE_REGISTRY
from world.lore.player_presets import PLAYER_PRESET_REGISTRY
from world.observability import log_warn

# The closed content-kind vocabulary, in the catalog's documented layout order.
# Duplicated BY DESIGN from ``world.art.official.OFFICIAL_CONTENT_KINDS`` — this
# module may not import that module — and locked equal by a contract test.
OFFICIAL_KIND_MONSTER = "monster"
OFFICIAL_KIND_PRESET = "preset"
OFFICIAL_KIND_NPC = "npc"
OFFICIAL_CONTENT_KINDS = (
    OFFICIAL_KIND_MONSTER,
    OFFICIAL_KIND_PRESET,
    OFFICIAL_KIND_NPC,
)

# The entity-carried provenance attribute names this resolver reads. The preset
# name is the one ``world/art/gallery_fallback.py`` declares (a contract test
# locks the two literals equal); the profile name is this change's authored NPC
# provenance, written at the host/examiner creation sites.
PRESET_PROVENANCE_ATTRIBUTE = "creation_preset_key"
NPC_PROFILE_PROVENANCE_ATTRIBUTE = "npc_profile_key"
# The monster arm's provenance name: the field
# ``typeclasses.monsters.Monster`` carries (``monster-identity-construction``,
# the sibling change that owns and writes it). This module reads it as a stored
# attribute name only — it may not import ``typeclasses`` — so the reference
# chain stays a leaf, and one named constant keeps the name in a single place
# beside the other two read names.
SPECIES_PROVENANCE_ATTRIBUTE = "species_key"

# The one bounded diagnostic id for a declared-but-unresolvable reference.
UNRESOLVED_REFERENCE_EVENT = "official_content_reference_unresolved"

# The per-process ceiling on distinct reported keys: a repeating bad key is
# reported once (its presentation repeats on every resolve), and the dedupe set
# is memory-bounded. Reached, further distinct keys are suppressed.
MAX_UNRESOLVED_DIAGNOSTICS = 64

# The dedupe origin: distinct ``(kind, key)`` pairs already reported. Only the
# test patch seam rewrites this; no consumer API hands it out.
_reported_unresolved: set[tuple[str, str]] = set()


class OfficialContentReferenceError(ValueError):
    """Raised when an official content reference is constructed malformed."""


@dataclass(frozen=True)
class OfficialContentReference:
    """One typed, validated ``(content kind, registered content key)`` pair.

    Construction validates the SHAPE only — the kind is inside the closed
    vocabulary and the key satisfies the shared stable-key contract. Registry
    membership is deliberately checked at resolution time against the live
    registries, never cached at construction, so a reference value stays a pure
    value object and an entity's stored provenance is always judged against the
    registries as they are now.
    """

    kind: str
    key: str

    def __post_init__(self) -> None:
        if self.kind not in OFFICIAL_CONTENT_KINDS:
            raise OfficialContentReferenceError(
                f"unknown official content kind {self.kind!r}; "
                f"expected one of {OFFICIAL_CONTENT_KINDS}"
            )
        if not is_valid_subject_key(self.key):
            raise OfficialContentReferenceError(
                "an official content key must satisfy the shared stable-key contract"
            )

    def identity(self) -> str:
        """The root-relative content-directory identity, e.g. ``preset/hero``."""
        return f"{self.kind}/{self.key}"


def _entity_attributes(entity: Any) -> Any:
    """The entity's attribute store, or ``None`` when it carries none."""
    if entity is None:
        return None
    return getattr(entity, "attributes", None)


def _entity_identity(entity: Any) -> str:
    """The stable identity a diagnostic may name, never a display name."""
    pk = getattr(entity, "pk", None)
    if pk is None:
        return type(entity).__name__
    return str(pk)


def _emit_unresolved(kind: str, declared: Any, entity: Any, reason: str) -> None:
    """Emit the one bounded diagnostic for a declared-but-unresolvable key.

    Deduped per distinct ``(kind, key)`` pair within the per-process ceiling, so
    a presentation-repeating bad key logs once instead of per resolve. The
    context carries business identifiers only: the kind, the (length-bounded)
    declared key, the entity identity, and the reason. The text is bounded both
    ways — truncated to the contract's key length and stripped of anything
    non-printable — because a malformed stored value never passed the grammar
    that would have made it safe to log verbatim.
    """
    key_text = "".join(
        character
        for character in str(declared)[:MAX_SUBJECT_KEY_LENGTH]
        if character.isprintable()
    )
    dedupe = (kind, key_text)
    if dedupe in _reported_unresolved:
        return
    if len(_reported_unresolved) >= MAX_UNRESOLVED_DIAGNOSTICS:
        return
    _reported_unresolved.add(dedupe)
    log_warn(
        UNRESOLVED_REFERENCE_EVENT,
        context={
            "kind": kind,
            "key": key_text,
            "entity": _entity_identity(entity),
            "reason": reason,
        },
    )


def _registry_for(kind: str) -> Mapping[str, Any] | None:
    """The live registry owning a kind's content keys, or ``None`` when absent.

    ``preset`` resolves against the player-preset registry, ``npc`` against the
    authored NPC profile registry, and ``monster`` against the species registry
    (``monster-species-registry``): the species vocabulary IS the monster kind's
    content vocabulary, so a threat tier is never a member of it.
    """
    if kind == OFFICIAL_KIND_MONSTER:
        return MONSTER_SPECIES_REGISTRY
    if kind == OFFICIAL_KIND_PRESET:
        return PLAYER_PRESET_REGISTRY
    if kind == OFFICIAL_KIND_NPC:
        return NPC_PROFILE_REGISTRY
    return None


def registered_content_key(kind: str, key: str) -> bool:
    """True when ``key`` names registered authored content of ``kind``.

    Read from the live registries per call (the
    ``gallery_fallback._declared_key_for_entity`` precedent), never cached at
    import, so a registry entry added after this module loaded is honored. Every
    kind has exactly one membership authority: ``preset``, ``npc``, and
    ``monster`` (the species registry), and an unknown kind registers nothing.
    """
    registry = _registry_for(kind)
    if registry is None:
        return False
    return key in registry


def official_content_reference(
    kind: str, key: object
) -> OfficialContentReference | None:
    """The validated reference for an authored ``(kind, key)`` pair, else ``None``.

    The authored-channel entry point: a caller that already holds a content key
    (a creation preview, the species arm's own lookup) asks here. An
    unknown kind, a key outside the shared stable-key contract, and a key the
    owning registry does not declare each answer ``None`` — never a substituted
    reference.
    """
    if kind not in OFFICIAL_CONTENT_KINDS:
        return None
    if not is_valid_subject_key(key):
        return None
    if not registered_content_key(kind, key):
        return None
    return OfficialContentReference(kind, key)


def official_content_reference_for_preset(preset_key: object) -> OfficialContentReference | None:
    """The preset reference a creation preview resolves from the preset key.

    Takes the authored preset key directly rather than a synthetic entity, so a
    preview can never create or touch a character, a gallery record, or stored
    artwork. Silent by design: a caller-supplied key is not a named entity's
    stored provenance, so an unresolvable one simply yields no reference and the
    preview falls back to the runtime chain.
    """
    return official_content_reference(OFFICIAL_KIND_PRESET, preset_key)


def _declared_reference(
    kind: str, declared: Any, entity: Any
) -> OfficialContentReference | None:
    """Resolve one entity-carried declared key, with its bounded diagnostic."""
    if not isinstance(declared, str) or not declared:
        _emit_unresolved(kind, declared, entity, "malformed_key")
        return None
    if not is_valid_subject_key(declared):
        _emit_unresolved(kind, declared, entity, "malformed_key")
        return None
    if not registered_content_key(kind, declared):
        _emit_unresolved(kind, declared, entity, "unregistered_key")
        return None
    return OfficialContentReference(kind, declared)


def _species_content_reference(entity: Any) -> OfficialContentReference | None:
    """The species-keyed official reference for a monster, or ``None``.

    The ``monster`` kind's content key is the individual's own stored species
    identity, which every variant of that species shares (design §7: official
    monster artwork is shared by species, never by threat tier). The value is
    read here as a stored attribute of the entity passed in — never the threat
    tier, the display name, or the variant key — so this function can only ever
    answer with that entity's own reference.

    An absent attribute (a tier-only individual) answers ``None`` silently, the
    way the preset and profile arms treat a missing provenance. A present value
    resolves through the shared :func:`_declared_reference` path, so a malformed
    or unregistered one degrades with the same single bounded diagnostic and
    falls through to the runtime/silhouette chain exactly as an absent one does.

    The arm is deliberately kind-agnostic: it reads the attribute NAME, so any
    entity that ever stores a registered species key resolves that species'
    reference. Today only ``typeclasses.monsters.Monster`` carries the field
    (the sibling change owns writing it); this module may not import
    ``typeclasses`` to check the class, and no other producer writes the name.
    """
    attributes = _entity_attributes(entity)
    if attributes is None:
        return None
    declared = attributes.get(SPECIES_PROVENANCE_ATTRIBUTE)
    if declared is None:
        return None
    return _declared_reference(OFFICIAL_KIND_MONSTER, declared, entity)


def official_content_reference_for_entity(entity: Any) -> OfficialContentReference | None:
    """The official content reference an entity's stored provenance declares.

    The ordered arms are exactly the provenance attributes an authored path
    writes: ``creation_preset_key`` (preset-born characters and companions),
    then ``npc_profile_key`` (authored settlement hosts and guild examiners),
    then the species arm (``species_key``, a monster's stored species identity).
    An entity carrying none of them — every dynamically generated NPC, every
    imported NPC, every blueprint occupant, every tier-only monster — resolves
    ``None``, so its presentation stays on the runtime chain. Nothing here is
    inferred from a display name, a threat tier, a variant key, a role, a row
    identity, a service anchor, or any other stored text.
    """
    attributes = _entity_attributes(entity)
    if attributes is not None:
        preset_key = attributes.get(PRESET_PROVENANCE_ATTRIBUTE)
        if preset_key is not None:
            reference = _declared_reference(
                OFFICIAL_KIND_PRESET, preset_key, entity
            )
            if reference is not None:
                return reference
        profile_key = attributes.get(NPC_PROFILE_PROVENANCE_ATTRIBUTE)
        if profile_key is not None:
            reference = _declared_reference(OFFICIAL_KIND_NPC, profile_key, entity)
            if reference is not None:
                return reference
    return _species_content_reference(entity)


__all__ = [
    "MAX_UNRESOLVED_DIAGNOSTICS",
    "NPC_PROFILE_PROVENANCE_ATTRIBUTE",
    "OFFICIAL_CONTENT_KINDS",
    "OFFICIAL_KIND_MONSTER",
    "OFFICIAL_KIND_NPC",
    "OFFICIAL_KIND_PRESET",
    "PRESET_PROVENANCE_ATTRIBUTE",
    "SPECIES_PROVENANCE_ATTRIBUTE",
    "UNRESOLVED_REFERENCE_EVENT",
    "OfficialContentReference",
    "OfficialContentReferenceError",
    "official_content_reference",
    "official_content_reference_for_entity",
    "official_content_reference_for_preset",
    "registered_content_key",
]
