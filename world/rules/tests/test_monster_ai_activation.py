"""Data-contract test: staged activation of the named production variant set: real registry binding, one settled production encounter, the release record and the legacy rollback restart seam

This module is the evidence carrier for ``monster-ai-rollout``. It names the
shipped bestiary on purpose: what it establishes is the *production* result of
this slice -- which registered variants the shipped rulebook activates, that
each one resolves through the real species/variant registry, that one affected
variant really decides through the utility path and settles a committed round,
that every other registered variant keeps the permanent legacy decision, and
that the release record's fingerprints are the ones this tuning actually
produces.

The synthetic-mechanism contracts of the earlier slices live in their own
modules; this one carries the shipped-content claims that only shipped data can
make, under the ``Data-contract test:`` convention
(``docs/development/spec-test-traceability.md``, ``tools/test_data_lint.py``).

Everything else is the real engine: real ``Monster``/``PlayerCharacter`` rows,
the real legality gates, the real estimator, the real selector, the real round
loop, the real session adapter and the production invalid-state boundary.
"""

from tools.spec_traceability import covers_requirement

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import yaml

from django.db import DatabaseError
from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import Room

from world.lore.monster_species import MONSTER_VARIANT_REGISTRY
from world.rules.action import ActionRequest
from world.rules import monster_behaviour as behaviour
from world.rules.combat import (
    Battlefield,
    BattlefieldActionContext,
    ExecutionScopeBase,
    run_round,
)
from world.rules.combat_session.ai_tuning import (
    clear_session_ai_tuning,
    record_session_ai_tuning,
    session_ai_tuning,
)
from world.rules.combat_session import policies
from world.rules.combat_session.observations import (
    clear_session_memory,
    observe_action,
    session_observations,
)
from world.rules.combat_session.policies import BASIC_ATTACK_KEY, _enemy_policy
from world.rules.combat_session.records import CombatSessionRecord
from world.rules.disengage import FLEE_SKILL_KEY
from world.rules.monster_behaviour import (
    AI_ALGORITHM_VERSION,
    MONSTER_AI_TUNING,
    DecisionMode,
    monster_behaviour_policy,
    resolve_monster_ai,
)
from world.rules.monster_individual import construct_species_individual
from world.skills.registry import SKILL_REGISTRY, SkillKind

from ._combat_session_helpers import _player as _combat_player

REPO_ROOT = Path(__file__).resolve().parents[3]
ACTIVATION_RECORD = (
    REPO_ROOT / "docs" / "development" / "monster-ai-activation-evidence" / "activation.json"
)

# The four canonical requirement IDs of this capability are inlined at each
# annotation below, because the traceability gate reads string literals only:
# ``activation-follows-complete-accepted-evidence``,
# ``expansion-and-retuning-require-affected-evidence``,
# ``legacy-mode-rollback-is-demonstrated`` and
# ``release-evidence-is-reproducible-and-scoped``.

#: One activation evidence UUID per documented operation (see the record).
SESSION = "activation:1:0"
ROLLBACK_SESSION = "activation:2:0"


def _record() -> dict:
    """Return the committed release record of this activation."""
    return json.loads(ACTIVATION_RECORD.read_text(encoding="utf-8"))


def _activated() -> dict[str, int]:
    """Return the named set and its authored intelligence, from the record."""
    return dict(_record()["activated"])


def _legacy_edited_tuning():
    """Load the shipped rulebook with the activation's modes edited back to legacy.

    This is the restart seam: the edited tuning is written to a temporary YAML
    file and read back through the production loader (``_load_rulebook`` ->
    ``_load_behaviour_profiles`` -> ``_load_ai_tuning``), exactly as a restarted
    process would load a changed on-disk mode. Nothing durable changes, so no
    migration or database restore is involved.
    """
    authored = dict(behaviour.MONSTER_BEHAVIOUR_YAML)
    authored["variant_decision_mode"] = {}
    with TemporaryDirectory() as directory:
        path = Path(directory) / "monster_behaviour.yaml"
        path.write_text(
            yaml.safe_dump(authored, allow_unicode=True, sort_keys=True),
            encoding="utf-8",
        )
        rulebook = behaviour._load_rulebook(path)
    profiles = behaviour._load_behaviour_profiles(rulebook)
    return behaviour._load_ai_tuning(rulebook, profiles=profiles)


def _stored(entity, trait_key: str) -> float:
    """One entity's committed gauge, read back from its own fresh row.

    A freshly constructed monster stores only its authored value until the first
    write, so the read falls back to the base when no current value exists yet.
    """
    traits = dict(
        ObjectDB.objects.get(id=entity.pk).attributes.get(
            "traits", default={}, category="traits"
        )
    )
    record = dict(traits.get(trait_key, {}))
    return float(record.get("current", record.get("base", 0.0)))


def _authored_surface(entity) -> tuple:
    """One entity's authored combat surface: every statistic, kit and proficiency.

    The activation and any retuning of it are decision tuning only: a variant's
    intelligence may not move a statistic, a resource pool, an owned skill or a
    proficiency. Only the authored (base) values are compared, because a real
    round legitimately moves the current gauges it settles.
    """
    traits = entity.attributes.get("traits", default={}, category="traits")
    statistics = tuple(
        (key, record["base"])
        for key, record in sorted(traits.items())
        if isinstance(record, dict) and "base" in record
    )
    skills = entity.db.skills or {}
    return (
        statistics,
        tuple(sorted(skills.get("active", ()))),
        tuple(sorted(skills.get("passive", ()))),
        entity.db.proficiency,
    )


def _first_owned_damage_key(entity) -> str:
    """The authored legacy contract's own skill choice: the first owned damage row.

    ``skill_choice: first_owned`` selects the first affordable active damage
    skill in the entity's owned order, so the expectation is written here from
    the declaration itself instead of being read back out of the selector.
    """
    for key in entity.skills.owned_keys():
        skill = SKILL_REGISTRY.get(key)
        if (
            skill is not None
            and skill.kind is SkillKind.ACTIVE
            and any(effect.startswith("damage:") for effect in skill.effects)
        ):
            return key
    raise AssertionError("the variant owns no damage skill")


def _defender(key: str, hp: int) -> PlayerCharacter:
    """Create one real player-side combatant with an authored hit-point pool."""
    defender = _combat_player(key)
    defender.traits.hp.base = hp
    defender.traits.hp.current = hp
    return defender


def _variant_keys() -> list[str]:
    """Every registered variant key, sorted."""
    return sorted(MONSTER_VARIANT_REGISTRY)


class ActivationRecordTests(EvenniaTestCase):
    """The release record and the evidence it points at describe this tuning."""

    @covers_requirement(
        "monster-ai-rollout::activation-follows-complete-accepted-evidence",
        "monster-ai-rollout::release-evidence-is-reproducible-and-scoped",
    )
    def test_the_release_record_names_the_loaded_startup_tuning(self):
        record = _record()
        self.assertEqual(record["algorithm_version"], AI_ALGORITHM_VERSION)
        self.assertEqual(
            record["configuration_fingerprint"], MONSTER_AI_TUNING.fingerprint
        )
        self.assertEqual(record["activated"], dict(MONSTER_AI_TUNING.variant_intelligence))
        self.assertEqual(
            sorted(record["activated"]), sorted(MONSTER_AI_TUNING.variant_decision_mode)
        )
        for key, mode in MONSTER_AI_TUNING.variant_decision_mode.items():
            with self.subTest(variant=key):
                self.assertIs(mode, DecisionMode.UTILITY)
                self.assertIn(key, MONSTER_VARIANT_REGISTRY)
        # The named set is a small one: the rest of the registry authors neither
        # an intelligence nor a mode override.
        self.assertLess(len(record["activated"]), len(_variant_keys()))

    @covers_requirement("monster-ai-rollout::release-evidence-is-reproducible-and-scoped")
    def test_every_referenced_evidence_file_carries_the_recorded_fingerprint(self):
        record = _record()
        self.assertTrue(record["evidence"], "the record references no evidence")
        for entry in record["evidence"]:
            path = REPO_ROOT / entry["path"]
            with self.subTest(path=entry["path"]):
                self.assertTrue(path.is_file(), entry["path"])
                report = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(
                    report["configuration_fingerprint"],
                    entry["fingerprint"],
                    entry["path"],
                )
                self.assertEqual(
                    report["algorithm_version"], record["algorithm_version"], entry["path"]
                )

    @covers_requirement("monster-ai-rollout::release-evidence-is-reproducible-and-scoped")
    def test_the_recorded_performance_evidence_meets_the_warm_budget(self):
        performance = json.loads(
            (
                REPO_ROOT
                / "docs"
                / "development"
                / "monster-ai-manual-evidence"
                / "performance.json"
            ).read_text(encoding="utf-8")
        )
        self.assertTrue(performance["budget_met"])
        budget = float(performance["envelope"]["budget_ms"])
        utility = [
            timing for timing in performance["timings"] if timing["mode"] == "utility"
        ]
        self.assertEqual(len(utility), 1)
        self.assertLessEqual(float(utility[0]["p95_ms"]), budget)
        self.assertGreater(int(utility[0]["examined"]), 0)

    @covers_requirement("monster-ai-rollout::release-evidence-is-reproducible-and-scoped")
    def test_the_recorded_selector_evidence_clears_its_required_margin(self):
        selector = json.loads(
            (
                REPO_ROOT
                / "docs"
                / "development"
                / "monster-ai-manual-evidence"
                / "selector-check.json"
            ).read_text(encoding="utf-8")
        )
        self.assertTrue(selector["margin_met"])
        self.assertGreaterEqual(
            float(selector["paired_difference"]), float(selector["margin_required"])
        )


class ActivationBindingTests(EvenniaTestCase):
    """The named set binds through the real registry; everything else is legacy."""

    @covers_requirement("monster-ai-rollout::activation-follows-complete-accepted-evidence")
    def test_the_named_set_resolves_through_the_real_species_variant_registry(self):
        activated = _activated()
        for key, intelligence in sorted(activated.items()):
            variant = MONSTER_VARIANT_REGISTRY[key]
            monster = construct_species_individual(
                variant.species_key, key, key=f"activation {key}"
            )
            with self.subTest(variant=key):
                resolution = resolve_monster_ai(monster)
                self.assertIsNotNone(resolution)
                self.assertIs(resolution.mode, DecisionMode.UTILITY)
                self.assertIsNone(resolution.invalid_reason)
                self.assertEqual(resolution.intelligence, intelligence)
                self.assertEqual(resolution.variant_key, key)
                self.assertEqual(
                    resolution.archetype_key, variant.behaviour_profile_key
                )
                self.assertEqual(
                    resolution.tuning_fingerprint, MONSTER_AI_TUNING.fingerprint
                )

    @covers_requirement("monster-ai-rollout::activation-follows-complete-accepted-evidence")
    def test_every_other_registered_variant_stays_legacy(self):
        activated = set(_activated())
        others = [key for key in _variant_keys() if key not in activated]
        self.assertEqual(len(others), len(_variant_keys()) - len(activated))
        for key in others:
            variant = MONSTER_VARIANT_REGISTRY[key]
            monster = construct_species_individual(
                variant.species_key, key, key=f"legacy {key}"
            )
            with self.subTest(variant=key):
                resolution = resolve_monster_ai(monster)
                self.assertIsNotNone(resolution)
                self.assertIs(resolution.mode, DecisionMode.LEGACY)
                self.assertIsNone(resolution.invalid_reason)
                self.assertIsNone(resolution.intelligence)
                self.assertEqual(resolution.variant_key, key)

    @covers_requirement("monster-ai-rollout::expansion-and-retuning-require-affected-evidence")
    def test_a_retuned_profile_moves_the_fingerprint_and_rebalances_nothing(self):
        record = _record()
        key = sorted(_activated())[0]
        retuned_book = dict(behaviour.MONSTER_BEHAVIOUR_YAML)
        retuned_book["variant_intelligence"] = dict(
            retuned_book["variant_intelligence"], **{key: _activated()[key] + 1}
        )
        profiles = behaviour._load_behaviour_profiles(retuned_book)
        retuned = behaviour._load_ai_tuning(retuned_book, profiles=profiles)
        # An affected-profile edit always produces a new fingerprint, so the
        # recorded acceptance claims can no longer stand for the changed tuning.
        self.assertNotEqual(retuned.fingerprint, MONSTER_AI_TUNING.fingerprint)
        self.assertNotEqual(retuned.fingerprint, record["configuration_fingerprint"])
        self.assertEqual(
            {
                other: value
                for other, value in retuned.variant_intelligence.items()
                if other != key
            },
            {
                other: value
                for other, value in MONSTER_AI_TUNING.variant_intelligence.items()
                if other != key
            },
        )
        variant = MONSTER_VARIANT_REGISTRY[key]
        monster = construct_species_individual(
            variant.species_key, key, key="activation retune probe"
        )
        surface = _authored_surface(monster)
        with patch.object(behaviour, "MONSTER_AI_TUNING", retuned):
            resolution = resolve_monster_ai(monster)
        self.assertEqual(resolution.intelligence, _activated()[key] + 1)
        # Intelligence is decision tuning only: no statistic, resource, owned
        # skill or proficiency came with it.
        self.assertEqual(_authored_surface(monster), surface)
        # The same requirement covers a weight edit of the affected profile:
        # moving one authored weight also produces a new fingerprint, so a claim
        # recorded under the earlier tuning no longer describes it, and it is
        # likewise decision tuning rather than a statistic rebalance.
        archetype = MONSTER_VARIANT_REGISTRY[key].behaviour_profile_key
        retuned_archetypes = dict(retuned_book["archetypes"])
        retuned_archetypes[archetype] = dict(
            retuned_archetypes[archetype],
            utility_weights=dict(
                retuned_archetypes[archetype]["utility_weights"], damage=2.0
            ),
        )
        weight_book = dict(retuned_book, archetypes=retuned_archetypes)
        weight_tuning = behaviour._load_ai_tuning(
            weight_book, profiles=behaviour._load_behaviour_profiles(weight_book)
        )
        self.assertNotEqual(weight_tuning.fingerprint, MONSTER_AI_TUNING.fingerprint)
        self.assertNotEqual(
            weight_tuning.fingerprint, record["configuration_fingerprint"]
        )
        with patch.object(behaviour, "MONSTER_AI_TUNING", weight_tuning):
            self.assertIs(resolve_monster_ai(monster).mode, DecisionMode.UTILITY)
        self.assertEqual(_authored_surface(monster), surface)


class RealEncounterTests(EvenniaTestCase):
    """One affected real encounter decides and settles through the utility path."""

    def setUp(self):
        super().setUp()
        clear_session_ai_tuning()
        clear_session_memory()
        self.addCleanup(clear_session_ai_tuning)
        self.addCleanup(clear_session_memory)
        #: The opt-in decision traces and the requests this round really settled.
        self.traces: list = []
        self.requests: list = []
        self.room = create_object(Room, key="activation arena")
        self.defender = _defender("activation defender", 400)
        self.defender.location = self.room
        variant_key = sorted(_activated())[0]
        variant = MONSTER_VARIANT_REGISTRY[variant_key]
        self.variant_key = variant_key
        self.variant = variant
        self.monster = construct_species_individual(
            variant.species_key, variant_key, key="activation decider"
        )
        self.monster.location = self.room
        self.field = Battlefield(
            {
                "foes": frozenset({str(self.monster.key)}),
                "party": frozenset({str(self.defender.key)}),
            },
            {
                str(self.monster.key): self.monster,
                str(self.defender.key): self.defender,
            },
        )
        self.record = CombatSessionRecord(
            session_id=SESSION,
            mode="normal",
            room_id=self.room.pk,
            player_ids=(self.defender.pk,),
            enemy_ids=(self.monster.pk,),
            fled_ids=(),
            knocked_out_ids=(),
            rounds_elapsed=0,
            exam_id=None,
        )

    def _decide(self, entity, battlefield):
        """The production session adapter for the monster, other combatants idle.

        ``_enemy_policy`` is the boundary production uses: it records this
        session's tuning for the actor and builds the session's settlement
        context before the decision. Every other combatant stays idle, so the
        monster's own action is the round's only write and the unchanged-surface
        comparison stays meaningful.
        """
        if str(entity.key) != str(self.monster.key):
            return None
        return _enemy_policy(entity, battlefield, self.record)

    @covers_requirement("monster-ai-rollout::activation-follows-complete-accepted-evidence")
    def test_one_affected_encounter_selects_and_settles_with_unchanged_stats(self):
        surface = _authored_surface(self.monster)
        before_hp = _stored(self.defender, "hp")
        before_monster_hp = _stored(self.monster, "hp")
        real_policy = policies.monster_behaviour_policy

        def traced_policy(*args, **kwargs):
            """Forward to the real decision, adding only the opt-in trace sink."""
            request = real_policy(*args, **kwargs, trace=self.traces)
            self.requests.append(request)
            return request

        with (
            patch.object(policies, "monster_behaviour_policy", traced_policy),
            patch("world.rules.combat.rounds.roll_d100", return_value=95),
            patch("world.rules.combat.damage.roll_d100", return_value=95),
        ):
            logs = run_round(
                self.field,
                self._decide,
                decision_scope_base=ExecutionScopeBase(SESSION, 1),
            )
        # The decision really was the utility decision, in this session's scope.
        self.assertEqual(len(self.traces), 1)
        trace = self.traces[0]
        self.assertGreaterEqual(trace.candidates, 1)
        self.assertIsNotNone(trace.selected)
        self.assertEqual(trace.scope[0], SESSION)
        self.assertEqual(trace.scope[1], 1)
        self.assertFalse(trace.inspected)
        self.assertEqual(trace.algorithm_version, AI_ALGORITHM_VERSION)
        self.assertEqual(trace.configuration_fingerprint, MONSTER_AI_TUNING.fingerprint)
        self.assertEqual(trace.intelligence, _activated()[self.variant_key])
        self.assertTrue(trace.selected.target_ids)
        # The trace describes the request that really went to settlement.
        self.assertEqual(len(self.requests), 1)
        self.assertEqual(self.requests[0].skill_key, trace.selected.skill_key)
        self.assertEqual(self.requests[0].scale, trace.selected.scale)
        self.assertIn(trace.selected.skill_key, self.monster.skills.owned_keys())
        # The selected action was legal and really settled: the round wrote a
        # damage entry and the defender's committed hit points fell.
        kinds = [entry.kind for log in logs for entry in log.entries]
        self.assertIn("damage", kinds)
        self.assertLess(_stored(self.defender, "hp"), before_hp)
        # The session recorded the tuning it actually decided with.
        recorded = session_ai_tuning(SESSION)[f"dbref:{self.monster.pk}"]
        self.assertIs(recorded.mode, DecisionMode.UTILITY)
        self.assertEqual(recorded.tuning_fingerprint, MONSTER_AI_TUNING.fingerprint)
        # Nothing about the monster itself moved: no statistic, resource, owned
        # skill or proficiency is carried by the activation.
        self.assertEqual(_authored_surface(self.monster), surface)
        self.assertEqual(_stored(self.monster, "hp"), before_monster_hp)


class RollbackTests(EvenniaTestCase):
    """Editing the mode back to legacy and restarting restores the legacy decision."""

    def setUp(self):
        super().setUp()
        clear_session_ai_tuning()
        clear_session_memory()
        self.addCleanup(clear_session_ai_tuning)
        self.addCleanup(clear_session_memory)
        self.room = create_object(Room, key="rollback arena")
        self.variant_key = sorted(_activated())[0]
        self.variant = MONSTER_VARIANT_REGISTRY[self.variant_key]
        self.monster = construct_species_individual(
            self.variant.species_key, self.variant_key, key="rollback decider"
        )
        self.monster.location = self.room
        self.weak = _defender("rollback weak", 50)
        self.strong = _defender("rollback strong", 400)
        self.field = Battlefield(
            {
                "foes": frozenset({str(self.monster.key)}),
                "party": frozenset({str(self.weak.key), str(self.strong.key)}),
            },
            {
                str(self.monster.key): self.monster,
                str(self.weak.key): self.weak,
                str(self.strong.key): self.strong,
            },
        )
        self.record = CombatSessionRecord(
            session_id=ROLLBACK_SESSION,
            mode="normal",
            room_id=self.room.pk,
            player_ids=(self.weak.pk, self.strong.pk),
            enemy_ids=(self.monster.pk,),
            fled_ids=(),
            knocked_out_ids=(),
            rounds_elapsed=0,
            exam_id=None,
        )

    def _decide(self, entity, battlefield):
        """The production session adapter for the monster, other combatants idle."""
        if str(entity.key) != str(self.monster.key):
            return None
        return _enemy_policy(entity, battlefield, self.record)

    @covers_requirement("monster-ai-rollout::legacy-mode-rollback-is-demonstrated")
    def test_a_restart_loading_the_edited_mode_reproduces_the_legacy_smoke(self):
        record = _record()["legacy_rollback"]
        rollback = _legacy_edited_tuning()
        self.assertEqual(rollback.fingerprint, record["configuration_fingerprint"])
        self.assertEqual(dict(rollback.variant_decision_mode), {})
        self.assertEqual(
            dict(rollback.variant_intelligence), _activated()
        )
        with patch.object(behaviour, "MONSTER_AI_TUNING", rollback):
            # Target and skill: the permanent legacy rule chooses the lowest-HP
            # living enemy and its first owned damage skill, with no dice spent.
            with patch.object(
                behaviour.dice,
                "roll_d100",
                side_effect=AssertionError("legacy selection consumes no dice"),
            ):
                request = monster_behaviour_policy(
                    self.monster, self.field, context=BattlefieldActionContext(self.field)
                )
            self.assertIsNotNone(request)
            self.assertEqual(str(request.targets[0].key), str(self.weak.key))
            self.assertEqual(request.skill_key, _first_owned_damage_key(self.monster))
            self.assertEqual(request.scale, 1.0)
            # The same restarted tuning through a real round: the legacy action
            # reaches the real resolver, damages the lowest-hit-point enemy only,
            # commits, and leaves the untouched recipient exactly as it was.
            before_weak = _stored(self.weak, "hp")
            before_strong = _stored(self.strong, "hp")
            with (
                patch("world.rules.combat.rounds.roll_d100", return_value=95),
                patch("world.rules.combat.damage.roll_d100", return_value=95),
            ):
                logs = run_round(
                    self.field,
                    self._decide,
                    decision_scope_base=ExecutionScopeBase(ROLLBACK_SESSION, 1),
                )
            kinds = [entry.kind for log in logs for entry in log.entries]
            self.assertIn("damage", kinds)
            self.assertLess(_stored(self.weak, "hp"), before_weak)
            self.assertEqual(_stored(self.strong, "hp"), before_strong)
            settled = session_ai_tuning(ROLLBACK_SESSION)[f"dbref:{self.monster.pk}"]
            self.assertIs(settled.mode, DecisionMode.LEGACY)
            self.assertEqual(settled.tuning_fingerprint, rollback.fingerprint)
            # Flee priority: at or below the archetype's authored fraction the
            # legacy body flees instead of attacking, at its own threshold, and
            # that request settles as a real disengage attempt and not damage.
            profile = behaviour.BEHAVIOUR_PROFILES[self.variant.behaviour_profile_key]
            self.assertIsNotNone(profile.flee_hp_fraction)
            self.monster.traits.hp.current = int(
                self.monster.traits.hp.base * profile.flee_hp_fraction
            )
            fleeing = monster_behaviour_policy(
                self.monster, self.field, context=BattlefieldActionContext(self.field)
            )
            self.assertEqual(fleeing.skill_key, FLEE_SKILL_KEY)
            self.assertEqual([str(target.key) for target in fleeing.targets], [str(self.monster.key)])
            before_weak = _stored(self.weak, "hp")
            with patch("world.rules.combat.rounds.roll_d100", return_value=95):
                flee_logs = run_round(
                    self.field,
                    self._decide,
                    decision_scope_base=ExecutionScopeBase(ROLLBACK_SESSION, 2),
                )
            flee_kinds = [entry.kind for log in flee_logs for entry in log.entries]
            self.assertIn("disengage_attempt", flee_kinds)
            self.assertNotIn("damage", flee_kinds)
            self.assertEqual(_stored(self.weak, "hp"), before_weak)
            # Non-monster delegation is untouched by the mode: an entity with no
            # threat tier still reaches the shared default policy, unchanged.
            sentinel = ActionRequest(
                actor=self.weak,
                skill_key=BASIC_ATTACK_KEY,
                targets=[self.monster],
                context=BattlefieldActionContext(self.field),
            )
            with patch.object(
                behaviour.combat, "default_attack_policy", return_value=sentinel
            ) as delegated_policy:
                delegated = monster_behaviour_policy(self.weak, self.field)
            delegated_policy.assert_called_once()
            self.assertIs(delegated, sentinel)

    @covers_requirement("monster-ai-rollout::legacy-mode-rollback-is-demonstrated")
    def test_a_new_session_never_applies_a_fresh_disk_edit_without_a_restart(self):
        startup = behaviour.MONSTER_AI_TUNING
        loaded_rulebook = behaviour.MONSTER_BEHAVIOUR_YAML
        rollback = _legacy_edited_tuning()
        record = _record()
        self.assertEqual(startup.fingerprint, record["configuration_fingerprint"])
        self.assertNotEqual(rollback.fingerprint, startup.fingerprint)
        # The shipped rulebook still names the activated set: the rollback edit
        # is a separate on-disk change this running process does not perform.
        self.assertEqual(
            set(behaviour.MONSTER_BEHAVIOUR_YAML["variant_decision_mode"]),
            set(_activated()),
        )
        # One session really decides through the production adapter under the
        # startup tuning, so the process holds both recorded tuning and settled
        # tactical history for it.
        with (
            patch("world.rules.combat.rounds.roll_d100", return_value=95),
            patch("world.rules.combat.damage.roll_d100", return_value=95),
        ):
            logs = run_round(
                self.field,
                self._decide,
                decision_scope_base=ExecutionScopeBase(ROLLBACK_SESSION, 1),
            )
        with self.captureOnCommitCallbacks(execute=True):
            for log in logs:
                observe_action(
                    ROLLBACK_SESSION,
                    1,
                    log,
                    roster=self.field.roster,
                    battlefield=self.field,
                )
        self.assertTrue(dict(session_ai_tuning(ROLLBACK_SESSION)))
        self.assertTrue(session_observations(ROLLBACK_SESSION))
        # A NEW session in the same process loads no configuration again: it uses
        # the startup tuning this process already validated, and neither the
        # loaded rulebook nor the tuning object changes.
        new_session = construct_species_individual(
            self.variant.species_key, self.variant_key, key="rollback new session"
        )
        before_restart = record_session_ai_tuning(SESSION, new_session)
        self.assertIs(before_restart.mode, DecisionMode.UTILITY)
        self.assertEqual(before_restart.tuning_fingerprint, startup.fingerprint)
        self.assertIs(behaviour.MONSTER_AI_TUNING, startup)
        self.assertIs(behaviour.MONSTER_BEHAVIOUR_YAML, loaded_rulebook)
        # Only the restart seam -- a new process that validated and loaded the
        # edited tuning -- can produce the rolled-back decision, and that restart
        # clears the process's whole tactical state: the tuning recorded for the
        # finished sessions and their settled observation history.
        clear_session_ai_tuning()
        clear_session_memory()
        self.assertEqual(dict(session_ai_tuning(ROLLBACK_SESSION)), {})
        self.assertEqual(session_observations(ROLLBACK_SESSION), ())
        with patch.object(behaviour, "MONSTER_AI_TUNING", rollback):
            after_restart = record_session_ai_tuning(ROLLBACK_SESSION, new_session)
        self.assertIs(after_restart.mode, DecisionMode.LEGACY)
        self.assertEqual(after_restart.tuning_fingerprint, rollback.fingerprint)

    @covers_requirement("monster-ai-rollout::legacy-mode-rollback-is-demonstrated")
    def test_a_database_failure_keeps_its_own_boundary_during_rollback(self):
        rollback = _legacy_edited_tuning()
        failure = DatabaseError("stored read failed")
        with (
            patch.object(behaviour, "MONSTER_AI_TUNING", rollback),
            patch.object(behaviour.combat, "_stored_hp", side_effect=failure),
            patch.object(behaviour, "log_warn") as warning,
        ):
            with self.assertRaises(DatabaseError) as raised:
                monster_behaviour_policy(
                    self.monster, self.field, context=BattlefieldActionContext(self.field)
                )
        self.assertIs(raised.exception, failure)
        events = [call.args[0] for call in warning.call_args_list if call.args]
        self.assertNotIn("monster_ai_invalid_state", events)
        self.assertEqual(events, [])