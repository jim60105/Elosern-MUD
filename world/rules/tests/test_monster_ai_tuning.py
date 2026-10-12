"""Behavior tests for the monster AI tuning rulebook, resolution and session record.

Every fixture here is synthetic: file-local species/variant/tier rows with
invented ``t_`` keys and invented prose, and synthetic rulebook mappings built
in the test, so no shipped key, display string or catalog symbol is named.
"""

from tools.spec_traceability import covers_requirement

import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
import tempfile
from unittest.mock import patch

from evennia.objects.models import ObjectDB
from evennia.utils.test_resources import EvenniaTestCase
import yaml

from world.rules import monster_behaviour as behaviour
from world.rules.combat import Battlefield
from world.rules.combat_session.ai_tuning import (
    clear_session_ai_tuning,
    discard_session_ai_tuning,
    record_session_ai_tuning,
    session_ai_tuning,
)
from world.rules.combat_session.lifecycle import clear_session
from world.rules.combat_session.policies import _enemy_policy
from world.rules.combat_session.records import CombatSessionRecord
from world.rules.monster_behaviour import (
    AI_ALGORITHM_VERSION,
    DecisionMode,
    InvalidDecisionReason,
    MonsterBehaviourConfigError,
    UTILITY_WEIGHT_NAMES,
    _load_ai_tuning,
    _load_behaviour_profiles,
    _load_rulebook,
    monster_behaviour_policy,
    resolve_monster_ai,
)
from world.rules.monster_individual import construct_species_individual
from world.tests.synthetic_data import (
    make_monster_species,
    make_monster_tier,
    make_monster_variant,
)

from ._combat_session_helpers import open_synthetic_scope, synth_damage_skill
from .combat_fixtures import FakeEntity
from .test_monster_behaviour_policy import FakeMonster, _field

SPECIES = "t_ai_species"
OTHER_SPECIES = "t_ai_other_species"
ABSENT_SPECIES = "t_ai_absent_species"
ORDINARY = "t_ai_ordinary"
STRONGER = "t_ai_stronger"
OTHER_VARIANT = "t_ai_other_variant"
ORPHAN = "t_ai_orphan"
TIER = "t_ai_tier"
OTHER_TIER = "t_ai_other_tier"
ARCHETYPE = "t_ai_patrol"
OTHER_ARCHETYPE = "t_ai_ambush"
ABSENT_ARCHETYPE = "t_ai_absent_archetype"
SESSION = "normal:1:0"
OTHER_SESSION = "normal:2:0"
BUDGET = 256

MANDATORY_FIELDS = (
    "target_strategy",
    "skill_choice",
    "prefer_area_when_multiple_enemies",
    "flee_hp_fraction",
)
WEIGHTS = {name: 1.0 for name in UTILITY_WEIGHT_NAMES}
TIER_KEYS = {TIER, OTHER_TIER}

_TIER_ROWS = {
    TIER: make_monster_tier(TIER),
    OTHER_TIER: make_monster_tier(OTHER_TIER),
}
_SPECIES_ROWS = {
    SPECIES: make_monster_species(SPECIES, default_variant_key=ORDINARY),
    OTHER_SPECIES: make_monster_species(
        OTHER_SPECIES, default_variant_key=OTHER_VARIANT
    ),
}
_VARIANT_ROWS = {
    ORDINARY: make_monster_variant(
        ORDINARY,
        species_key=SPECIES,
        threat_tier=TIER,
        behaviour_profile_key=ARCHETYPE,
    ),
    STRONGER: make_monster_variant(
        STRONGER,
        species_key=SPECIES,
        threat_tier=OTHER_TIER,
        behaviour_profile_key=OTHER_ARCHETYPE,
    ),
    OTHER_VARIANT: make_monster_variant(
        OTHER_VARIANT,
        species_key=OTHER_SPECIES,
        threat_tier=TIER,
        behaviour_profile_key=ARCHETYPE,
    ),
}
#: A registered variant whose species relationship resolves nowhere: it can
#: never author tuning, so it pins its own archetype to legacy.
_ORPHAN_ROW = make_monster_variant(
    ORPHAN,
    species_key=ABSENT_SPECIES,
    threat_tier=TIER,
    behaviour_profile_key=ARCHETYPE,
)
#: Every registered variant whose authored binding resolves to each archetype:
#: authoring that archetype as utility obliges startup to see a validated
#: intelligence value for exactly these keys.
PATROL_VARIANTS = (ORDINARY, OTHER_VARIANT)
AMBUSH_VARIANTS = (STRONGER,)


def _intelligence(keys, value=50, **extra):
    """One complete intelligence map for the variants a case activates."""
    return {**dict.fromkeys(keys, value), **extra}


def _archetype(
    *,
    mode="legacy",
    weights=None,
    target_strategy="lowest_hp",
    skill_choice="first_owned",
    prefer_area=False,
    flee=None,
):
    """One synthetic archetype entry carrying the complete legacy contract."""
    return {
        "target_strategy": target_strategy,
        "skill_choice": skill_choice,
        "prefer_area_when_multiple_enemies": prefer_area,
        "flee_hp_fraction": flee,
        "decision_mode": mode,
        "utility_weights": dict(WEIGHTS) if weights is None else weights,
    }


def _archetypes(*, patrol=None, ambush=None):
    """Both archetype entries, each overridable, so the table stays complete."""
    return {
        ARCHETYPE: _archetype(**(patrol or {})),
        OTHER_ARCHETYPE: _archetype(
            target_strategy="highest_effective_power",
            skill_choice="highest_expected_damage",
            **(ambush or {}),
        ),
    }


def _rulebook(
    *,
    defaults=None,
    archetypes=None,
    intelligence=None,
    modes=None,
    budget=BUDGET,
):
    return {
        "tier_default_archetype": (
            {TIER: ARCHETYPE, OTHER_TIER: OTHER_ARCHETYPE}
            if defaults is None
            else defaults
        ),
        "archetypes": _archetypes() if archetypes is None else archetypes,
        "variant_intelligence": {} if intelligence is None else intelligence,
        "variant_decision_mode": {} if modes is None else modes,
        "candidate_budget": budget,
    }


def _load(rulebook, *, variants=None):
    """Load one tuned rulebook exactly as startup loads the shipped one."""
    profiles = _load_behaviour_profiles(rulebook, tiers=TIER_KEYS)
    return _load_ai_tuning(
        rulebook,
        profiles=profiles,
        species=_SPECIES_ROWS,
        variants=_VARIANT_ROWS if variants is None else variants,
    )


def _tuning(
    *,
    defaults=None,
    archetypes=None,
    intelligence=None,
    modes=None,
    budget=BUDGET,
    variants=None,
):
    """Load one synthetic tuning from an in-memory rulebook mapping."""
    return _load(
        _rulebook(
            defaults=defaults,
            archetypes=archetypes,
            intelligence=intelligence,
            modes=modes,
            budget=budget,
        ),
        variants=variants,
    )


def _tuning_from_disk(rulebook):
    """Load one tuning from a rulebook file, as a restart would read it."""
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "monster_behaviour.yaml"
        path.write_text(yaml.safe_dump(rulebook), encoding="utf-8")
        return _load(_load_rulebook(path))


class FakeAIMonster:
    """The identity and binding attributes one resolution reads."""

    def __init__(
        self,
        key,
        *,
        threat_tier=TIER,
        behaviour_tree=None,
        species_key=None,
        variant_key=None,
    ):
        self.key = key
        self.threat_tier = threat_tier
        self.behaviour_tree = behaviour_tree
        self.species_key = species_key
        self.variant_key = variant_key


#: One free single-target physical strike for the authoring decision fixtures.
_CLAW = synth_damage_skill("t_ai_claw", "合成爪擊")


class MonsterBehaviourAuthoringTests(unittest.TestCase):
    """A synthetic rulebook is the sole authority for target and skill choice."""

    def setUp(self):
        open_synthetic_scope(
            self, "skills", "elements", extra={"skills": {_CLAW.key: _CLAW}}
        )

    def _decide(self, rulebook, actor, enemies):
        profiles = _load_behaviour_profiles(rulebook, tiers=TIER_KEYS)
        with patch.multiple(
            behaviour,
            MONSTER_BEHAVIOUR_YAML=rulebook,
            BEHAVIOUR_PROFILES=profiles,
        ):
            return monster_behaviour_policy(actor, _field(actor, enemies))

    @covers_requirement(
        "monster-behaviour-profile::behaviour-parameters-are-data-driven-not-hardcoded-in-python"
    )
    def test_the_authored_tier_default_and_strategy_drive_the_decision(self):
        # Two enemies whose HP order is the reverse of their power order, so
        # the authored target strategy is observable in the chosen target.
        weak = FakeEntity(
            "t_ai_weak", hp=10, atk_phys=5, agility=5, defense=5, magic_power=5
        )
        strong = FakeEntity(
            "t_ai_strong", hp=90, atk_phys=1, agility=1, defense=1, magic_power=1
        )
        actor = FakeMonster("t_ai_actor", threat_tier=TIER, owned=[_CLAW.key])
        weakest_first = self._decide(_rulebook(), actor, [weak, strong])
        self.assertEqual(weakest_first.skill_key, _CLAW.key)
        self.assertEqual(weakest_first.targets, [weak])
        # Re-authoring the tier default alone moves the decision to the other
        # archetype's strategy: no balance authority lives in the Python.
        greatest_first = self._decide(
            _rulebook(defaults={TIER: OTHER_ARCHETYPE, OTHER_TIER: ARCHETYPE}),
            actor,
            [weak, strong],
        )
        self.assertEqual(greatest_first.targets, [strong])


class MonsterAITuningLoaderTests(unittest.TestCase):
    """Startup strictness: one malformed field must fail the load."""

    def _profiles(self, rulebook):
        return _load_behaviour_profiles(rulebook, tiers=TIER_KEYS)

    def test_each_mandatory_legacy_field_is_required(self):
        for field in MANDATORY_FIELDS:
            with self.subTest(field=field):
                # One field leaves an otherwise complete, otherwise valid table.
                complete = _archetypes()
                del complete[ARCHETYPE][field]
                with self.assertRaises(MonsterBehaviourConfigError):
                    self._profiles(_rulebook(archetypes=complete))

    def test_unknown_archetype_and_top_level_fields_are_rejected(self):
        complete = _archetypes()
        complete[ARCHETYPE]["surprise"] = 1
        with self.assertRaises(MonsterBehaviourConfigError):
            self._profiles(_rulebook(archetypes=complete))
        loaded = _tuning()
        with self.assertRaises(MonsterBehaviourConfigError):
            _load_ai_tuning(
                {**_rulebook(), "surprise": {}},
                profiles=loaded.behaviour_profiles,
                species=_SPECIES_ROWS,
                variants=_VARIANT_ROWS,
            )
        with self.assertRaises(MonsterBehaviourConfigError):
            _load_ai_tuning(
                {
                    name: value
                    for name, value in _rulebook().items()
                    if name != "candidate_budget"
                },
                profiles=loaded.behaviour_profiles,
                species=_SPECIES_ROWS,
                variants=_VARIANT_ROWS,
            )

    def test_weights_must_be_the_complete_named_schema(self):
        malformed = {
            "incomplete": {k: v for k, v in WEIGHTS.items() if k != "waste"},
            "extra": dict(WEIGHTS, surprise=1.0),
            "not-a-mapping": "heroic",
            "boolean-number": dict(WEIGHTS, damage=True),
            "negative": dict(WEIGHTS, damage=-1.0),
            "infinite": dict(WEIGHTS, damage=float("inf")),
            "not-a-number": dict(WEIGHTS, damage=float("nan")),
            "primitive-type": dict(WEIGHTS, damage="1.0"),
        }
        for label, weights in malformed.items():
            with self.subTest(case=label):
                rulebook = _rulebook(
                    archetypes=_archetypes(patrol={"weights": weights})
                )
                with self.assertRaises(MonsterBehaviourConfigError):
                    self._profiles(rulebook)

    def test_decision_mode_and_budget_are_strictly_typed(self):
        for mode in ("berserk", True, 1, None, ["legacy"]):
            with self.subTest(mode=mode):
                rulebook = _rulebook(
                    archetypes=_archetypes(patrol={"mode": mode})
                )
                with self.assertRaises(MonsterBehaviourConfigError):
                    self._profiles(rulebook)
        # An authoring that omits the optional mode is legacy, not an error.
        complete = _archetypes()
        del complete[ARCHETYPE]["decision_mode"]
        profiles = self._profiles(_rulebook(archetypes=complete))
        self.assertIs(profiles[ARCHETYPE].decision_mode, DecisionMode.LEGACY)
        for budget in (0, 4097, BUDGET * 1.0, True, "256", None):
            with self.subTest(budget=budget):
                with self.assertRaises(MonsterBehaviourConfigError):
                    _tuning(budget=budget)
        for budget in (1, 4096):
            with self.subTest(budget=budget):
                self.assertEqual(_tuning(budget=budget).candidate_budget, budget)

    def test_tier_default_mapping_must_cover_exactly_the_tier_registry(self):
        cases = {
            "missing": {TIER: ARCHETYPE},
            "extra": {
                TIER: ARCHETYPE,
                OTHER_TIER: OTHER_ARCHETYPE,
                "t_ai_third": ARCHETYPE,
            },
            "unknown-archetype": {TIER: ARCHETYPE, OTHER_TIER: ABSENT_ARCHETYPE},
        }
        for label, defaults in cases.items():
            with self.subTest(case=label):
                with self.assertRaises(MonsterBehaviourConfigError):
                    self._profiles(_rulebook(defaults=defaults))

    def test_variant_maps_require_registered_pairs_and_integers(self):
        orphaned = {**_VARIANT_ROWS, ORPHAN: _ORPHAN_ROW}
        malformed_intelligence = {
            "unregistered-key": {"t_ai_absent_variant": 50},
            "boolean": {ORDINARY: True},
            "fractional": {ORDINARY: 50.0},
            "string": {ORDINARY: "50"},
            "out-of-range-low": {ORDINARY: -1},
            "out-of-range-high": {ORDINARY: 101},
            "wrong-container": [ORDINARY],
        }
        for label, intelligence in malformed_intelligence.items():
            with self.subTest(case=label):
                with self.assertRaises(MonsterBehaviourConfigError):
                    _tuning(intelligence=intelligence)
        with self.assertRaises(MonsterBehaviourConfigError):
            _tuning(intelligence={ORPHAN: 50}, variants=orphaned)
        malformed_modes = {
            "unregistered-key": {"t_ai_absent_variant": "utility"},
            "unrecognized": {ORDINARY: "berserk"},
            "primitive-type": {ORDINARY: 1},
            "wrong-container": (ORDINARY,),
        }
        for label, modes in malformed_modes.items():
            with self.subTest(case=label):
                with self.assertRaises(MonsterBehaviourConfigError):
                    _tuning(modes=modes)
        with self.assertRaises(MonsterBehaviourConfigError):
            _tuning(modes={ORPHAN: "utility"}, variants=orphaned)

    def test_utility_activation_coverage_requires_intelligence(self):
        utility_archetypes = _archetypes(patrol={"mode": "utility"})
        with self.assertRaises(MonsterBehaviourConfigError):
            _tuning(archetypes=utility_archetypes)
        with self.assertRaises(MonsterBehaviourConfigError):
            _tuning(modes={ORDINARY: "utility"})
        # Authored coverage is accepted, and an inactive legacy value is
        # validated exactly as strictly as an active utility one.
        covered = _tuning(
            archetypes=utility_archetypes,
            intelligence=_intelligence(PATROL_VARIANTS, 90),
        )
        self.assertEqual(
            dict(covered.variant_intelligence),
            {ORDINARY: 90, OTHER_VARIANT: 90},
        )
        with self.assertRaises(MonsterBehaviourConfigError):
            _tuning(
                archetypes=utility_archetypes,
                intelligence=_intelligence(PATROL_VARIANTS, 90, **{ORDINARY: 101}),
            )
        with self.assertRaises(MonsterBehaviourConfigError):
            _tuning(intelligence={ORDINARY: 10, STRONGER: False})

    def test_a_variant_referencing_an_unknown_archetype_is_rejected(self):
        broken = dict(_VARIANT_ROWS)
        broken[ORDINARY] = make_monster_variant(
            ORDINARY,
            species_key=SPECIES,
            threat_tier=TIER,
            behaviour_profile_key=ABSENT_ARCHETYPE,
        )
        with self.assertRaises(MonsterBehaviourConfigError):
            _tuning(variants=broken)

    def test_the_optional_fields_are_additive(self):
        # A legacy archetype may stop at the four mandatory fields: no mode,
        # no weights, and the load still succeeds.
        minimal = {name: _archetype()[name] for name in MANDATORY_FIELDS}
        table = _archetypes()
        table[ARCHETYPE] = minimal
        profiles = self._profiles(_rulebook(archetypes=table))
        self.assertIs(profiles[ARCHETYPE].decision_mode, DecisionMode.LEGACY)
        self.assertIsNone(profiles[ARCHETYPE].utility_weights)
        # "Not scored yet" is a decision input of its own.
        self.assertNotEqual(
            _tuning().fingerprint, _tuning(archetypes=table).fingerprint
        )
        # Authoring that same archetype utility needs both its intelligence
        # and its weights to be usable.
        with self.assertRaises(MonsterBehaviourConfigError):
            _tuning(
                archetypes={
                    ARCHETYPE: dict(minimal, decision_mode="utility"),
                    OTHER_ARCHETYPE: _archetypes()[OTHER_ARCHETYPE],
                },
                intelligence=_intelligence(PATROL_VARIANTS, 10),
            )

    def test_malformed_key_types_and_unrepresentable_numbers_are_named(self):
        mixed = _archetypes()
        mixed[ARCHETYPE][1] = "extra"
        with self.assertRaises(MonsterBehaviourConfigError) as mixed_archetype:
            self._profiles(_rulebook(archetypes=mixed))
        self.assertIsInstance(mixed_archetype.exception, MonsterBehaviourConfigError)
        loaded = _tuning()
        with self.assertRaises(MonsterBehaviourConfigError) as mixed_top_level:
            _load_ai_tuning(
                {**_rulebook(), 1: {}},
                profiles=loaded.behaviour_profiles,
                species=_SPECIES_ROWS,
                variants=_VARIANT_ROWS,
            )
        self.assertIsInstance(
            mixed_top_level.exception, MonsterBehaviourConfigError
        )
        with self.assertRaises(MonsterBehaviourConfigError):
            self._profiles(
                _rulebook(
                    archetypes=_archetypes(
                        patrol={"weights": dict(WEIGHTS, damage=10**1000)}
                    )
                )
            )

    def test_all_legacy_tuning_loads_with_empty_variant_maps(self):
        tuning = _tuning()
        self.assertEqual(tuning.algorithm_version, AI_ALGORITHM_VERSION)
        self.assertEqual(tuning.candidate_budget, BUDGET)
        self.assertEqual(tuning.variant_intelligence, {})
        self.assertEqual(tuning.variant_decision_mode, {})
        self.assertEqual(tuning.variant_bindings, {})
        self.assertEqual(set(tuning.behaviour_profiles), set(_archetypes()))
        for profile in tuning.behaviour_profiles.values():
            self.assertIs(profile.decision_mode, DecisionMode.LEGACY)
            self.assertEqual(
                set(profile.utility_weights.as_payload()), set(UTILITY_WEIGHT_NAMES)
            )
        self.assertRegex(tuning.fingerprint, r"^[0-9a-f]{64}$")

    def test_fingerprint_is_reproducible_and_moves_with_every_input(self):
        base = _tuning().fingerprint
        self.assertEqual(base, _tuning().fingerprint)
        with patch.object(
            behaviour, "AI_ALGORITHM_VERSION", AI_ALGORITHM_VERSION + 1
        ):
            self.assertNotEqual(base, _tuning().fingerprint)
        changed = {
            "budget": _tuning(budget=BUDGET - 1),
            "weight": _tuning(
                archetypes=_archetypes(
                    patrol={"weights": dict(WEIGHTS, damage=2.0)}
                )
            ),
            "intelligence": _tuning(intelligence={ORDINARY: 10}),
            "tier-default": _tuning(
                defaults={TIER: OTHER_ARCHETYPE, OTHER_TIER: ARCHETYPE}
            ),
            "target-strategy": _tuning(
                archetypes=_archetypes(
                    patrol={"target_strategy": "highest_effective_power"}
                )
            ),
            "skill-choice": _tuning(
                archetypes=_archetypes(
                    patrol={"skill_choice": "highest_expected_damage"}
                )
            ),
            "area-preference": _tuning(
                archetypes=_archetypes(patrol={"prefer_area": True})
            ),
            "flee-threshold": _tuning(
                archetypes=_archetypes(patrol={"flee": 0.5})
            ),
        }
        for label, tuning in changed.items():
            with self.subTest(case=label):
                self.assertNotEqual(base, tuning.fingerprint)
        # The mode is an input on its own: hold the authored intelligence, the
        # budget and every other field constant.
        authored = _intelligence(PATROL_VARIANTS, 10)
        self.assertNotEqual(
            _tuning(intelligence=authored).fingerprint,
            _tuning(
                archetypes=_archetypes(patrol={"mode": "utility"}),
                intelligence=authored,
            ).fingerprint,
        )
        # A referenced variant's authored binding is a decision input, while a
        # display-only rename of that same variant is not.
        named = _tuning(modes={ORDINARY: "legacy"})
        rebinding = _tuning(
            modes={ORDINARY: "legacy"},
            variants={
                **_VARIANT_ROWS,
                ORDINARY: make_monster_variant(
                    ORDINARY,
                    species_key=SPECIES,
                    threat_tier=OTHER_TIER,
                    behaviour_profile_key=ARCHETYPE,
                ),
            },
        )
        self.assertNotEqual(named.fingerprint, rebinding.fingerprint)
        renamed = _tuning(
            modes={ORDINARY: "legacy"},
            variants={
                **_VARIANT_ROWS,
                ORDINARY: make_monster_variant(
                    ORDINARY,
                    species_key=SPECIES,
                    threat_tier=TIER,
                    behaviour_profile_key=ARCHETYPE,
                    display_name_zh="合成改名型",
                ),
            },
        )
        self.assertEqual(named.fingerprint, renamed.fingerprint)


class MonsterAIDecisionTests(unittest.TestCase):
    """Runtime resolution honours the actual binding, never a variant string."""

    def setUp(self):
        open_synthetic_scope(
            self,
            "monster_species",
            "monster_variants",
            extra={
                "monster_species": _SPECIES_ROWS,
                "monster_variants": _VARIANT_ROWS,
            },
        )

    def _resolve(self, monster, **kwargs):
        return resolve_monster_ai(monster, tuning=_tuning(**kwargs))

    def test_a_variant_override_wins_over_the_archetype_mode(self):
        paired = self._resolve(
            FakeAIMonster("t_ai_u", species_key=SPECIES, variant_key=ORDINARY),
            modes={ORDINARY: "utility"},
            intelligence={ORDINARY: 70},
        )
        self.assertIs(paired.mode, DecisionMode.UTILITY)
        self.assertEqual(paired.intelligence, 70)
        self.assertIsNone(paired.invalid_reason)
        overridden = self._resolve(
            FakeAIMonster("t_ai_l", species_key=SPECIES, variant_key=ORDINARY),
            archetypes=_archetypes(patrol={"mode": "utility"}),
            modes={ORDINARY: "legacy"},
            intelligence=_intelligence(PATROL_VARIANTS, 70),
        )
        self.assertIs(overridden.mode, DecisionMode.LEGACY)
        self.assertEqual(overridden.archetype_key, ARCHETYPE)

    def test_a_repaired_pair_is_never_trusted(self):
        # The mode map names ORDINARY, but the stored variant key now belongs
        # to another species: the override must not apply.
        repaired = self._resolve(
            FakeAIMonster(
                "t_ai_repaired", species_key=SPECIES, variant_key=OTHER_VARIANT
            ),
            modes={ORDINARY: "utility"},
            intelligence={ORDINARY: 70},
        )
        self.assertIs(repaired.mode, DecisionMode.LEGACY)
        self.assertIsNone(repaired.variant_key)
        self.assertIsNone(repaired.intelligence)

    @covers_requirement(
        "monster-behaviour-profile::monster-behaviour-tree-resolves-to-a-real-archetype-defaulting-from-threat-tier"
    )
    def test_the_actual_stored_binding_decides_the_mode(self):
        monster = FakeAIMonster(
            "t_ai_bound",
            behaviour_tree=OTHER_ARCHETYPE,
            species_key=SPECIES,
            variant_key=ORDINARY,
        )
        self.assertEqual(self._resolve(monster).archetype_key, OTHER_ARCHETYPE)
        # A repaired archetype reference is honoured rather than replaced by
        # the tier default, and resolves to a typed state instead of raising.
        monster.behaviour_tree = ABSENT_ARCHETYPE
        invalid = self._resolve(monster)
        self.assertIs(invalid.invalid_reason, InvalidDecisionReason.INVALID_BINDING)
        self.assertIsNone(invalid.mode)

    def test_utility_without_a_pair_or_intelligence_is_typed_invalid(self):
        unpaired = self._resolve(
            FakeAIMonster("t_ai_tier_only"),
            archetypes=_archetypes(patrol={"mode": "utility"}),
            intelligence=_intelligence(PATROL_VARIANTS, 50),
        )
        self.assertIs(unpaired.invalid_reason, InvalidDecisionReason.INVALID_IDENTITY)
        # The pair resolves, but a repaired binding moved the monster onto an
        # archetype authored utility while it authors no intelligence itself.
        unvalued = self._resolve(
            FakeAIMonster(
                "t_ai_unvalued",
                behaviour_tree=OTHER_ARCHETYPE,
                species_key=SPECIES,
                variant_key=ORDINARY,
            ),
            archetypes=_archetypes(ambush={"mode": "utility"}),
            intelligence=_intelligence(AMBUSH_VARIANTS, 50),
        )
        self.assertIs(
            unvalued.invalid_reason, InvalidDecisionReason.MISSING_INTELLIGENCE
        )
        # An untuned legacy variant reaches a usable decision instead.
        legacy = self._resolve(
            FakeAIMonster("t_ai_legacy", species_key=SPECIES, variant_key=ORDINARY)
        )
        self.assertIsNone(legacy.invalid_reason)
        self.assertIs(legacy.mode, DecisionMode.LEGACY)
        self.assertNotEqual(legacy, unvalued)

    def test_independent_variants_keep_their_own_intelligence(self):
        authored = {"intelligence": {ORDINARY: 80, STRONGER: 20}}
        ordinary = self._resolve(
            FakeAIMonster("t_ai_ordinary", species_key=SPECIES, variant_key=ORDINARY),
            **authored,
        )
        stronger = self._resolve(
            FakeAIMonster(
                "t_ai_stronger",
                threat_tier=OTHER_TIER,
                species_key=SPECIES,
                variant_key=STRONGER,
            ),
            **authored,
        )
        self.assertEqual(ordinary.intelligence, 80)
        self.assertEqual(stronger.intelligence, 20)
        self.assertEqual(stronger.archetype_key, OTHER_ARCHETYPE)

    def test_tier_only_and_unregistered_monsters_stay_legacy(self):
        tier_only = self._resolve(FakeAIMonster("t_ai_tier_only"))
        self.assertIs(tier_only.mode, DecisionMode.LEGACY)
        self.assertIsNone(tier_only.variant_key)
        self.assertIsNone(tier_only.intelligence)
        unregistered = self._resolve(
            FakeAIMonster(
                "t_ai_orphan", species_key=ABSENT_SPECIES, variant_key=ORPHAN
            )
        )
        self.assertIs(unregistered.mode, DecisionMode.LEGACY)
        self.assertIsNone(unregistered.variant_key)

    def test_a_non_monster_has_no_monster_resolution(self):
        classified = FakeAIMonster("t_ai_plain")
        del classified.threat_tier
        self.assertIsNone(resolve_monster_ai(classified))

    def test_a_malformed_stored_binding_is_a_typed_invalid_state(self):
        # Only the unset placeholder falls back to the tier default; a
        # repaired non-string binding is reported instead of being masked.
        for stored in (None, ""):
            with self.subTest(unset=stored):
                monster = FakeAIMonster("t_ai_unset", behaviour_tree=stored)
                self.assertEqual(self._resolve(monster).archetype_key, ARCHETYPE)
        for stored in (0, 7, [], {}, ["t_ai_patrol"]):
            with self.subTest(malformed=stored):
                monster = FakeAIMonster("t_ai_junk", behaviour_tree=stored)
                resolved = self._resolve(monster)
                self.assertIs(
                    resolved.invalid_reason,
                    InvalidDecisionReason.INVALID_BINDING,
                )


class SessionAITuningTests(unittest.TestCase):
    """One process records its startup tuning per session; a restart replaces it."""

    def setUp(self):
        clear_session_ai_tuning()
        self.addCleanup(clear_session_ai_tuning)

    def test_recording_is_keyed_by_session_and_actor(self):
        tuning = _tuning()
        first = FakeAIMonster("t_ai_first", species_key=SPECIES, variant_key=ORDINARY)
        second = FakeAIMonster(
            "t_ai_second", species_key=SPECIES, variant_key=STRONGER
        )
        record_session_ai_tuning(SESSION, first, tuning=tuning)
        record_session_ai_tuning(SESSION, second, tuning=tuning)
        self.assertEqual(
            set(session_ai_tuning(SESSION)),
            {"key:t_ai_first", "key:t_ai_second"},
        )
        self.assertEqual(session_ai_tuning(OTHER_SESSION), {})
        recorded = session_ai_tuning(SESSION)
        self.assertEqual(
            recorded["key:t_ai_first"].tuning_fingerprint, tuning.fingerprint
        )
        # The view is a copy, and the record itself is frozen: a caller can
        # never edit recorded tuning through one of its own containers.
        with self.assertRaises(FrozenInstanceError):
            recorded["key:t_ai_first"].mode = DecisionMode.UTILITY
        with self.assertRaises(TypeError):
            recorded["t_ai_first"] = recorded["key:t_ai_first"]
        self.assertEqual(len(session_ai_tuning(SESSION)), 2)

    def test_an_active_session_keeps_the_tuning_the_process_loaded(self):
        startup = behaviour.MONSTER_AI_TUNING
        monster = FakeAIMonster(
            "t_ai_active", species_key=SPECIES, variant_key=ORDINARY
        )
        record_session_ai_tuning(SESSION, monster, tuning=startup)
        # The rulebook on disk changes, but this process only ever loads the
        # tuning it started with -- and loading the edited file does not
        # replace it.
        edited = _tuning_from_disk(_rulebook(budget=BUDGET - 1))
        self.assertNotEqual(startup.fingerprint, edited.fingerprint)
        self.assertIs(behaviour.MONSTER_AI_TUNING, startup)
        self.assertEqual(
            session_ai_tuning(SESSION)["key:t_ai_active"].tuning_fingerprint,
            startup.fingerprint,
        )
        self.assertNotEqual(
            session_ai_tuning(SESSION)["key:t_ai_active"].tuning_fingerprint,
            edited.fingerprint,
        )
        # A newly started session in the same process uses the same startup
        # tuning, so a session can never adopt a disk edit without a restart.
        record_session_ai_tuning(OTHER_SESSION, FakeAIMonster("t_ai_new"))
        self.assertEqual(
            session_ai_tuning(OTHER_SESSION)["key:t_ai_new"].tuning_fingerprint,
            startup.fingerprint,
        )

    def test_a_restarted_process_reconstructs_with_the_new_startup_tuning(self):
        monster = FakeAIMonster(
            "t_ai_restart", species_key=SPECIES, variant_key=ORDINARY
        )
        record_session_ai_tuning(SESSION, monster, tuning=_tuning())
        clear_session_ai_tuning()
        self.assertEqual(session_ai_tuning(SESSION), {})
        restarted = _tuning(budget=BUDGET - 1)
        record_session_ai_tuning(SESSION, monster, tuning=restarted)
        recorded = session_ai_tuning(SESSION)["key:t_ai_restart"]
        self.assertEqual(recorded.tuning_fingerprint, restarted.fingerprint)
        self.assertIs(recorded.mode, DecisionMode.LEGACY)

    def test_recording_re_resolves_a_repaired_binding(self):
        tuning = _tuning()
        monster = FakeAIMonster(
            "t_ai_drift", species_key=SPECIES, variant_key=ORDINARY
        )
        record_session_ai_tuning(SESSION, monster, tuning=tuning)
        monster.behaviour_tree = ABSENT_ARCHETYPE
        record_session_ai_tuning(SESSION, monster, tuning=tuning)
        recorded = session_ai_tuning(SESSION)["key:t_ai_drift"]
        self.assertIs(recorded.invalid_reason, InvalidDecisionReason.INVALID_BINDING)

    def test_a_non_monster_is_not_recorded(self):
        class Plain:
            key = "t_ai_plain"

        self.assertIsNone(record_session_ai_tuning(SESSION, Plain()))
        self.assertEqual(session_ai_tuning(SESSION), {})


class MonsterAISessionBoundaryTests(EvenniaTestCase):
    """The production decision boundary records tuning and writes nothing durable."""

    def setUp(self):
        super().setUp()
        clear_session_ai_tuning()
        self.addCleanup(clear_session_ai_tuning)
        open_synthetic_scope(
            self,
            "monster_tiers",
            "monster_species",
            "monster_variants",
            extra={
                "monster_tiers": _TIER_ROWS,
                "monster_species": _SPECIES_ROWS,
                "monster_variants": _VARIANT_ROWS,
            },
        )
        self.rulebook = _rulebook()
        self.profiles = _load_behaviour_profiles(self.rulebook, tiers=TIER_KEYS)
        self.tuning = _load_ai_tuning(
            self.rulebook,
            profiles=self.profiles,
            species=_SPECIES_ROWS,
            variants=_VARIANT_ROWS,
        )
        self.patches = patch.multiple(
            behaviour,
            MONSTER_BEHAVIOUR_YAML=self.rulebook,
            BEHAVIOUR_PROFILES=self.profiles,
            MONSTER_AI_TUNING=self.tuning,
        )
        self.patches.start()
        self.addCleanup(self.patches.stop)
        self.monster = construct_species_individual(
            SPECIES, ORDINARY, key="t_ai_boundary"
        )
        self.opponent = construct_species_individual(
            OTHER_SPECIES, OTHER_VARIANT, key="t_ai_opponent"
        )

    def _battlefield(self):
        return Battlefield(
            {
                "monsters": frozenset({str(self.monster.key)}),
                "party": frozenset({str(self.opponent.key)}),
            },
            {
                str(self.monster.key): self.monster,
                str(self.opponent.key): self.opponent,
            },
        )

    def _record(self, session_id):
        return record_session_ai_tuning(
            session_id, self.monster, tuning=self.tuning
        )

    def test_recording_resolves_the_constructed_monster_and_stores_nothing(self):
        attributes_before = {
            str(item.key): item.value for item in self.monster.attributes.all()
        }
        rows_before = ObjectDB.objects.count()
        recorded = self._record(SESSION)
        self.assertEqual(recorded.tuning_fingerprint, self.tuning.fingerprint)
        self.assertIs(recorded.mode, DecisionMode.LEGACY)
        self.assertEqual(recorded.variant_key, ORDINARY)
        self.assertIsNone(recorded.invalid_reason)
        self.assertEqual(ObjectDB.objects.count(), rows_before)
        self.assertEqual(
            {str(item.key): item.value for item in self.monster.attributes.all()},
            attributes_before,
        )
        self.assertEqual(self.monster.species_key, SPECIES)
        self.assertEqual(self.monster.variant_key, ORDINARY)
        self.assertEqual(self.monster.threat_tier, TIER)
        self.assertEqual(self.monster.db.behaviour_tree, ARCHETYPE)
        self.assertIsNone(getattr(self.monster, "intelligence", None))
        self.assertNotIn(
            "intelligence",
            {field.name for field in type(self.monster)._meta.get_fields()},
        )

    def test_the_production_enemy_policy_records_the_same_tuning(self):
        record = CombatSessionRecord(
            session_id=SESSION,
            mode="normal",
            room_id=0,
            player_ids=(),
            enemy_ids=(),
            fled_ids=(),
            knocked_out_ids=(),
            rounds_elapsed=0,
            exam_id=None,
        )
        battlefield = self._battlefield()
        _enemy_policy(self.monster, battlefield, record)
        recorded = session_ai_tuning(SESSION)
        self.assertEqual(
            recorded[f"dbref:{self.monster.pk}"].tuning_fingerprint,
            self.tuning.fingerprint,
        )
        self.assertEqual(
            recorded[f"dbref:{self.monster.pk}"],
            resolve_monster_ai(self.monster, tuning=self.tuning),
        )

    def test_a_repaired_stored_binding_is_read_in_place(self):
        self.monster.db.behaviour_tree = 7
        recorded = self._record(SESSION)
        self.assertIs(
            recorded.invalid_reason, InvalidDecisionReason.INVALID_BINDING
        )
        self.assertEqual(self.monster.db.behaviour_tree, 7)

    def test_terminal_cleanup_drops_only_its_own_session(self):
        record = CombatSessionRecord(
            session_id=SESSION,
            mode="normal",
            room_id=0,
            player_ids=(),
            enemy_ids=(),
            fled_ids=(),
            knocked_out_ids=(),
            rounds_elapsed=0,
            exam_id=None,
        )
        self._record(SESSION)
        record_session_ai_tuning(
            OTHER_SESSION, self.opponent, tuning=self.tuning
        )
        clear_session(self.monster, None, record)
        self.assertEqual(session_ai_tuning(SESSION), {})
        self.assertTrue(session_ai_tuning(OTHER_SESSION))
        discard_session_ai_tuning(OTHER_SESSION)
        self.assertEqual(session_ai_tuning(OTHER_SESSION), {})
