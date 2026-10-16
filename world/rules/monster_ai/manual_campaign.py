"""Evennia-side manual execution boundary for the monster-AI manual evidence.

This module is the DB-facing half of ``monster-ai-manual-evidence``: it builds
the synthetic archetype profiles through the production loader, constructs real
synthetic entities, drives real combat-session rounds through the shared
round/resolver boundary with committed reload, and records the deciding
monsters' own decisions for the report layer in
:mod:`world.rules.monster_ai.manual_reports`. It runs only from the manual CLI
(``tools/monster_ai_manual_reports.py``) against an isolated scratch database;
nothing here is imported by the game runtime, discovered by default tests or
invoked by startup/CI/contract gates.

Every encounter uses fresh entities and clears the session-owned observation
and AI-tuning stores first, so a previous run cannot influence one; each
encounter seeds the process dice from its documented combat seed, and every
decision records the selector seed and the execution identity it actually used.
The player side of an encounter is a real production roster — the initiating
player plus the companion NPCs bound to it through ``join_party`` — so a
multi-opponent situation is engaged through the same collection production
uses.

An encounter is evidence only if its preconditions really held. Every
situation's declarations are serialized with the report; its decision boundary
is verified at the provider boundary against the decision that was produced
there; each committed round is re-read from fresh rows after the idmapper cache
is dropped; and a monster action the resolver refuses aborts the whole batch
instead of being recorded as a weaker accepted result.
"""

from __future__ import annotations

import random
import time
from contextlib import contextmanager
from dataclasses import dataclass, replace
from typing import Any, Iterator, Mapping, Sequence

from django.db import connection
from django.test.utils import CaptureQueriesContext
from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.idmapper.models import flush_cache
from django.conf import settings

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import Room

# Eagerly imported outside any synthetic scope (the shared helper precedent):
# these rulebooks validate shipped rows at import, so importing them inside a
# synthetic scope would validate them against synthetic catalogs.
import world.rules.cross_lineage_unlock  # noqa: F401
import world.rules.defeat_aftermath  # noqa: F401
from world.rules import monster_behaviour as behaviour
from world.rules.action import ActionResolver, _stored_trait_value
from world.rules.buffs import (
    BUFF_DEFINITIONS,
    apply_buff,
    entity_active_buffs,
    has_positional_marker,
)
from world.rules.combat import (
    COMBAT_YAML,
    Battlefield,
    BattlefieldActionContext,
    current_decision_scope,
    decision_scope,
)
from world.rules.combat_session import (
    BASIC_ATTACK_KEY,
    engage_group,
    preflight_draft_entries,
    read_session,
    reconstruct_battlefield,
    to_storage,
    submit_player_action,
)
from world.rules.combat_session import ai_tuning as ai_tuning_module
from world.rules.combat_session import observations as observations_module
from world.rules.combat_session import policies as policies_module
from world.rules.monster_ai import candidates as candidates_module
from world.rules.monster_ai import manual_reports as reports
from world.rules.monster_ai.models import stable_identity
from world.rules.monster_individual import construct_species_individual
from world.lore.races import RACE_REGISTRY
from world.rules.party import combat_companions, join_party
from world.rules.spell_conditions import is_strike_class
from world.skills.registry import TargetSpec
from world.tests.synthetic_data import (
    SYNTH_GLOWMIRE_ELEMENT,
    SYNTH_SKILLS,
    make_monster_species,
    make_monster_tier,
    make_monster_variant,
    synthetic_registries,
)

#: The one synthetic species/tier every campaign variant belongs to.
SPECIES_KEY = "t_campaign_species"
TIER_KEY = "t_campaign_tier"
#: The kit's invented element every synthetic damage effect resolves through.
_ELEMENT = SYNTH_GLOWMIRE_ELEMENT.key
#: The shipped seal buff the mandatory-targeting situation applies.
_SEAL_BUFF_KEY = "lamb_seal"


def _skill(key: str, label: str, *, effects: list[str], cost: dict[str, int] | None = None,
           target_spec: TargetSpec | None = None) -> Any:
    """Build one synthetic skill from the kit's elemental-spell template."""
    base = SYNTH_SKILLS["t_ember_burst"]
    return replace(
        base,
        key=key,
        label=label,
        description=label,
        target_spec=base.target_spec if target_spec is None else target_spec,
        cost={} if cost is None else dict(cost),
        effects=list(effects),
    )


#: The neutral zero-cost single-target magic driver the *player* submits to
#: drive a session round (the encounter measures the monster's decisions, not
#: the player's). It is deliberately NOT strike class -- ``is_strike_class``
#: means SINGLE with physical damage and no magic damage -- so the driving
#: player's own action never clears the positional marker a mandatory-targeting
#: encounter mounted on it: production clears a strike-class actor's own
#: displacement at resolution (attack design D4), which would silently erase
#: the scenario's constraint before the monster ever decided.
PLAYER_DRIVER_KEY = "t_campaign_driver"


def _campaign_skill_rows() -> tuple[Any, ...]:
    """Return the campaign's synthetic skill rows.

    The monster kit carries the reference envelope's own width -- sixteen
    active skills across single/area damage and healing/self-healing shapes --
    so the performance scenario measures the configured ``owned_skills``
    ceiling rather than a convenient handful.
    """
    rows = [
        _skill(
            PLAYER_DRIVER_KEY,
            "合成驅動",
            effects=[f"damage:{_ELEMENT}:magic"],
            cost={},
        )
    ]
    for index in range(10):
        school = "physical" if index % 2 else "magic"
        cost = {} if index % 3 == 0 else {"mp": 4 + index}
        rows.append(
            _skill(
                f"t_campaign_strike_{index}",
                f"合成攻擊{index}",
                effects=[f"damage:{_ELEMENT}:{school}"],
                cost=cost,
            )
        )
    for index in range(2):
        rows.append(
            _skill(
                f"t_campaign_area_{index}",
                f"合成範圍{index}",
                effects=[f"damage:{_ELEMENT}:magic"],
                cost={"mp": 10 + index},
                target_spec=TargetSpec.AREA,
            )
        )
    for index in range(2):
        rows.append(
            _skill(
                f"t_campaign_heal_{index}",
                f"合成治療{index}",
                effects=["heal:single"],
                cost={"mp": 8 + index},
            )
        )
    for index in range(2):
        rows.append(
            _skill(
                f"t_campaign_selfheal_{index}",
                f"合成自癒{index}",
                effects=["self_heal"],
                cost={},
                # An actor-bound skill declares its own target shape: SINGLE
                # would demand exactly one target the actor-bound producer
                # never submits, so the self-heal would be rejected during
                # enumeration instead of being the legal alternative it is.
                target_spec=TargetSpec.SELF,
            )
        )
    return tuple(rows)


_CAMPAIGN_SKILLS = _campaign_skill_rows()
#: The campaign rows by key: a boundary check classifies a plan's skill
#: through the same shipped vocabulary the producer used.
CAMPAIGN_SKILLS_BY_KEY = {row.key: row for row in _CAMPAIGN_SKILLS}
_MONSTER_SKILL_KEYS = tuple(
    row.key for row in _CAMPAIGN_SKILLS if row.key != PLAYER_DRIVER_KEY
)
#: The narrow kit an encounter's monsters actually carry: two single-target
#: strikes, one area shape, one heal and one self-heal, which is enough for
#: every situation's boundary without making one decision enumerate sixteen
#: families per target.
_ENCOUNTER_SKILL_KEYS = (
    "t_campaign_strike_0",
    "t_campaign_strike_1",
    "t_campaign_area_0",
    "t_campaign_heal_0",
    "t_campaign_selfheal_0",
)
#: The kit the allied decider of the support situation carries: a heal it can
#: spend on an injured ally, its own self-heal and one strike.
_SUPPORT_SKILL_KEYS = (
    "t_campaign_heal_0",
    "t_campaign_selfheal_0",
    "t_campaign_strike_0",
)
#: The kit's ally-directed heal, the support boundary's own legal answer to an
#: observed injured ally.
_HEAL_SKILL_KEY = "t_campaign_heal_0"
#: The monster offense every situation uses unless it declares its own: low
#: enough that the engaged party out-lasts the monster inside the round cap.
_BOUNDED_MONSTER_ATK = 8
#: The offense the finishing situation declares: high enough that a knockout of
#: its injured opponent is credibly projected instead of merely possible, which
#: is exactly the boundary that situation exists to exercise.
_FINISHING_MONSTER_ATK = 25


def _strike_class_keys() -> frozenset[str]:
    """Return the kit's strike-class single-target skills."""
    return frozenset(
        key for key, skill in CAMPAIGN_SKILLS_BY_KEY.items() if is_strike_class(skill)
    )


def _nonstrike_hostile_single_keys() -> tuple[str, ...]:
    """Return the kit's non-strike hostile single-target damage skills.

    These are exactly what the mandatory displacement rule asks about: a
    genuinely castable alternative attack that can still name a displaced
    hostile bearer, which is why the displaced target stays reachable at all.
    """
    keys: list[str] = []
    for key in _ENCOUNTER_SKILL_KEYS:
        skill = CAMPAIGN_SKILLS_BY_KEY[key]
        if is_strike_class(skill) or skill.target_spec is not TargetSpec.SINGLE:
            continue
        if any(
            isinstance(effect, str) and effect.startswith("damage:")
            for effect in skill.effects
        ):
            keys.append(key)
    return tuple(keys)


#: The legacy decider's synthetic variant (never declared utility).
LEGACY_VARIANT_KEY = "t_campaign_legacy"
#: The synthetic row registered under the production basic-attack key, so the
#: non-deciding party members' own default-attack policy resolves.
_BASIC_ATTACK_ROW = _skill(
    BASIC_ATTACK_KEY, "合成基本攻擊", effects=[f"damage:{_ELEMENT}:physical"], cost={}
)


def _positional_buff_key() -> str:
    """Return the shipped positional marker that outlasts the encounter longest.

    The mandatory-targeting constraint has to be live at every monster decision
    of the encounter, and nothing in the encounter may clear the bearer's own
    marker, so the mounted marker is the authored positional row with the
    longest duration (ties broken by key, so the choice is deterministic).
    """
    candidates = [
        (int(BUFF_DEFINITIONS[key].duration or 0), key)
        for key in sorted(BUFF_DEFINITIONS)
        if getattr(BUFF_DEFINITIONS[key], "marker", None) == "positional"
    ]
    if not candidates:
        raise ValueError("no positional-marker buff is authored")
    return max(candidates)[1]


def _timed_buff_key() -> str:
    """Return one shipped buff definition with a short finite duration.

    Applied to the long-lifecycle monster so a real mounted effect expires
    inside the encounter's own committed round count. Only an inert, non-marker
    row qualifies: a positional marker would change the decision's targeting
    and the seal would narrow it, so either would make the lifecycle scenario
    measure something else.
    """
    for key in sorted(BUFF_DEFINITIONS):
        definition = BUFF_DEFINITIONS[key]
        duration = getattr(definition, "duration", None)
        if not isinstance(duration, int) or isinstance(duration, bool):
            continue
        if 0 < duration <= 30 and key != _SEAL_BUFF_KEY:
            if getattr(definition, "marker", None) is None:
                return key
    raise ValueError("no short-duration buff is authored")


class CampaignFailure(RuntimeError):
    """One manual-evidence precondition failed: the batch aborts unpublished.

    A manual acceptance run is evidence only if an unmet precondition, an
    illegal selected action or a failed committed-reload check stops the run
    instead of being recorded as a weaker result.
    """


class RefusedMonsterAction(CampaignFailure):
    """A monster's selected action was refused by settlement.

    The batch must fail: an illegal selected action can never produce an
    accepted report (simulation design, bounded outcome).
    """


@dataclass(frozen=True, slots=True)
class SituationSpec:
    """One synthetic situation's battlefield configuration.

    Every field is a plain scalar/tuple so a situation declaration can never
    carry a live entity; the harness materializes them per encounter. Maximum
    and initial HP are separate fields, so an intentionally injured opponent is
    declared as an injured one rather than through a reduced maximum, and the
    serialized declaration the report carries says exactly which it is. The
    initiating player is always the session's own requester, so their hit
    points stay high enough to keep driving rounds while the bound companions
    carry the opponent pressure the situation exercises: production
    engagement collects exactly the initiating player and its bound
    companions, never other characters merely sharing the room.
    """

    name: str
    monsters: int
    monster_hp: int
    monster_mp: int
    monster_atk: int = _BOUNDED_MONSTER_ATK
    initiator_hp: int = 300
    companion_hp: tuple[int, ...] = ()
    companion_hp_max: tuple[int, ...] = ()
    monster_hp_max: int | None = None
    initiator_hp_max: int | None = None
    seal_opponents: int = 0
    displaced_opponents: int = 0
    monster_effect: str | None = None
    allied_support: bool = False

    @property
    def companion_max(self) -> tuple[int, ...]:
        """The companions' maximum HP, defaulting to their initial HP."""
        return self.companion_hp if not self.companion_hp_max else self.companion_hp_max

    def declaration(self, *, monster_skills: Sequence[str]) -> reports.ScenarioDeclaration:
        """Return this situation's materialized declaration for the report."""
        maximum = self.monster_hp if self.monster_hp_max is None else self.monster_hp_max
        return reports.ScenarioDeclaration(
            name=self.name,
            monsters=self.monsters,
            monsters_hp=(self.monster_hp,) * self.monsters,
            monsters_hp_max=(maximum,) * self.monsters,
            monster_mp=self.monster_mp,
            monster_atk=self.monster_atk,
            initiator_hp=self.initiator_hp,
            initiator_hp_max=(
                self.initiator_hp if self.initiator_hp_max is None else self.initiator_hp_max
            ),
            companion_hp=self.companion_hp,
            companion_hp_max=self.companion_max,
            seal_opponents=self.seal_opponents,
            displaced_opponents=self.displaced_opponents,
            seal_key=_SEAL_BUFF_KEY,
            positional_key=_positional_buff_key(),
            driver_skill_key=PLAYER_DRIVER_KEY,
            monster_skills=tuple(monster_skills),
            support_skills=_SUPPORT_SKILL_KEYS if self.allied_support else (),
            monster_effect=self.monster_effect,
            allied_support=self.allied_support,
        )


def _situations() -> tuple[SituationSpec, ...]:
    """Return the six distinct synthetic situations the allocation requires.

    Each declaration names the one boundary the approved simulation design
    assigns to it and materializes it with real production entities and
    shipped effects: the player-side roster is the initiating player plus
    companions bound through ``join_party``, the mandatory-targeting boundary
    mounts the shipped seal and the shipped positional marker instead of
    declaring them, and the long-lifecycle boundary mounts a shipped finite
    effect that expires inside the encounter's own committed rounds.
    """
    return (
        # Finishing choice: a credible knockout against an INJURED opponent --
        # a healthy maximum with a low initial value, so the finishing
        # projection is bounded by real remaining life instead of by a low
        # maximum that only pretends to be an injury. The monster carries the
        # one situation-specific offense the design needs a knockout to be
        # credibly projected from, and the party keeps a healthy second member
        # so losing the nearly-finished one never strands the encounter.
        SituationSpec("finishing_choice", monsters=1, monster_hp=90, monster_mp=80,
                      monster_atk=_FINISHING_MONSTER_ATK,
                      companion_hp=(12, 400), companion_hp_max=(90, 400)),
        # Area versus single target: three opponents with uneven remaining HP.
        SituationSpec("area_versus_single", monsters=1, monster_hp=160, monster_mp=80,
                      companion_hp=(150, 40)),
        # Resource exhaustion: useful choices competing for a finite MP pool --
        # the pool is smaller than the two cheapest useful skills together, so
        # the decision really has to give one of them up.
        SituationSpec("resource_exhaustion", monsters=1, monster_hp=110, monster_mp=9,
                      companion_hp=(300,)),
        # Mandatory targeting: two sealed opponents, the leading one also
        # displaced, plus the monster's genuinely legal non-strike hostile
        # alternative (the kit's magic-school single strike, which names the
        # required bearer while the physical strike-class single is refused).
        SituationSpec("mandatory_targeting", monsters=1, monster_hp=160, monster_mp=60,
                      companion_hp=(250, 200), seal_opponents=2,
                      displaced_opponents=1),
        # Tactical support and focus: two allied deciders, one able to heal.
        SituationSpec("support_and_focus", monsters=2, monster_hp=45, monster_mp=60,
                      companion_hp=(300,), allied_support=True),
        # Long encounter and lifecycle: repeated rounds against a durable
        # opponent pair with a real mounted effect expiring inside the
        # encounter's own committed round count.
        SituationSpec("long_lifecycle", monsters=1, monster_hp=150, monster_mp=200,
                      initiator_hp=400, companion_hp=(400,),
                      monster_effect=_timed_buff_key()),
    )


def _authored_archetypes() -> tuple[str, ...]:
    """Return the six production behaviour archetype keys, sorted.

    The campaign's six archetypes are the authored utility profiles, read from
    the production rulebook rather than duplicated here.
    """
    archetypes = tuple(sorted(behaviour.MONSTER_BEHAVIOUR_YAML["archetypes"]))
    if len(archetypes) != 6:
        raise ValueError(
            f"the manual campaign expects six authored archetypes, found {len(archetypes)}"
        )
    return archetypes


def _variant_key(archetype: str, intelligence: int) -> str:
    """Return one synthetic variant's key for an archetype/intelligence pair."""
    return f"t_campaign_{archetype}_{intelligence}"


def _decision_label(trace: Any) -> str:
    """Return one decision's readable identity for a failure message."""
    session_id, round_index, actor_id, slot_index, context_mode = trace.scope
    return (
        f"decision {session_id!r} round {round_index} slot {slot_index} "
        f"actor {actor_id!r} ({context_mode})"
    )


@dataclass(slots=True)
class _Encounter:
    """One encounter's live participants, kept current across committed rounds.

    ``bearer`` is the mandatory-targeting situation's sealed and displaced
    opponent (the initiating player, the first opponent engagement collects),
    ``injured`` the finishing situation's deliberately injured opponent and
    ``monsters`` the allied deciders whose pressure the support boundary
    observes. Every one is a live entity, so no boundary check can ever be
    satisfied by a declaration alone. ``reload`` re-acquires every participant
    from its own row, so the objects the round engine writes through, the
    objects the decision-boundary checks read and the objects the
    committed-round check compares are always the same, freshly re-acquired
    instances -- never a cache populated by an earlier round.
    """

    situation: SituationSpec
    session_id: str
    initiator: Any
    companions: tuple[Any, ...]
    monsters: tuple[Any, ...]
    injured_index: int | None = None

    @property
    def bearer(self) -> Any:
        """The mandatory-targeting situation's sealed, displaced opponent."""
        return self.initiator

    @property
    def injured(self) -> Any | None:
        """The finishing situation's deliberately injured opponent."""
        if self.injured_index is None:
            return None
        return self.companions[self.injured_index]

    @property
    def participants(self) -> tuple[Any, ...]:
        """Every participant the encounter's rounds write to."""
        return (self.initiator, *self.companions, *self.monsters)

    def reload(self) -> None:
        """Re-acquire every participant from its own row, dropping caches."""
        companions = len(self.companions)
        fresh = CampaignHarness.reload_participants(*self.participants)
        self.initiator = fresh[0]
        self.companions = tuple(fresh[1 : 1 + companions])
        self.monsters = tuple(fresh[1 + companions :])


class CampaignHarness:
    """One manual campaign run's complete DB-facing execution boundary."""

    def __init__(
        self,
        *,
        situations: Sequence[str] | None = None,
        seed_indices: Sequence[int] = reports.CAMPAIGN_SEED_INDICES,
        intelligences: Sequence[int] = reports.INTELLIGENCE_VALUES,
    ) -> None:
        self.archetypes = _authored_archetypes()
        declared = _situations()
        if situations is not None:
            wanted = tuple(situations)
            unknown = [name for name in wanted if name not in {spec.name for spec in declared}]
            if unknown:
                raise ValueError(f"unknown situation(s): {', '.join(unknown)}")
            declared = tuple(spec for spec in declared if spec.name in wanted)
        self.situations = declared
        self.seed_indices = tuple(seed_indices)
        self.intelligences = tuple(intelligences)
        self._warmups = reports.PERFORMANCE_WARMUPS
        self._measurements = reports.PERFORMANCE_MEASUREMENTS
        self._scope = None
        self._restore: list[tuple[Any, str, Any]] = []
        self.tuning: Any = None
        self.skills: dict[str, Any] = {}
        self.species: dict[str, Any] = {}
        self.variants: dict[str, Any] = {}
        self.room: Any = None

    # -- lifecycle ---------------------------------------------------------
    def __enter__(self) -> "CampaignHarness":
        self._enter_scope()
        self._install_tuning()
        # A scratch database has no Evennia Limbo yet, so the arena room is
        # created without a home and then published as DEFAULT_HOME: every
        # subsequent entity resolves its home to this room.
        self.room = create_object(Room, key="manual campaign arena", nohome=True)
        self._restore.append((settings, "DEFAULT_HOME", settings.DEFAULT_HOME))
        settings.DEFAULT_HOME = f"#{self.room.pk}"
        return self

    def __exit__(self, *exc: Any) -> None:
        self._restore_tuning()
        if self._scope is not None:
            self._scope.__exit__(None, None, None)
            self._scope = None

    def _enter_scope(self) -> None:
        """Enter the synthetic catalog scope and build the campaign rows."""
        # The production basic-attack row is registered beside the campaign kit
        # so every non-deciding party member's own default-attack policy
        # resolves inside the synthetic catalog.
        self.skills = {
            row.key: row for row in (*_CAMPAIGN_SKILLS, _BASIC_ATTACK_ROW)
        }
        first_variant = _variant_key(self.archetypes[0], reports.INTELLIGENCE_VALUES[0])
        self.species = {
            SPECIES_KEY: make_monster_species(SPECIES_KEY, default_variant_key=first_variant)
        }
        variant_rows: dict[str, Any] = {}
        for archetype in self.archetypes:
            for intelligence in reports.INTELLIGENCE_VALUES:
                key = _variant_key(archetype, intelligence)
                variant_rows[key] = replace(
                    make_monster_variant(
                        key,
                        species_key=SPECIES_KEY,
                        threat_tier=TIER_KEY,
                        behaviour_profile_key=archetype,
                    ),
                    active_skill_keys=_MONSTER_SKILL_KEYS,
                    passive_skill_keys=(),
                )
        # The performance scenario's legacy decider: the same generated variant
        # shape, but never declared utility, so it resolves the archetype's
        # authored legacy mode and produces the permanent legacy action.
        variant_rows[LEGACY_VARIANT_KEY] = replace(
            make_monster_variant(
                LEGACY_VARIANT_KEY,
                species_key=SPECIES_KEY,
                threat_tier=TIER_KEY,
                behaviour_profile_key=self.archetypes[0],
            ),
            active_skill_keys=_MONSTER_SKILL_KEYS,
            passive_skill_keys=(),
        )
        self.variants = variant_rows
        extra = {
            "skills": dict(self.skills),
            "monster_tiers": {TIER_KEY: make_monster_tier(TIER_KEY)},
            "monster_species": self.species,
            "monster_variants": variant_rows,
        }
        self._scope = synthetic_registries(
            "monster_tiers", "monster_species", "monster_variants", "races",
            "skills", "elements", extra=extra,
        )
        self._scope.__enter__()

    def _install_tuning(self) -> None:
        """Build the campaign rulebook through the production loader and install it."""
        intelligence = {
            _variant_key(archetype, value): value
            for archetype in self.archetypes
            for value in reports.INTELLIGENCE_VALUES
        }
        modes = {key: "utility" for key in intelligence}
        authored = behaviour.MONSTER_BEHAVIOUR_YAML["archetypes"]
        book = {
            "tier_default_archetype": {TIER_KEY: self.archetypes[0]},
            "archetypes": {key: dict(authored[key]) for key in self.archetypes},
            "variant_intelligence": intelligence,
            "variant_decision_mode": modes,
            "candidate_budget": reports.PERFORMANCE_CANDIDATE_BUDGET,
        }
        profiles = behaviour._load_behaviour_profiles(book, tiers={TIER_KEY})
        tuning = behaviour._load_ai_tuning(
            book, profiles=profiles, species=self.species, variants=self.variants
        )
        self.tuning = tuning
        for name, value in (
            ("MONSTER_BEHAVIOUR_YAML", book),
            ("BEHAVIOUR_PROFILES", profiles),
            ("MONSTER_AI_TUNING", tuning),
        ):
            self._restore.append((behaviour, name, getattr(behaviour, name)))
            setattr(behaviour, name, value)

    def _restore_tuning(self) -> None:
        for module, name, value in reversed(self._restore):
            setattr(module, name, value)
        self._restore = []

    # -- entity construction ----------------------------------------------
    def _player(self, key: str, hp: int, hp_max: int | None = None) -> Any:
        """Create the initiating player of one encounter in the arena.

        The driver skill is the kit's magic-school single: the player drives
        rounds through it without ever clearing a displacement marker mounted
        on its own body (see :data:`PLAYER_DRIVER_KEY`).
        """
        player = create_object(PlayerCharacter, key=key)
        player.race = next(iter(RACE_REGISTRY))
        player.apply_race_baseline()
        player.db.skills = {"active": [PLAYER_DRIVER_KEY], "passive": []}
        player.traits.hp.base = hp if hp_max is None else hp_max
        player.traits.hp.current = hp
        player.traits.atk_phys.base = 25
        player.traits.atk_phys.current = 25
        player.traits.defense.base = 15
        player.traits.defense.current = 15
        player.location = self.room
        return player

    def _companion(self, key: str, hp: int, hp_max: int | None = None) -> Any:
        """Create one real binding-ready companion NPC of the player's side.

        Production engagement collects exactly the initiating player's bound,
        co-located, living companions as the rest of the player-side roster
        (``combat_companions``), so a multi-opponent situation is materialized
        by binding real companions rather than by inventing extra stand-in
        players. A companion owns the production ``basic_attack`` key, so its
        own default-attack policy resolves inside the synthetic catalog.
        """
        companion = create_object(NPC, key=key)
        companion.race = next(iter(RACE_REGISTRY))
        companion.apply_race_baseline()
        companion.db.skills = {"active": [BASIC_ATTACK_KEY], "passive": []}
        companion.traits.hp.base = hp if hp_max is None else hp_max
        companion.traits.hp.current = hp
        companion.traits.atk_phys.base = 25
        companion.traits.atk_phys.current = 25
        companion.traits.defense.base = 15
        companion.traits.defense.current = 15
        companion.location = self.room
        return companion

    def _monster(
        self,
        key: str,
        variant_key: str,
        *,
        hp: int,
        mp: int,
        hp_max: int | None = None,
        atk: int = _BOUNDED_MONSTER_ATK,
        skills: Sequence[str] = _ENCOUNTER_SKILL_KEYS,
    ) -> Any:
        monster = construct_species_individual(SPECIES_KEY, variant_key, key=key)
        monster.location = self.room
        monster.traits.hp.base = hp if hp_max is None else hp_max
        monster.traits.hp.current = hp
        monster.traits.mp.base = max(mp, 0)
        monster.traits.mp.current = max(mp, 0)
        # The situation's declared offense: bounded for every ordinary
        # situation so the engaged party out-lasts the monster inside the round
        # cap, and lethal where the situation exists to project a knockout.
        monster.traits.atk_phys.base = atk
        monster.traits.atk_phys.current = atk
        monster.db.skills = {"active": list(skills), "passive": []}
        return monster

    # -- encounter execution ----------------------------------------------
    def run_archetype_campaign(self, archetype: str) -> tuple[reports.EncounterOutcome, ...]:
        """Run the named archetype's 24 encounters and return their outcomes.

        The archetype is one of the six authored profiles; a single invocation
        runs exactly that archetype's allocation and nothing else.
        """
        if archetype not in self.archetypes:
            raise ValueError(f"unknown archetype: {archetype!r}")
        outcomes: list[reports.EncounterOutcome] = []
        for situation in self.situations:
            for seed_index in self.seed_indices:
                for intelligence in self.intelligences:
                    outcomes.append(
                        self._run_encounter(
                            situation, archetype, seed_index, intelligence
                        )
                    )
        return tuple(outcomes)

    def run_single_encounter(
        self,
        situation: str,
        archetype: str,
        *,
        seed_index: int = 0,
        intelligence: int | None = None,
    ) -> reports.EncounterOutcome:
        """Run exactly one named encounter (the focused smoke path)."""
        spec = next((item for item in self.situations if item.name == situation), None)
        if spec is None:
            raise ValueError(f"unknown situation: {situation!r}")
        if archetype not in self.archetypes:
            raise ValueError(f"unknown archetype: {archetype!r}")
        value = self.intelligences[0] if intelligence is None else intelligence
        return self._run_encounter(spec, archetype, seed_index, value)

    # Public entity builders: the focused smoke tests build the same real
    # synthetic entities the campaign uses instead of duplicating fixtures.
    def build_player(self, key: str, hp: int) -> Any:
        """Create one real synthetic player combatant in the arena."""
        return self._player(key, hp)

    def build_monster(
        self,
        key: str,
        *,
        archetype: str | None = None,
        intelligence: int | None = None,
        hp: int = 60,
        mp: int = 60,
    ) -> Any:
        """Create one real synthetic utility monster in the arena."""
        archetype_key = self.archetypes[0] if archetype is None else archetype
        value = self.intelligences[0] if intelligence is None else intelligence
        return self._monster(
            key, _variant_key(archetype_key, value), hp=hp, mp=mp
        )

    def _run_encounter(
        self,
        situation: SituationSpec,
        archetype: str,
        seed_index: int,
        intelligence: int,
    ) -> reports.EncounterOutcome:
        observations_module.clear_session_memory()
        ai_tuning_module.clear_session_ai_tuning()
        scenario_seed = reports.scenario_seed(situation.name, archetype, seed_index)
        # The paired variants share one documented combat seed, derived from
        # the scenario's own documented seed: only the synthetic variant's
        # intelligence differs between the two paired encounters.
        combat_seed = reports.stable_seed("combat", scenario_seed)
        random.seed(combat_seed)
        variant_key = _variant_key(archetype, intelligence)
        session_id = reports.manual_session_id(situation.name, archetype, seed_index)

        initiator = self._player(
            "campaign-player-0", situation.initiator_hp, situation.initiator_hp_max
        )
        companions = [
            self._companion(
                f"campaign-companion-{index}", hp, situation.companion_max[index]
            )
            for index, hp in enumerate(situation.companion_hp)
        ]
        for companion in companions:
            join_party(companion, initiator)
        monsters = []
        for index in range(situation.monsters):
            monster = self._monster(
                f"campaign-monster-{index}",
                variant_key,
                hp=situation.monster_hp,
                mp=situation.monster_mp,
                hp_max=situation.monster_hp_max,
                atk=situation.monster_atk,
            )
            if situation.allied_support and index == 1:
                monster.db.skills = {
                    "active": list(_SUPPORT_SKILL_KEYS),
                    "passive": [],
                }
            monsters.append(monster)
        if situation.monster_effect is not None:
            apply_buff(monsters[0], situation.monster_effect)
        # The player-side roster production engagement will collect: the
        # initiating player first, then its bound companions in party order.
        opponents = (initiator, *companions)
        for opponent in opponents[: situation.seal_opponents]:
            apply_buff(opponent, _SEAL_BUFF_KEY)
        for opponent in opponents[: situation.displaced_opponents]:
            apply_buff(opponent, _positional_buff_key())

        self._verify_preconditions(situation, initiator, companions, monsters)
        engagement = engage_group(initiator, monsters)
        origin_session_id = engagement["record"].session_id
        # The manual selection seam: before the first round the durable session
        # record carries the DOCUMENTED scenario identity, so the round engine,
        # the session-owned observation memory and every decision's scope agree
        # on it, and two paired variants decide under ONE shared session
        # identity. The identity the scratch database's own engagement
        # allocated is reported beside it.
        initiator.db.active_combat = to_storage(
            replace(engagement["record"], session_id=session_id)
        )
        roles = self._roles(initiator, companions, monsters)
        injured_index = next(
            (
                index
                for index in range(len(companions))
                if situation.companion_hp[index] < situation.companion_max[index]
            ),
            None,
        )
        if situation.name == "finishing_choice" and injured_index is None:
            raise CampaignFailure(
                "finishing_choice: the situation declares no injured opponent "
                "(maximum and initial HP are identical for every companion)"
            )
        encounter = _Encounter(
            situation=situation,
            session_id=session_id,
            initiator=initiator,
            companions=tuple(companions),
            monsters=tuple(monsters),
            injured_index=injured_index,
        )
        facts: list[dict[str, Any]] = []
        samples, rounds, outcome = self._play(
            encounter, roles=roles, facts=facts
        )
        self._verify_boundary_facts(situation, facts)
        self._verify_terminal_state(encounter, outcome)
        if situation.monster_effect is not None:
            self._verify_effect_expired(
                encounter.monsters[0], situation.monster_effect, rounds
            )

        return reports.EncounterOutcome(
            archetype=archetype,
            situation=situation.name,
            seed_index=seed_index,
            intelligence=intelligence,
            outcome=outcome,
            rounds=rounds,
            decisions=tuple(samples),
            scenario_seed=scenario_seed,
            combat_seed=combat_seed,
            session_id=session_id,
            origin_session_id=origin_session_id,
            scenario=situation.declaration(monster_skills=_ENCOUNTER_SKILL_KEYS),
            roles=roles,
        )

    @staticmethod
    def _verify_preconditions(
        situation: SituationSpec,
        initiator: Any,
        companions: Sequence[Any],
        monsters: Sequence[Any],
    ) -> None:
        """Fail the encounter unless its situation's roster really materialized.

        The scenario boundaries are properties of the engaged roster, not of a
        declaration: production engagement must have collected exactly the
        bound companions, the mounted seal and displacement markers must be
        live on the opponents the situation names, a companion the declaration
        calls injured must really start injured (rather than merely having a low
        maximum) and the finite effect the lifecycle situation mounts must have
        really mounted. A mismatch is a simulator bug that fails the batch
        rather than a silently weaker scenario.
        """
        engaged = tuple(int(entity.pk) for entity in combat_companions(initiator))
        expected = tuple(int(entity.pk) for entity in companions)
        if engaged != expected:
            raise CampaignFailure(
                f"{situation.name}: engaged companions {engaged} do not match the "
                f"bound roster {expected}"
            )
        for position, opponent in enumerate((initiator, *companions)):
            if position < situation.seal_opponents:
                if _SEAL_BUFF_KEY not in entity_active_buffs(opponent):
                    raise CampaignFailure(
                        f"{situation.name}: opponent {opponent.key} carries no live seal"
                    )
            if position < situation.displaced_opponents:
                if not has_positional_marker(opponent):
                    raise CampaignFailure(
                        f"{situation.name}: opponent {opponent.key} carries no live "
                        "positional marker"
                    )
        for index, (initial, maximum) in enumerate(
            zip(situation.companion_hp, situation.companion_max)
        ):
            companion = companions[index]
            if initial < maximum and companion.traits.hp.current >= companion.traits.hp.base:
                raise CampaignFailure(
                    f"{situation.name}: companion {companion.key} is declared injured "
                    f"({initial}/{maximum} HP) but materialized fully healed"
                )
        if situation.monster_effect is not None:
            if situation.monster_effect not in entity_active_buffs(monsters[0]):
                raise CampaignFailure(
                    f"{situation.name}: the finite effect "
                    f"{situation.monster_effect!r} never mounted on the monster"
                )

    @staticmethod
    def _verify_effect_expired(monster: Any, effect: str, rounds: int) -> None:
        """Fail the encounter unless its finite mounted effect really expired.

        An effect whose authored duration has elapsed expires; equality is a
        legal expiry (a shorter legal encounter must not be rejected), so only
        an encounter that ran strictly longer is required, and that longer
        encounter must then really show the effect gone.
        """
        seconds = int(COMBAT_YAML["round"]["seconds"]) * rounds
        duration = BUFF_DEFINITIONS[effect].duration or 0
        if seconds < duration:
            raise CampaignFailure(
                f"the encounter ran {seconds}s, too short to expire the mounted "
                f"effect {effect!r} ({duration}s)"
            )
        if seconds > duration and effect in entity_active_buffs(monster):
            raise CampaignFailure(
                f"the mounted effect {effect!r} outlived the encounter's {rounds} rounds"
            )

    # -- committed reload --------------------------------------------------
    @staticmethod
    def reload_participants(*entities: Any) -> tuple[Any, ...]:
        """Return fresh rows for entities after dropping each one's own cache.

        The committed-reload boundary: Evennia's idmapper answers a plain
        ``ObjectDB`` query from its instance cache, so every durable read first
        evicts that participant and only then re-acquires it by primary key --
        the returned row is a new instance whose stored attributes can only
        come from the database, never from the object the round wrote through.
        Only the named participants are evicted: the arena room stays cached,
        so the session's own identity checks (``actor.location is room``) keep
        holding for the instance the round driver holds.
        """
        for entity in entities:
            entity.flush_cached_instance(entity)
        return tuple(
            ObjectDB.objects.get(pk=int(entity.pk)) for entity in entities
        )

    @staticmethod
    def _roles(
        initiator: Any, companions: Sequence[Any], monsters: Sequence[Any]
    ) -> dict[str, str]:
        """Return the encounter-local role of every participant.

        Roles are the stable, encounter-local identities the report records
        beside each decision's target identities, so target concentration is
        readable as focus on an opponent role instead of as a scratch
        database's per-encounter dbref.
        """
        roles = {stable_identity(initiator): "player"}
        for index, companion in enumerate(companions):
            roles[stable_identity(companion)] = f"companion-{index}"
        for index, monster in enumerate(monsters):
            roles[stable_identity(monster)] = f"monster-{index}"
        return roles

    def _verify_committed_round(
        self,
        encounter: _Encounter,
        rounds: int,
        *,
        terminal: bool,
    ) -> None:
        """Verify one round's effects as durable, committed state.

        What the round's own live objects hold is captured first -- those are
        the objects the engine just wrote through -- and only then is each
        participant re-acquired from a fresh row. The session's committed round
        count, each participant's stored gauges and each participant's live
        effect set must match that in-process view, so a write that never
        reached the database, or a round that cleared the session without a
        terminal outcome, fails rather than being reported as committed state.
        """
        written = {
            entity.key: _durable_surface(entity) for entity in encounter.participants
        }
        encounter.reload()
        fresh = {entity.key: entity for entity in encounter.participants}
        for key, surface in written.items():
            if _durable_surface(fresh[key]) != surface:
                raise CampaignFailure(
                    f"{encounter.situation.name}: the committed state of {key} reads "
                    f"{_durable_surface(fresh[key])} from a fresh row, but the "
                    f"round wrote {surface}"
                )
        record = read_session(fresh[encounter.initiator.key])
        if record is None:
            if not terminal:
                raise CampaignFailure(
                    f"{encounter.situation.name}: the committed round cleared the "
                    "durable session without a terminal outcome"
                )
            return
        if terminal:
            raise CampaignFailure(
                f"{encounter.situation.name}: a terminal round left the durable "
                f"session {record.session_id!r} active"
            )
        if record.rounds_elapsed != rounds:
            raise CampaignFailure(
                f"{encounter.situation.name}: the durable session records "
                f"{record.rounds_elapsed} committed rounds, not {rounds}"
            )

    def _verify_terminal_state(
        self,
        encounter: _Encounter,
        outcome: str,
    ) -> None:
        """Verify the encounter's committed terminal state from fresh rows.

        A terminal settlement clears the durable session record and sweeps the
        encounter's displacement markers and seals from every participant, and
        the session's observation memory is discarded with the session; a
        capped encounter keeps its active session and is reported unresolved.
        """
        encounter.reload()
        participants = encounter.participants
        initiator = encounter.initiator
        record = read_session(initiator)
        if outcome == reports.OUTCOME_CAPPED:
            if record is None:
                raise CampaignFailure(
                    f"{encounter.situation.name}: an unresolved encounter lost its "
                    "session"
                )
            return
        if record is not None:
            raise CampaignFailure(
                f"{encounter.situation.name}: {outcome} settlement left the durable "
                f"session {record.session_id!r} active"
            )
        for entity in participants:
            if has_positional_marker(entity):
                raise CampaignFailure(
                    f"{encounter.situation.name}: {outcome} settlement left a "
                    f"displacement marker on {entity.key}"
                )
            if _SEAL_BUFF_KEY in entity_active_buffs(entity):
                raise CampaignFailure(
                    f"{encounter.situation.name}: {outcome} settlement left a seal "
                    f"on {entity.key}"
                )
        # The session's observation memory is discarded by a commit-only
        # request (monster-ai-observation-lifecycle), so it is asserted exactly
        # where the caller's transaction really committed -- the manual tool's
        # own mode. Inside a caller's still-open transaction the discard is
        # legitimately still pending, and asserting it there would fail for the
        # caller rather than for the harness.
        if connection.in_atomic_block:
            return
        battlefield = Battlefield(
            {
                "party": frozenset(
                    entity.key for entity in (initiator, *encounter.companions)
                ),
                "foes": frozenset(monster.key for monster in encounter.monsters),
            },
            {entity.key: entity for entity in participants},
        )
        if observations_module.project_observations(
            encounter.session_id, battlefield
        ):
            raise CampaignFailure(
                f"{encounter.situation.name}: {outcome} settlement left the session's "
                "observation memory behind"
            )

    def _inspect_boundary(
        self,
        encounter: _Encounter,
        entity: Any,
        battlefield: Any,
        trace: Any,
        role: str,
        facts: list[dict[str, Any]],
    ) -> None:
        """Verify one situation's decision-boundary conditions, and record them.

        This runs at the provider boundary, on the decision the policy actually
        produced: the situation's constraint must be live *there* -- not merely
        before initiative -- and the candidate restrictions are read from the
        decision's own trace. A violated precondition fails the batch; the
        recorded facts are what the encounter-level check requires to have
        occurred at least once. Nothing here imposes a choice-frequency
        threshold: the checks establish opportunity and execution conditions.
        """
        name = encounter.situation.name
        fact: dict[str, Any] = {
            "situation": name,
            "role": role,
            "round": trace.scope[1],
            "accepted": len(trace.plans),
        }
        if name == "mandatory_targeting":
            bearer = encounter.bearer
            bearer_id = stable_identity(bearer)
            if _SEAL_BUFF_KEY not in entity_active_buffs(bearer):
                raise CampaignFailure(
                    f"mandatory_targeting: the seal was already gone from "
                    f"{bearer.key} at {_decision_label(trace)}"
                )
            if not has_positional_marker(bearer):
                raise CampaignFailure(
                    f"mandatory_targeting: the displacement was already gone from "
                    f"{bearer.key} at {_decision_label(trace)}"
                )
            strike_keys = _strike_class_keys()
            struck = [
                plan.skill_key
                for plan in trace.plans
                if plan.skill_key in strike_keys and bearer_id in plan.target_ids
            ]
            if struck:
                raise CampaignFailure(
                    f"mandatory_targeting: {_decision_label(trace)} kept the "
                    f"strike-class plan(s) {struck} on the displaced bearer"
                )
            alternatives = _nonstrike_hostile_single_keys()
            fact["nonstrike_alternative"] = any(
                plan.skill_key in alternatives and bearer_id in plan.target_ids
                for plan in trace.plans
            )
        elif name == "finishing_choice" and encounter.injured is not None:
            injured = encounter.injured
            injured_id = stable_identity(injured)
            fact["injured_connected"] = any(
                injured_id in plan.target_ids for plan in trace.plans
            )
            fact["finishing_projection"] = any(
                plan.finishing > 0 and injured_id in plan.target_ids
                for plan in trace.plans
            )
        elif name == "resource_exhaustion":
            remaining = entity.traits.mp.current
            # The plan's own ``cost`` feature is normalized; the authored MP
            # price of every skill the decision accepted is the real price, and
            # it is what a finite pool competes over.
            costs = sorted(
                {
                    skill.cost.get("mp", 0)
                    for plan in trace.plans
                    for skill in (CAMPAIGN_SKILLS_BY_KEY.get(plan.skill_key),)
                    if skill is not None and skill.cost.get("mp", 0) > 0
                }
            )
            fact["positive_cost_plans"] = len(costs)
            fact["competing_cost"] = costs[0] + costs[1] if len(costs) >= 2 else 0
            fact["remaining_mp"] = remaining
            fact["affordable_competition"] = (
                len(costs) >= 2 and fact["competing_cost"] > remaining
            )
        elif name == "support_and_focus" and role == "monster-1":
            injured_allies = [
                monster
                for monster in encounter.monsters
                if monster is not entity
                and monster.traits.hp.current < monster.traits.hp.base
            ]
            fact["injured_ally"] = bool(injured_allies)
            if injured_allies:
                fact["heal_plan"] = any(
                    plan.skill_key == _HEAL_SKILL_KEY for plan in trace.plans
                )
                if not fact["heal_plan"]:
                    raise CampaignFailure(
                        f"support_and_focus: the support decider saw an injured ally at "
                        f"{_decision_label(trace)} but had no legal heal"
                    )
        elif name == "long_lifecycle":
            observations = observations_module.project_observations(
                encounter.session_id, battlefield
            )
            current = trace.scope[1]
            ages = [current - record.round_index for record in observations]
            fact["memory_records"] = len(observations)
            fact["memory_oldest_age"] = max(ages, default=0)
            # The projection offers the committed ring PLUS this transaction's
            # own journalled boundaries, until the commit fold evicts. So the
            # live read is bounded by the ring's record cap plus at most one
            # boundary per current participant, and its oldest visible round is
            # at most the ring's round-retention span behind -- the exact bound
            # the documented ring promises, with the current round's overlay
            # accounted for instead of asserted away.
            limit = observations_module.MAX_RETAINED_RECORDS + len(battlefield.roster)
            if len(observations) > limit:
                raise CampaignFailure(
                    f"long_lifecycle: {_decision_label(trace)} read "
                    f"{len(observations)} observations, over the retained bound of "
                    f"{limit}"
                )
            if any(
                age < 0 or age > observations_module.MAX_RETAINED_ROUNDS
                for age in ages
            ):
                raise CampaignFailure(
                    f"long_lifecycle: {_decision_label(trace)} read observations "
                    f"outside the {observations_module.MAX_RETAINED_ROUNDS}-round "
                    f"retention window (ages {sorted(ages)})"
                )
        elif name == "area_versus_single":
            area_keys = {
                key
                for key, skill in CAMPAIGN_SKILLS_BY_KEY.items()
                if skill.target_spec is TargetSpec.AREA
            }
            fact["area_plans"] = sum(
                1 for plan in trace.plans if plan.skill_key in area_keys
            )
            fact["single_plans"] = sum(
                1
                for plan in trace.plans
                if plan.skill_key in _ENCOUNTER_SKILL_KEYS
                and plan.skill_key not in area_keys
                and plan.target_ids
            )
        facts.append(fact)

    @staticmethod
    def _verify_boundary_facts(
        situation: SituationSpec, facts: Sequence[Mapping[str, Any]]
    ) -> None:
        """Require that the situation's boundary opportunity really occurred.

        Opportunity, never choice frequency: each named situation must have
        presented the decision boundary the allocation claims for it at least
        once during the encounter.
        """

        def occurred(key: str) -> bool:
            return any(fact.get(key) for fact in facts)

        if not facts:
            raise CampaignFailure(
                f"{situation.name}: the encounter recorded no decision boundary"
            )
        if situation.name == "mandatory_targeting" and not occurred("nonstrike_alternative"):
            raise CampaignFailure(
                "mandatory_targeting: no decision offered the legal non-strike "
                "hostile alternative against the displaced bearer"
            )
        if situation.name == "finishing_choice":
            if not occurred("injured_connected"):
                raise CampaignFailure(
                    "finishing_choice: no decision ever considered the injured opponent"
                )
            if not occurred("finishing_projection"):
                raise CampaignFailure(
                    "finishing_choice: no decision projected a knockout of the "
                    "injured opponent"
                )
        if situation.name == "resource_exhaustion" and not occurred("affordable_competition"):
            raise CampaignFailure(
                "resource_exhaustion: no decision faced two useful choices it could "
                "not both afford"
            )
        if situation.name == "support_and_focus" and not occurred("injured_ally"):
            raise CampaignFailure(
                "support_and_focus: no decision observed allied pressure to answer"
            )
        if situation.name == "long_lifecycle" and not occurred("memory_records"):
            raise CampaignFailure(
                "long_lifecycle: the encounter never observed session memory"
            )
        if situation.name == "area_versus_single":
            if not occurred("area_plans"):
                raise CampaignFailure(
                    "area_versus_single: no decision had a legal area plan"
                )
            if not any(fact.get("single_plans", 0) >= 2 for fact in facts):
                raise CampaignFailure(
                    "area_versus_single: no decision had two or more legal "
                    "single-target plans"
                )

    def _confirm_remaining_allies(
        self, initiator: Any, target: Any, result: dict[str, Any]
    ) -> dict[str, Any]:
        """Confirm one basic attack per remaining required ally of the draft.

        The player side is a complete party draft: the initiator's own
        submission only admits its selection, so every other required allied
        actor must select its own command before the round resolves. This
        harness supplies exactly the ``basic_attack`` each companion already
        owns, one actor at a time, and returns the confirmation that completed
        the draft -- the round's own result. A draft that cannot complete is a
        simulator failure reported loudly, never a silently capped encounter.
        """
        while result.get("outcome") == "draft":
            record = read_session(initiator)
            if record is None:
                raise CampaignFailure(
                    f"the session of {initiator.key} ended with an incomplete "
                    f"party draft: {result!r}"
                )
            battlefield = reconstruct_battlefield(initiator, record)
            progress = preflight_draft_entries(initiator, record, battlefield)
            entities = {
                int(entity.pk): entity for entity in battlefield.roster.values()
            }
            pending = [
                pk
                for pk in progress["required_actors"]
                if pk not in (record.draft_entries or {}) and pk in entities
            ]
            if not pending:
                raise CampaignFailure(
                    f"the party draft cannot complete for {initiator.key}: "
                    f"{progress!r}"
                )
            result = submit_player_action(
                initiator, BASIC_ATTACK_KEY, [target], commanded_actor=entities[pending[0]]
            )
        return result

    def _play(
        self,
        encounter: _Encounter,
        *,
        roles: Mapping[str, str],
        facts: list[dict[str, Any]],
    ) -> tuple[list[reports.DecisionSample], int, str]:
        """Drive one session round-by-round until terminal settlement or the cap.

        The initiating player is the session's own requester: it selects one
        ordinary action per round against a currently legal living opponent,
        and every remaining required allied actor then confirms its own
        ``basic_attack`` so the last confirmation resolves the one ordinary
        round this harness measures. A submission that settlement refuses, a monster action the
        resolver refuses, or an active session with no legal living opponent
        left, is a simulator failure reported loudly rather than a capped
        encounter; only the session's own terminal outcome or this run's actual
        round bound classifies the encounter. Every committed round is then
        re-read from fresh rows, so the durable round count and the
        participants' stored state are verified as committed state instead of
        as the writing process's own memory.
        """
        traces: list[Any] = []
        #: One entry per recorded decision: the session's OWN execution
        #: identity, beside the trace's (documented) effective scope.
        engine_scopes: list[tuple[Any, ...]] = []
        #: One entry per recorded decision: the encounter-local role of the
        #: deciding monster, as the decision's ``actor_id`` documents it.
        decision_roles: list[str] = []
        monster_keys = {monster.key for monster in encounter.monsters}
        rounds = 0
        last_outcome = "round"
        with self._recording(
            encounter,
            traces,
            engine_scopes,
            decision_roles,
            monster_keys,
            roles,
            facts,
        ):
            for _ in range(reports.ROUND_CAP):
                # Every round runs on freshly re-acquired participants, so the
                # engine's objects, the boundary checks' objects and the
                # committed-round comparison's objects are the same instances
                # and none of them answers from an earlier round's cache.
                encounter.reload()
                initiator = encounter.initiator
                record = read_session(initiator)
                if record is None:
                    break
                target = self._legal_opponent(initiator, record, monster_keys)
                if target is None:
                    raise CampaignFailure(
                        f"{initiator.key} has no legal living opponent left while its "
                        "session is still active"
                    )
                result = submit_player_action(initiator, PLAYER_DRIVER_KEY, [target])
                result = self._confirm_remaining_allies(initiator, target, result)
                rounds += 1
                last_outcome = result.get("outcome")
                if last_outcome not in ("round", "victory", "defeat", "fled", "cap"):
                    raise CampaignFailure(
                        f"unexpected submission outcome {last_outcome!r}: {result!r}"
                    )
                self._verify_committed_round(
                    encounter,
                    rounds,
                    terminal=last_outcome != "round",
                )
                if last_outcome != "round":
                    break
        if last_outcome == "victory":
            outcome = reports.OUTCOME_WIN
        elif last_outcome in ("defeat", "fled"):
            outcome = reports.OUTCOME_LOSS
        else:
            # The session's own terminal cap or this run's actual round bound:
            # an unresolved encounter, never a terminal win or loss.
            outcome = reports.OUTCOME_CAPPED
        samples = [
            self._sample(
                trace, index, roles, decision_roles[index], engine_scopes[index]
            )
            for index, trace in enumerate(traces)
        ]
        return samples, rounds, outcome

    @staticmethod
    def _legal_opponent(initiator: Any, record: Any, monster_keys: set[str]) -> Any:
        """Return one currently legal, living opponent of the live session.

        The target is read from the session's own reconstructed battlefield
        (the same boundary settlement validates against), so a dead, fled or
        knocked-out monster is never submitted against.
        """
        battlefield = reconstruct_battlefield(initiator, record)
        for key in sorted(monster_keys):
            entity = battlefield.roster.get(key)
            if (
                entity is not None
                and key not in battlefield.fled
                and not battlefield.is_knocked_out(key)
                and entity.traits.hp.current > 0
            ):
                return entity
        return None

    def _sample(
        self,
        trace: Any,
        index: int,
        roles: Mapping[str, str],
        actor_role: str,
        engine_scope: tuple[Any, ...],
    ) -> reports.DecisionSample:
        """Project one recorded decision trace into a replayable report sample.

        The sample carries the decision's actual effective selector seed, its
        temperature, the configuration fingerprint the seed was derived with,
        the effective execution identity the seed was derived from and the
        session's own engine identity beside it, the scored plans that were
        sampled from, the selected plan, its measured proposal counters and its
        own initial observation snapshot. Target identities are also mapped to
        their encounter-local roles, so a target distribution never has to be
        read as a raw scratch dbref.

        ``selected_illegal`` stays structurally false: a refused monster action
        aborts the encounter (see :class:`RefusedMonsterAction`) instead of
        being recorded as a weaker accepted result.
        """
        selected = trace.selected
        highest = False
        if selected is not None and trace.plans:
            highest = selected.score >= max(plan.score for plan in trace.plans)
        skill_key = None if selected is None else selected.skill_key
        target_ids = () if selected is None else tuple(selected.target_ids)

        def role_of(identity: Any) -> str:
            return roles.get(identity, f"unknown:{identity}")

        flags: list[str] = []
        for plan in trace.plans:
            flags.extend(limit.value for limit in plan.limits)
        no_action = None
        if selected is None:
            if trace.candidates == 0 and trace.exhausted:
                no_action = reports.NO_ACTION_BUDGET_OMISSION
            elif trace.candidates == 0:
                no_action = reports.NO_ACTION_LEGAL_RESTRICTION
            else:
                no_action = reports.NO_ACTION_ESTIMATOR_EXCLUSION
        return reports.DecisionSample(
            skill_key=skill_key,
            target_ids=target_ids,
            highest_utility=highest,
            selected_illegal=False,
            no_action=no_action,
            index=index,
            actor_role=actor_role,
            target_roles=tuple(role_of(identity) for identity in target_ids),
            seed=trace.seed,
            temperature=trace.temperature,
            configuration_fingerprint=trace.configuration_fingerprint,
            scope=tuple(trace.scope),
            session_scope=tuple(engine_scope),
            plans=tuple(plan.to_payload() for plan in trace.plans),
            selected_plan=None if selected is None else selected.to_payload(),
            examined=len(trace.plans)
            + len(trace.rejections)
            + len(trace.exclusions),
            accepted=len(trace.plans),
            rejections=len(trace.rejections),
            exclusions=len(trace.exclusions),
            omitted_estimates=len(trace.omitted_estimates),
            omitted_families=trace.omitted_families,
            omitted_targets=trace.omitted_targets,
            exhausted=bool(trace.exhausted),
            approximation_flags=tuple(sorted(set(flags))),
            initial_observations=tuple(trace.observations),
            trace=trace.to_payload(),
        )

    @contextmanager
    def _recording(
        self,
        encounter: _Encounter,
        traces: list[Any],
        engine_scopes: list[tuple[Any, ...]],
        decision_roles: list[str],
        monster_keys: set[str],
        roles: Mapping[str, str],
        facts: list[dict[str, Any]],
    ) -> Iterator[None]:
        """Record every monster decision, install the selection seam and fail on refusal.

        The production session provider is wrapped for the duration of one
        encounter only. The wrapper:

        * installs the DOCUMENTED actor identity for the policy call, so a
          decision's selector seed is derived from the encounter-local role
          instead of a scratch dbref and two paired variants decide on matched
          inputs (the session side arrives documented, because the durable
          record itself carries the documented identity);
        * forwards the decision's own trace sink, and keeps the session's own
          execution identity beside each recorded decision;
        * verifies the situation's decision-boundary conditions against the
          decision that was just produced.

        The resolver wrapper runs the same request through settlement and
        aborts the whole batch when a monster's selected action is refused: the
        round resolves each request immediately after the provider call that
        produced it, so the decision just recorded IS the refused one. Both
        wrappers restore the original binding on exit whatever the body raises.
        """
        original_policy = policies_module.monster_behaviour_policy

        def policy(entity, battlefield, **kwargs):
            scope = current_decision_scope()
            before = len(traces)
            kwargs["trace"] = traces
            if scope is None:
                return original_policy(entity, battlefield, **kwargs)
            role = roles.get(
                stable_identity(entity), str(getattr(entity, "key", "unknown"))
            )
            with decision_scope(
                replace(scope, actor_id=reports.manual_actor_id(role))
            ):
                result = original_policy(entity, battlefield, **kwargs)
            if len(traces) > before:
                engine_scopes.append(
                    (
                        scope.session_id,
                        scope.round_index,
                        scope.actor_id,
                        scope.slot_index,
                        scope.context_mode,
                    )
                )
                decision_roles.append(role)
                self._inspect_boundary(
                    encounter, entity, battlefield, traces[-1], role, facts
                )
            return result

        original_resolve = ActionResolver.resolve

        def resolve(request, *args, **kwargs):
            result = original_resolve(request, *args, **kwargs)
            actor = getattr(request, "actor", None)
            if actor is not None and getattr(actor, "key", None) in monster_keys:
                if getattr(result, "outcome", None) != "success":
                    raise RefusedMonsterAction(
                        self._refusal_message(request, result, traces)
                    )
            return result

        policies_module.monster_behaviour_policy = policy
        ActionResolver.resolve = resolve
        try:
            yield
        finally:
            policies_module.monster_behaviour_policy = original_policy
            ActionResolver.resolve = original_resolve

    @staticmethod
    def _refusal_message(request: Any, result: Any, traces: Sequence[Any]) -> str:
        """Return one refusal's message, naming the actor and the decision."""
        actor = getattr(request, "actor", None)
        decision = (
            "no decision was recorded"
            if not traces
            else f"{_decision_label(traces[-1])} with selector seed {traces[-1].seed}"
        )
        return (
            f"settlement refused {getattr(actor, 'key', actor)}'s selected action "
            f"{getattr(request, 'skill_key', None)!r} "
            f"(reason {getattr(result, 'reason', None)!r}, "
            f"detail {getattr(result, 'detail', None)!r}) at {decision}"
        )

    # -- performance scenario ---------------------------------------------
    def run_performance_scenario(
        self, *, warmups: int | None = None, measurements: int | None = None
    ) -> reports.PerformanceReport:
        """Measure the whole policy call in both modes on the reference envelope."""
        self._warmups = reports.PERFORMANCE_WARMUPS if warmups is None else int(warmups)
        self._measurements = (
            reports.PERFORMANCE_MEASUREMENTS if measurements is None else int(measurements)
        )
        timings = []
        for mode in reports.PERFORMANCE_MODES:
            timings.append(self._measure_mode(mode))
        # The scaling probe is ONE fixed battlefield, built once and then probed
        # at each examined-proposal budget: the actor/participant data never
        # varies with the budget, only the enumeration work the decision is
        # allowed to do.
        scaling_field = self._performance_field("utility", enemies=8)
        scaling = [
            self._measure_scaling(budget, scaling_field)
            for budget in reports.PERFORMANCE_SCALING_BUDGETS
        ]
        return reports.PerformanceReport(
            participants=reports.PERFORMANCE_PARTICIPANTS,
            owned_skills=reports.PERFORMANCE_OWNED_SKILLS,
            candidate_budget=reports.PERFORMANCE_CANDIDATE_BUDGET,
            warmups=self._warmups,
            measurements=self._measurements,
            timings=tuple(timings),
            scaling=tuple(scaling),
            budget_ms=reports.PERFORMANCE_P95_BUDGET_MS,
        )

    def _performance_field(
        self, mode: str, *, enemies: int, allies: int | None = None
    ) -> tuple[Any, Any]:
        """Build one reference battle of exactly 16 participants and a decider.

        One decider over the reference envelope: its teammates are the campaign
        kit, the opposing team is a party-side roster of living enemies. The
        scaling probe builds this field once and only varies the decision's
        examined-proposal budget against it.
        """
        if mode == "legacy":
            variant_key = LEGACY_VARIANT_KEY
        else:
            variant_key = _variant_key(self.archetypes[0], reports.INTELLIGENCE_VALUES[1])
        decider = self._monster(
            "perf-decider", variant_key, hp=400, mp=400, skills=_MONSTER_SKILL_KEYS
        )
        if allies is None:
            allies = reports.PERFORMANCE_PARTICIPANTS - 1 - enemies
        teammates = [
            self._monster(f"perf-ally-{index}", variant_key, hp=200, mp=200)
            for index in range(allies)
        ]
        hostiles = [self._player(f"perf-enemy-{index}", 200) for index in range(enemies)]
        roster = {entity.key: entity for entity in (decider, *teammates, *hostiles)}
        teams = {
            "monsters": frozenset(entity.key for entity in (decider, *teammates)),
            "party": frozenset(entity.key for entity in hostiles),
        }
        return decider, Battlefield(teams, roster)

    def _measure_mode(self, mode: str) -> reports.PolicyTiming:
        """Time one mode's complete policy call: cold, warm-ups and measurements."""
        decider, battlefield = self._performance_field(mode, enemies=8)
        context = BattlefieldActionContext(battlefield)
        sink: list[Any] = []
        timing_kwargs = self._timing_callable(decider, battlefield, context, sink)
        queries = {"count": 0}
        with CaptureQueriesContext(connection) as captured:
            cold_ms = self._one(timing_kwargs)
            queries["count"] = len(captured)
        for _ in range(self._warmups):
            self._one(timing_kwargs)
        state_before = random.getstate()
        samples = [self._one(timing_kwargs) for _ in range(self._measurements)]
        dice_isolated = random.getstate() == state_before
        examined, accepted, omitted = _proposal_counters(sink[-1] if sink else None)
        return reports.build_policy_timing(
            mode=mode,
            cold_ms=cold_ms,
            samples_ms=samples,
            queries=queries["count"],
            examined=examined,
            accepted=accepted,
            omitted=omitted,
            dice_isolated=dice_isolated,
        )

    def _timing_callable(self, decider, battlefield, context, sink):
        def call() -> None:
            behaviour.monster_behaviour_policy(
                decider, battlefield, context=context, trace=sink
            )

        return call

    @staticmethod
    def _one(call) -> float:
        """Run one call under the monotonic clock and return its milliseconds."""
        start = time.perf_counter()
        call()
        return (time.perf_counter() - start) * 1000.0

    def _measure_scaling(
        self, budget: int, field: tuple[Any, Any] | None = None
    ) -> reports.ScalingSample:
        """Count one decision's ORM work at one examined-proposal budget.

        The battlefield is one fixed reference roster (supplied by the caller,
        or built here), probed unchanged at every budget: the candidate-count
        variable is the enumeration work the decision is allowed, never a
        different actor's or participant's data.
        """
        if field is None:
            field = self._performance_field("utility", enemies=8)
        decider, battlefield = field
        context = BattlefieldActionContext(battlefield)
        sink: list[Any] = []
        call = self._timing_callable(decider, battlefield, context, sink)
        # Every probe starts from cold caches -- the idmapper's instance cache
        # and each participant's attribute cache -- so the measured call really
        # re-reads the same fixed roster's participants and skills. Every probe
        # therefore reads identical actor/participant data, and any query
        # difference between two budgets can only be the enumeration work.
        flush_cache()
        for entity in battlefield.roster.values():
            entity.attributes.reset_cache()
        with self._examined_proposal_budget(budget):
            with CaptureQueriesContext(connection) as captured:
                call()
        examined, accepted, omitted = _proposal_counters(sink[-1] if sink else None)
        return reports.ScalingSample(
            budget=budget,
            queries=len(captured),
            examined=examined,
            accepted=accepted,
            omitted=omitted,
        )

    @staticmethod
    @contextmanager
    def _examined_proposal_budget(budget: int) -> Iterator[None]:
        """Install one examined-proposal budget for the measured decision.

        The manual scaling seam: the production candidate producer reads its
        module-level default budget only when a decision asks for no explicit
        one, so the probe varies exactly the enumerated-work allowance while
        the roster, the state and the decision body stay fixed. The original
        value is restored whatever the body raises.
        """
        original = candidates_module.DEFAULT_CANDIDATE_BUDGET
        candidates_module.DEFAULT_CANDIDATE_BUDGET = int(budget)
        try:
            yield
        finally:
            candidates_module.DEFAULT_CANDIDATE_BUDGET = original


def _proposal_counters(trace: Any) -> tuple[int, int, int]:
    """Return one decision's measured (examined, accepted, omitted) proposals.

    ``examined`` is every proposal the decision examined -- its accepted
    candidates, its rejections and its mandatory-filter exclusions, which is
    exactly the candidate set's own ``examined`` counter -- never the accepted
    set pretending to be the enumerated work. ``omitted`` is what the
    examined-proposal budget left unexamined, its families and its targets
    together.
    """
    if trace is None:
        return (0, 0, 0)
    return (
        trace.candidates + len(trace.rejections) + len(trace.exclusions),
        len(trace.plans),
        trace.omitted_families + trace.omitted_targets,
    )


def _durable_surface(entity: Any) -> tuple[Any, ...]:
    """Return one participant's durable state: its gauges and its live effects.

    The two hit-point and resource gauges plus the live effect key set are
    exactly what a committed round writes, so the same surface read from the
    engine's own object and from a freshly re-acquired row is the
    committed-reload comparison.
    """
    return (
        _stored_trait_value(entity.traits.hp),
        _stored_trait_value(entity.traits.mp),
        tuple(sorted(entity_active_buffs(entity))),
    )


def rosters_are_identical(left: Any, right: Any) -> bool:
    """Return whether two constructed variants share stats, kit and proficiency.

    The paired campaign changes only the synthetic variant's intelligence, so
    the two constructed individuals must agree on every stored trait, their
    owned skill rows and their resolved proficiency — the guard the report's
    "stats stay identical" claim rests on.
    """
    def surface(entity: Any) -> tuple[Any, ...]:
        traits = entity.attributes.get("traits", category="traits") or {}
        owned = getattr(entity.db, "skills", None) or {}
        return (
            tuple(sorted((key, repr(value)) for key, value in traits.items())),
            tuple(sorted(owned.get("active", []))),
            tuple(sorted(owned.get("passive", []))),
        )

    return surface(left) == surface(right)