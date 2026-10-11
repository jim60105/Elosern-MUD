"""The one shared deterministic actor materializer (design §5.3).

Both scene paths build actors here: the accepted-stage SceneBuilder
(:mod:`world.quests.scene_builder`) and the pre-acceptance encounter boundary
(:mod:`world.quests.encounter_activation`). Extracting the focused
creation/initialization steps keeps a single construction path, so the
whitelisted prototype gate, the shared characterization/age rules, the
registry-derived traits, the named portrait policy, the persona card, and the
lineage auto-seed are applied identically everywhere.

A conversable role spawns as the whitelisted ``scene_llm_npc`` prototype (an
``LLMNPC`` carrying the scripted-dialogue capability the existing topic
interaction needs). Unrelated monsters and non-conversable prototypes are never
converted: the non-conversable path keeps the plain ``scene_npc`` prototype.

The module is deterministic (no generative import, no live transport) and never
writes quest state; it spawns and configures actors only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from evennia.prototypes.spawner import spawn

from typeclasses.components import ScriptedDialogue
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from world.lore.npc_card import NpcCard, NpcCardError
from world.lore.npc_tiers import NPC_TIER_REGISTRY
from world.lore.scene_archetypes import SCENE_ARCHETYPE_REGISTRY
from world.quests.characterization import characterize_errors, race_lifespan_upper_bound
from world.quests.compile.contracts import StageNpcCharacterization
from world.rules.npc_identity import validate_npc_name, validate_npc_title
from world.rules.npc_persona import NpcPersonaStorageError, initialize_npc_persona
from world.rules.progression import apply_lineage_auto_seed
from world.rules.traits import build_initial_traits, trait_config_for_values

#: The closed occupant prototype whitelist. ``scene_monster`` is the only
#: monster path; ``scene_llm_npc`` is the conversable generated-role path.
SCENE_OCCUPANT_PROTOTYPE_WHITELIST: tuple[str, ...] = (
    "scene_npc",
    "scene_monster",
    "scene_llm_npc",
)

#: The plain authored default age for a portrait-bearing occupant whose
#: blueprint declared no ages (design D3). Race-agnostic and always within the
#: zero-to-lifespan validation range for every race.
PORTRAIT_DEFAULT_AGE = 25

_FALLBACK_SCENE_NAME = "任務場景"


class SceneBuilderError(RuntimeError):
    """Base class for deterministic scene-materialization rejections."""


class SceneBuilderNotActive(SceneBuilderError):
    """The referenced quest record is unknown, inactive, or stage-mismatched."""


class SceneBuilderNoRequirements(SceneBuilderError):
    """The current stage has no registered spawn requirements (hand-written quest)."""


class SceneBuilderLocationError(SceneBuilderError):
    """The caller is not at a valid origin for the stage's destination."""


class SceneBuilderSpawnError(SceneBuilderError):
    """A scene key failed to resolve or the spawner produced an invalid object."""


class SceneBuilderRoleUnavailable(SceneBuilderError):
    """A required package-owned role has no available actor (never repaired)."""


@dataclass(frozen=True)
class RoleSpawn:
    """One validated actor to materialize for a role.

    ``characterization`` is required (the authored identity invariant holds on
    every spawn path); ``conversable`` selects the whitelisted generative-NPC
    prototype and, when a ``dialogue_key`` is supplied, seeds the scripted
    dialogue component.
    """

    role: str
    tier: str
    disposition: str | None
    characterization: StageNpcCharacterization
    conversable: bool = False
    dialogue_key: str | None = None


def scene_name(archetype_key: str | None) -> str:
    if archetype_key is None:
        return _FALLBACK_SCENE_NAME
    archetype = SCENE_ARCHETYPE_REGISTRY.get(archetype_key)
    return _FALLBACK_SCENE_NAME if archetype is None else archetype.display_name_zh


def validate_occupant_parent(prototype: dict) -> None:
    """Reject any occupant prototype outside the whitelist, and an override.

    Rejects an explicit ``typeclass`` override so the whitelist gates the actual
    spawned type, not merely the claimed parentage (mirrors
    ``world.maps.instance``).
    """
    parent = prototype.get("prototype_parent")
    if parent not in SCENE_OCCUPANT_PROTOTYPE_WHITELIST:
        raise SceneBuilderSpawnError(
            f"prototype_parent {parent!r} is not in "
            "SCENE_OCCUPANT_PROTOTYPE_WHITELIST"
        )
    typeclass = prototype.get("typeclass")
    if typeclass is not None:
        raise SceneBuilderSpawnError(
            "a scene-occupant prototype must not override the typeclass; "
            "the whitelist gates the spawned type"
        )


def card_record(persona: Any) -> Any:
    """Return the record form of a carried card without trusting its type."""
    if isinstance(persona, NpcCard):
        return persona.to_record()
    return persona


def validate_characterization(
    characterization: StageNpcCharacterization | None,
    role: str,
    tier_key: str,
) -> None:
    """Re-validate one occupant's characterization through the shared helper.

    The compile boundary already validated the accepted blueprint, but a forged
    requirement or package could bypass it and write a negative or non-integer
    canonical age, a malformed policy, or an occupant WITHOUT the authored
    identity. Every occupant MUST carry a valid ``display_name``, ``title`` and
    complete compact ``persona`` card: re-running the same shared rules keeps
    the age-bounds rule, the authored-identity invariant and the card contract
    hard floors on every spawn path (design D6).
    """
    if characterization is None:
        raise SceneBuilderSpawnError(
            f"occupant {role!r} carries no characterization; authored identity "
            "is required on every spawn path"
        )
    entry: dict[str, Any] = {}
    if characterization.display_name is not None:
        entry["display_name"] = characterization.display_name
    if characterization.title is not None:
        entry["title"] = characterization.title
    if characterization.age is not None:
        entry["age"] = characterization.age
    if characterization.apparent_age is not None:
        entry["apparent_age"] = characterization.apparent_age
    if characterization.portrait_stable_key is not None:
        entry["portrait"] = {"stable_key": characterization.portrait_stable_key}
    if characterization.persona is not None:
        entry["persona"] = card_record(characterization.persona)
    for message in characterize_errors(
        entry,
        lifespan_upper_bound=race_lifespan_upper_bound(tier_key),
    ):
        raise SceneBuilderSpawnError(
            f"invalid characterization for occupant {role!r}: {message}"
        )


def apply_characterization(
    npc: NPC,
    characterization: StageNpcCharacterization,
    provenance: dict[str, Any],
) -> None:
    """Apply one occupant's characterization per-field (design D1).

    Each carried field applies independently: ``display_name`` sets the display
    name; the paired ages set the canonical ``age``/``apparent_age`` attributes;
    a portrait ``stable_key`` materializes the full named policy dict (design D2)
    and, when the ages are absent, the deterministic default age so subject-age
    eligibility always has canonical inputs (design D3). An occupant without a
    portrait policy never receives the default or a policy (design D4). The
    occupant's compact card is written through the deterministic persona
    initializer with the caller's provenance, inside the caller's atomic
    materialization; any initializer failure is raised as
    ``SceneBuilderSpawnError`` and rolls the whole spawn back.
    """
    if characterization.display_name is not None:
        npc.db.display_name = validate_npc_name(characterization.display_name)
    if characterization.title is not None:
        npc.npc_title = validate_npc_title(characterization.title)
    if characterization.age is not None and characterization.apparent_age is not None:
        npc.db.age = characterization.age
        npc.db.apparent_age = characterization.apparent_age
    if characterization.portrait_stable_key is not None:
        if npc.db.age is None:
            npc.db.age = PORTRAIT_DEFAULT_AGE
        if npc.db.apparent_age is None:
            npc.db.apparent_age = PORTRAIT_DEFAULT_AGE
        npc.db.portrait_policy = {
            "mode": "named",
            "stable_key": characterization.portrait_stable_key,
        }
    try:
        initialize_npc_persona(npc, card_record(characterization.persona), provenance)
    except (NpcCardError, NpcPersonaStorageError) as error:
        raise SceneBuilderSpawnError(
            f"occupant persona initialization failed: {error}"
        ) from error
    if characterization.combat_traits:
        from world.rules.traits import set_combat_traits

        set_combat_traits(npc, characterization.combat_traits)


def _install_scripted_dialogue(npc: NPC, dialogue_key: str) -> None:
    """Grant one conversable generated role its scripted-dialogue capability."""
    npc.components.add(ScriptedDialogue.create(npc, dialogue_key=dialogue_key))


def spawn_role_actor(
    room: Any,
    spawn_spec: RoleSpawn,
    provenance: dict[str, Any],
) -> NPC:
    """Spawn and initialize one actor for a validated role (design §5.3).

    The prototype parent is selected from the closed whitelist by the role's
    conversable flag; the trait block comes from the immutable tier registry; the
    characterization, persona card, dialogue capability and lineage auto-seed are
    applied through the shared helpers. The caller owns the surrounding
    transaction.
    """
    tier = NPC_TIER_REGISTRY.get(spawn_spec.tier)
    if tier is None:
        raise SceneBuilderSpawnError(f"unknown NPC tier {spawn_spec.tier!r}")
    characterization = spawn_spec.characterization
    validate_characterization(characterization, spawn_spec.role, spawn_spec.tier)
    config = trait_config_for_values(
        build_initial_traits(tier.race_key, tier=tier.static_tier_key)
    )
    prototype = {
        "prototype_parent": "scene_llm_npc" if spawn_spec.conversable else "scene_npc",
        "key": validate_npc_name(characterization.display_name),
        "location": room,
    }
    validate_occupant_parent(prototype)
    spawned = spawn(prototype)
    if not spawned:
        raise SceneBuilderSpawnError(
            "spawner.spawn() returned no object for a scene NPC"
        )
    npc = spawned[0]
    if not isinstance(npc, NPC):
        raise SceneBuilderSpawnError(
            f"spawned object {npc!r} is not an NPC; rejecting it"
        )
    npc.race = tier.race_key
    npc.db.npc_tier_key = spawn_spec.tier
    npc._apply_trait_config(config)
    npc.db.disposition = spawn_spec.disposition
    apply_characterization(npc, characterization, provenance)
    apply_lineage_auto_seed(npc)
    if spawn_spec.dialogue_key:
        _install_scripted_dialogue(npc, spawn_spec.dialogue_key)
    return npc


def spawn_monster(room: Any, archetype: str | None, tier_key: str) -> Monster:
    """Spawn one whitelisted scene monster from the monster-tier registry."""
    prototype = {
        "prototype_parent": "scene_monster",
        "key": f"{scene_name(archetype)}的魔物",
        "location": room,
    }
    validate_occupant_parent(prototype)
    spawned = spawn(prototype)
    if not spawned:
        raise SceneBuilderSpawnError(
            "spawner.spawn() returned no object for a scene monster"
        )
    monster = spawned[0]
    if not isinstance(monster, Monster):
        raise SceneBuilderSpawnError(
            f"spawned object {monster!r} is not a Monster; rejecting it"
        )
    monster.threat_tier = tier_key
    monster.apply_monster_tier("floor")
    return monster


def schedule_occupant_portraits(occupants: tuple[Any, ...] | list[Any]) -> None:
    """Schedule the portrait ensure for occupants carrying an explicit named policy.

    Runs inside the outer atomic materialization, so ``transaction.on_commit``
    fires only after the spawn transaction commits and an art failure can never
    roll back a materialized scene (design D9).
    """
    named = [
        occupant
        for occupant in occupants
        if getattr(occupant, "db", None) is not None
        and occupant.db.portrait_policy is not None
        and hasattr(occupant.db.portrait_policy, "get")
        and occupant.db.portrait_policy.get("mode") == "named"
    ]
    if not named:
        return
    from world.art.service import schedule_occupant_portrait

    for occupant in named:
        schedule_occupant_portrait(occupant)


__all__ = [
    "PORTRAIT_DEFAULT_AGE",
    "RoleSpawn",
    "SCENE_OCCUPANT_PROTOTYPE_WHITELIST",
    "SceneBuilderError",
    "SceneBuilderLocationError",
    "SceneBuilderNoRequirements",
    "SceneBuilderNotActive",
    "SceneBuilderRoleUnavailable",
    "SceneBuilderSpawnError",
    "apply_characterization",
    "card_record",
    "schedule_occupant_portraits",
    "scene_name",
    "spawn_monster",
    "spawn_role_actor",
    "validate_characterization",
    "validate_occupant_parent",
]
