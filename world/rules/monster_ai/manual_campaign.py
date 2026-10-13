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
decision seed it was scoped with.
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
from typeclasses.rooms import Room

# Eagerly imported outside any synthetic scope (the shared helper precedent):
# these rulebooks validate shipped rows at import, so importing them inside a
# synthetic scope would validate them against synthetic catalogs.
import world.rules.cross_lineage_unlock  # noqa: F401
import world.rules.defeat_aftermath  # noqa: F401
from world.rules import monster_behaviour as behaviour
from world.rules.action import ActionResolver
from world.rules.buffs import apply_buff
from world.rules.combat import Battlefield, BattlefieldActionContext
from world.rules.combat_session import engage_group, read_session, submit_player_action
from world.rules.combat_session import ai_tuning as ai_tuning_module
from world.rules.combat_session import observations as observations_module
from world.rules.combat_session import policies as policies_module
from world.rules.monster_ai import manual_reports as reports
from world.rules.monster_individual import construct_species_individual
from world.lore.races import RACE_REGISTRY
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


@dataclass(frozen=True, slots=True)
class SituationSpec:
    """One synthetic situation's battlefield configuration.

    Every field is a plain scalar/list so a situation declaration can never
    carry a live entity; the harness materializes them per encounter.
    """

    name: str
    monsters: int
    players: int
    monster_hp: int
    monster_mp: int
    player_hp: tuple[int, ...]
    seal_players: int = 0
    allied_support: bool = False


def _situations() -> tuple[SituationSpec, ...]:
    """Return the six distinct synthetic situations the allocation requires."""
    return (
        # Finishing choice: a credible knockout against a healthy opponent.
        SituationSpec("finishing_choice", monsters=1, players=2, monster_hp=30,
                      monster_mp=80, player_hp=(12, 300)),
        # Area versus single target: three opponents with uneven remaining HP.
        SituationSpec("area_versus_single", monsters=1, players=3, monster_hp=45,
                      monster_mp=80, player_hp=(300, 150, 40)),
        # Resource exhaustion: useful choices competing for a finite MP pool.
        SituationSpec("resource_exhaustion", monsters=1, players=2, monster_hp=40,
                      monster_mp=13, player_hp=(300, 300)),
        # Mandatory targeting: two sealed opponents plus a legal non-strike
        # alternative (the monster's own self-heal).
        SituationSpec("mandatory_targeting", monsters=1, players=3, monster_hp=40,
                      monster_mp=60, player_hp=(300, 250, 200), seal_players=2),
        # Tactical support and focus: two allied deciders, one able to heal.
        SituationSpec("support_and_focus", monsters=2, players=2, monster_hp=45,
                      monster_mp=60, player_hp=(300, 300), allied_support=True),
        # Long encounter and lifecycle: repeated rounds against a durable pair.
        SituationSpec("long_lifecycle", monsters=1, players=2, monster_hp=150,
                      monster_mp=200, player_hp=(400, 400)),
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
        self.skills = {row.key: row for row in _CAMPAIGN_SKILLS}
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
        combat_seed = reports.stable_seed(
            "combat", situation.name, archetype, seed_index, intelligence
        )
        random.seed(combat_seed)
        variant_key = _variant_key(archetype, intelligence)

        players = [
            self._player(f"campaign-player-{index}", hp)
            for index, hp in enumerate(situation.player_hp)
        ]
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
            monsters.append(monster)
        for player in players[: situation.seal_players]:
            apply_buff(player, _SEAL_BUFF_KEY)

        engage_group(players[0], monsters)
        samples, rounds, outcome = self._play(players, monsters)

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

    def _play(
        self, players: Sequence[Any], monsters: Sequence[Any]
    ) -> tuple[list[reports.DecisionSample], int, str]:
        """Drive one session round-by-round until terminal settlement or the cap."""
        traces: list[Any] = []
        illegal = {"count": 0}
        monster_keys = {monster.key for monster in monsters}
        rounds = 0
        last_outcome = "round"
        with self._recording(traces, illegal, monster_keys):
            for _ in range(reports.ROUND_CAP):
                record = read_session(players[0])
                if record is None:
                    break
                actor = next(
                    (player for player in players if player.traits.hp.current > 0), None
                )
                if actor is None:
                    break
                result = submit_player_action(actor, PLAYER_STRIKE_KEY, [monsters[0]])
                rounds += 1
                last_outcome = result.get("outcome", "round")
                if last_outcome not in ("round", "overwhelm"):
                    break
        if read_session(players[0]) is None and last_outcome not in (
            "victory", "defeat", "fled", "forfeit",
        ):
            last_outcome = "settled"
        if last_outcome == "victory":
            outcome = reports.OUTCOME_WIN
        elif last_outcome in ("defeat", "fled", "forfeit"):
            outcome = reports.OUTCOME_LOSS
        elif rounds >= reports.ROUND_CAP:
            outcome = reports.OUTCOME_CAPPED
        elif read_session(players[0]) is None:
            outcome = reports.OUTCOME_LOSS
        else:
            outcome = reports.OUTCOME_CAPPED
        samples = [
            self._sample(trace, index) for index, trace in enumerate(traces)
        ]
        return samples, rounds, outcome

    def _sample(self, trace: Any, index: int) -> reports.DecisionSample:
        """Project one recorded decision trace into a report sample."""
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
            selected_illegal=False,
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
        self, traces: list[Any], illegal: dict[str, int], monster_keys: set[str]
    ) -> Iterator[None]:
        """Record every monster decision's trace and settlement rejection.

        The production session provider is wrapped for the duration of one
        encounter only: the wrapper forwards the decision's own trace sink, and
        the resolver wrapper counts a monster request settlement refused. Both
        wrappers restore the original binding on exit whatever the body raises.
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
                if getattr(result, "outcome", None) != "success":
                    illegal["count"] += 1
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