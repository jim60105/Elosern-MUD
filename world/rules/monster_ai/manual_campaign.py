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
encounter seeds the process dice from its recorded combat seed and records the
decision seed it was scoped with. The player side of an encounter is a real
production roster — the initiating player plus the companion NPCs bound to it
through ``join_party`` — so a multi-opponent situation is engaged through the
same collection production uses, and a refused monster action is recorded
against the decision that made it rather than asserted away.
"""

from __future__ import annotations

import random
import time
from contextlib import contextmanager
from dataclasses import dataclass, replace
from typing import Any, Iterator, Sequence

from django.db import connection
from django.test.utils import CaptureQueriesContext
from evennia.utils.create import create_object
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
from world.rules.action import ActionResolver
from world.rules.buffs import (
    BUFF_DEFINITIONS,
    apply_buff,
    entity_active_buffs,
    has_positional_marker,
)
from world.rules.combat import COMBAT_YAML, Battlefield, BattlefieldActionContext
from world.rules.combat_session import (
    BASIC_ATTACK_KEY,
    engage_group,
    read_session,
    reconstruct_battlefield,
    submit_player_action,
)
from world.rules.combat_session import ai_tuning as ai_tuning_module
from world.rules.combat_session import observations as observations_module
from world.rules.combat_session import policies as policies_module
from world.rules.monster_ai import manual_reports as reports
from world.rules.monster_individual import construct_species_individual
from world.lore.races import RACE_REGISTRY
from world.rules.party import combat_companions, join_party
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


#: The neutral zero-cost strike the *player* submits to drive a session round
#: (the encounter measures the monster's decisions, not the player's).
PLAYER_STRIKE_KEY = "t_campaign_strike"


def _campaign_skill_rows() -> tuple[Any, ...]:
    """Return the campaign's synthetic skill rows.

    The monster kit carries the reference envelope's own width -- sixteen
    active skills across single/area damage and healing/self-healing shapes --
    so the performance scenario measures the configured ``owned_skills``
    ceiling rather than a convenient handful.
    """
    rows = [
        _skill(PLAYER_STRIKE_KEY, "合成打擊", effects=[f"damage:{_ELEMENT}:physical"], cost={})
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
            )
        )
    return tuple(rows)


_CAMPAIGN_SKILLS = _campaign_skill_rows()
_MONSTER_SKILL_KEYS = tuple(
    row.key for row in _CAMPAIGN_SKILLS if row.key != PLAYER_STRIKE_KEY
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
#: The legacy decider's synthetic variant (never declared utility).
LEGACY_VARIANT_KEY = "t_campaign_legacy"
#: The synthetic row registered under the production basic-attack key, so the
#: non-deciding party members' own default-attack policy resolves.
_BASIC_ATTACK_ROW = _skill(
    BASIC_ATTACK_KEY, "合成基本攻擊", effects=[f"damage:{_ELEMENT}:physical"], cost={}
)


def _positional_buff_key() -> str:
    """Return one shipped buff definition declaring the positional marker."""
    for key in sorted(BUFF_DEFINITIONS):
        if getattr(BUFF_DEFINITIONS[key], "marker", None) == "positional":
            return key
    raise ValueError("no positional-marker buff is authored")


def _timed_buff_key() -> str:
    """Return one shipped buff definition with a short finite duration.

    Applied to the long-lifecycle monster so a real mounted effect expires
    inside the encounter's own committed round count.
    """
    for key in sorted(BUFF_DEFINITIONS):
        duration = getattr(BUFF_DEFINITIONS[key], "duration", None)
        if isinstance(duration, int) and not isinstance(duration, bool):
            if 0 < duration <= 30:
                return key
    raise ValueError("no short-duration buff is authored")


@dataclass(frozen=True, slots=True)
class SituationSpec:
    """One synthetic situation's battlefield configuration.

    Every field is a plain scalar/tuple so a situation declaration can never
    carry a live entity; the harness materializes them per encounter. The
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
    initiator_hp: int = 300
    companion_hp: tuple[int, ...] = ()
    seal_opponents: int = 0
    displaced_opponents: int = 0
    monster_effect: str | None = None
    allied_support: bool = False


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
        # Finishing choice: a credible knockout against a healthy opponent.
        SituationSpec("finishing_choice", monsters=1, monster_hp=90, monster_mp=80,
                      companion_hp=(12,)),
        # Area versus single target: three opponents with uneven remaining HP.
        SituationSpec("area_versus_single", monsters=1, monster_hp=160, monster_mp=80,
                      companion_hp=(150, 40)),
        # Resource exhaustion: useful choices competing for a finite MP pool.
        SituationSpec("resource_exhaustion", monsters=1, monster_hp=110, monster_mp=13,
                      companion_hp=(300,)),
        # Mandatory targeting: two sealed opponents, the leading one also
        # displaced, plus the monster's genuinely legal non-strike
        # alternative (its own actor-bound self-heal).
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
    def _player(self, key: str, hp: int) -> Any:
        """Create the initiating player of one encounter in the arena."""
        player = create_object(PlayerCharacter, key=key)
        player.race = next(iter(RACE_REGISTRY))
        player.apply_race_baseline()
        player.db.skills = {"active": [PLAYER_STRIKE_KEY], "passive": []}
        player.traits.hp.base = hp
        player.traits.hp.current = hp
        player.traits.atk_phys.base = 25
        player.traits.atk_phys.current = 25
        player.traits.defense.base = 15
        player.traits.defense.current = 15
        player.location = self.room
        return player

    def _companion(self, key: str, hp: int) -> Any:
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
        companion.traits.hp.base = hp
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
        skills: Sequence[str] = _ENCOUNTER_SKILL_KEYS,
    ) -> Any:
        monster = construct_species_individual(SPECIES_KEY, variant_key, key=key)
        monster.location = self.room
        monster.traits.hp.base = hp
        monster.traits.hp.current = hp
        monster.traits.mp.base = max(mp, 0)
        monster.traits.mp.current = max(mp, 0)
        # Bound the monster's offense so an encounter terminates inside the
        # round cap instead of the opponents outlasting it.
        monster.traits.atk_phys.base = 8
        monster.traits.atk_phys.current = 8
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
        decision_seed = reports.scenario_seed(situation.name, archetype, seed_index)
        # The paired variants share one combat seed: only the synthetic
        # variant's intelligence differs between the two paired encounters.
        combat_seed = reports.stable_seed("combat", situation.name, archetype, seed_index)
        random.seed(combat_seed)
        variant_key = _variant_key(archetype, intelligence)

        initiator = self._player("campaign-player-0", situation.initiator_hp)
        companions = [
            self._companion(f"campaign-companion-{index}", hp)
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
            )
            if situation.allied_support and index == 1:
                monster.db.skills = {
                    "active": [
                        "t_campaign_heal_0",
                        "t_campaign_selfheal_0",
                        "t_campaign_strike_0",
                    ],
                    "passive": [],
                }
            if situation.monster_effect is not None and index == 0:
                apply_buff(monster, situation.monster_effect)
            monsters.append(monster)
        # The player-side roster production engagement will collect: the
        # initiating player first, then its bound companions in party order.
        opponents = (initiator, *companions)
        for opponent in opponents[: situation.seal_opponents]:
            apply_buff(opponent, _SEAL_BUFF_KEY)
        for opponent in opponents[: situation.displaced_opponents]:
            apply_buff(opponent, _positional_buff_key())

        self._verify_preconditions(situation, initiator, companions)
        engage_group(initiator, monsters)
        samples, rounds, outcome = self._play(initiator, monsters)
        if situation.monster_effect is not None:
            self._verify_effect_expired(
                monsters[0], situation.monster_effect, rounds
            )

        return reports.EncounterOutcome(
            archetype=archetype,
            situation=situation.name,
            seed_index=seed_index,
            intelligence=intelligence,
            decision_seed=decision_seed,
            combat_seed=combat_seed,
            outcome=outcome,
            rounds=rounds,
            decisions=tuple(samples),
        )

    @staticmethod
    def _verify_preconditions(
        situation: SituationSpec, initiator: Any, companions: Sequence[Any]
    ) -> None:
        """Fail the encounter unless its situation's roster really materialized.

        The scenario boundaries are properties of the engaged roster, not of a
        declaration: production engagement must have collected exactly the
        bound companions, and the mounted seal and displacement markers must be
        live on the opponents the situation names. A mismatch is a simulator
        bug that fails the batch rather than a silently weaker scenario.
        """
        engaged = tuple(int(entity.pk) for entity in combat_companions(initiator))
        expected = tuple(int(entity.pk) for entity in companions)
        if engaged != expected:
            raise RuntimeError(
                f"{situation.name}: engaged companions {engaged} do not match the "
                f"bound roster {expected}"
            )
        for position, opponent in enumerate((initiator, *companions)):
            if position < situation.seal_opponents:
                if _SEAL_BUFF_KEY not in entity_active_buffs(opponent):
                    raise RuntimeError(
                        f"{situation.name}: opponent {opponent.key} carries no live seal"
                    )
            if position < situation.displaced_opponents:
                if not has_positional_marker(opponent):
                    raise RuntimeError(
                        f"{situation.name}: opponent {opponent.key} carries no live "
                        "positional marker"
                    )

    @staticmethod
    def _verify_effect_expired(monster: Any, effect: str, rounds: int) -> None:
        """Fail the encounter unless its finite mounted effect really expired."""
        seconds = int(COMBAT_YAML["round"]["seconds"]) * rounds
        duration = BUFF_DEFINITIONS[effect].duration or 0
        if seconds <= duration:
            raise RuntimeError(
                f"the encounter ran {seconds}s, too short to expire the mounted "
                f"effect {effect!r} ({duration}s)"
            )
        if effect in entity_active_buffs(monster):
            raise RuntimeError(
                f"the mounted effect {effect!r} outlived the encounter's {rounds} rounds"
            )

    def _play(
        self, initiator: Any, monsters: Sequence[Any]
    ) -> tuple[list[reports.DecisionSample], int, str]:
        """Drive one session round-by-round until terminal settlement or the cap.

        The initiating player is the session's own requester, so every round
        submits one ordinary action from it against a currently legal living
        opponent. A submission that settlement refuses, or an active session
        with no legal living opponent left, is a simulator failure reported
        loudly rather than a capped encounter; only the session's own terminal
        outcome or this run's actual round bound classifies the encounter.
        """
        traces: list[Any] = []
        refused: set[int] = set()
        monster_keys = {monster.key for monster in monsters}
        rounds = 0
        last_outcome = "round"
        with self._recording(traces, refused, monster_keys):
            for _ in range(reports.ROUND_CAP):
                record = read_session(initiator)
                if record is None:
                    break
                target = self._legal_opponent(initiator, record, monster_keys)
                if target is None:
                    raise RuntimeError(
                        f"{initiator.key} has no legal living opponent left while its "
                        "session is still active"
                    )
                result = submit_player_action(initiator, PLAYER_STRIKE_KEY, [target])
                rounds += 1
                last_outcome = result.get("outcome")
                if last_outcome not in ("round", "victory", "defeat", "fled", "cap"):
                    raise RuntimeError(
                        f"unexpected submission outcome {last_outcome!r}: {result!r}"
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
            self._sample(trace, index, refused)
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
        self, trace: Any, index: int, refused: set[int]
    ) -> reports.DecisionSample:
        """Project one recorded decision trace into a report sample.

        ``refused`` carries the zero-based decision indices whose selected
        action settlement refused, so the report's selected-illegal count is
        measured from the encounter rather than asserted.
        """
        selected = trace.selected
        highest = False
        if selected is not None and trace.plans:
            highest = selected.score >= max(plan.score for plan in trace.plans)
        skill_key = None if selected is None else selected.skill_key
        target_ids = () if selected is None else tuple(selected.target_ids)
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
            selected_illegal=index in refused,
            no_action=no_action,
            rejections=len(trace.rejections),
            exclusions=len(trace.exclusions),
            omitted_estimates=len(trace.omitted_estimates),
            omitted_families=trace.omitted_families,
            exhausted=bool(trace.exhausted),
            approximation_flags=tuple(sorted(set(flags))),
            initial_observations=tuple(trace.observations),
        )

    @contextmanager
    def _recording(
        self, traces: list[Any], refused: set[int], monster_keys: set[str]
    ) -> Iterator[None]:
        """Record every monster decision's trace and settlement rejection.

        The production session provider is wrapped for the duration of one
        encounter only: the wrapper forwards the decision's own trace sink, and
        the resolver wrapper flags the decision whose selected action settlement
        refused. The round resolves each request immediately after the provider
        call that produced it, so the decision just recorded IS the refused one.
        Both wrappers restore the original binding on exit whatever the body
        raises.
        """
        original_policy = policies_module.monster_behaviour_policy

        def policy(entity, battlefield, **kwargs):
            kwargs["trace"] = traces
            return original_policy(entity, battlefield, **kwargs)

        original_resolve = ActionResolver.resolve

        def resolve(request, *args, **kwargs):
            result = original_resolve(request, *args, **kwargs)
            actor = getattr(request, "actor", None)
            if actor is not None and getattr(actor, "key", None) in monster_keys:
                if getattr(result, "outcome", None) != "success" and traces:
                    refused.add(len(traces) - 1)
            return result

        policies_module.monster_behaviour_policy = policy
        ActionResolver.resolve = resolve
        try:
            yield
        finally:
            policies_module.monster_behaviour_policy = original_policy
            ActionResolver.resolve = original_resolve

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
        scaling = []
        for mode in reports.PERFORMANCE_MODES:
            timings.append(self._measure_mode(mode))
        for count in reports.PERFORMANCE_SCALING_COUNTS:
            scaling.append(self._measure_scaling(count))
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

        The participant total is held constant: the scaling probe trades allied
        participants for enemies, so the candidate count varies on the SAME
        recorded actor/participant data rather than alongside it.
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
        trace = sink[-1] if sink else None
        examined = 0 if trace is None else trace.candidates
        accepted = 0 if trace is None else len(trace.plans)
        omitted = 0 if trace is None else len(trace.omitted_estimates)
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

    def _measure_scaling(self, enemies: int) -> reports.ScalingSample:
        """Count the ORM work of one decision at one enemy-participant count."""
        from evennia.utils.idmapper.models import flush_cache

        decider, battlefield = self._performance_field("utility", enemies=enemies)
        context = BattlefieldActionContext(battlefield)
        sink: list[Any] = []
        call = self._timing_callable(decider, battlefield, context, sink)
        # Flush the entity cache so the measured call really re-reads its
        # participants and skills instead of answering from the idmapper.
        flush_cache()
        with CaptureQueriesContext(connection) as captured:
            call()
        trace = sink[-1]
        return reports.ScalingSample(
            candidates=enemies, queries=len(captured), examined=trace.candidates
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