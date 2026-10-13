"""Behavior tests for the decision-mode scope of the monster flee policy.

Every fixture here is file-local and synthetic: the species, variant, tier,
archetype and skill rows are built from the shared kit's factories and
templates, and the participant rows are real ``Monster``/player rows built
through the production construction entry points. No shipped key, threshold or
catalog symbol is named by a resolvable literal.

The tests establish this slice's contract: the flee threshold, the inclusive
HP boundary and the flee priority are the *legacy* body's behavior, while a
monster whose effective decision mode is ``utility`` never voluntarily flees --
it proposes its own scored selection, keeps its own no-action boundary when no
legal candidate exists, and never enumerates, scores or returns the canonical
flee key. The configured typed-invalid-state fallback keeps its own contract,
which is the one deliberate path by which a utility-mode monster still reaches
the legacy body, inclusive flee request included.
"""

from tools.spec_traceability import covers_requirement

from contextlib import contextmanager
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.rooms import Room

from world.rules import monster_behaviour as behaviour
from world.rules.combat import Battlefield
from world.rules.disengage import FLEE_SKILL_KEY
from world.rules.monster_ai import MonsterAIStateError, enumerate_candidates
from world.rules.monster_behaviour import (
    DecisionMode,
    InvalidStateFallback,
    invalid_state_fallback,
    monster_behaviour_policy,
    resolve_monster_ai,
)
from world.rules.monster_individual import construct_species_individual

from ._combat_session_helpers import _player
from .test_monster_ai_selection import (
    ARCHETYPE,
    SPECIES,
    STRIKE,
    TIER,
    VARIANT,
    SyntheticTuningMixin,
    _scope,
    _suppress_innate_skills,
)

#: The one authored maximum both cases share, so ``50/100`` is the exact
#: inclusive boundary in binary floats and needs no tolerance.
MAX_HP = 100
BOUNDARY_HP = 50

#: The single archetype both cases resolve to: identical in every authored
#: field, with a non-null threshold and a legacy declaration, so the only
#: difference between the paired monsters is the variant's mode override.
ARCHETYPE_FIELDS = {
    "target_strategy": "lowest_hp",
    "skill_choice": "first_owned",
    "prefer_area_when_multiple_enemies": False,
    "flee_hp_fraction": BOUNDARY_HP / MAX_HP,
    "decision_mode": DecisionMode.LEGACY.value,
    "utility_weights": {
        name: 1.0 for name in behaviour.UTILITY_WEIGHT_NAMES
    },
}


def _field(monster, opponent) -> Battlefield:
    """One real battlefield: the monster's team and its single living foe."""
    return Battlefield(
        {
            "foes": frozenset({str(monster.key)}),
            "party": frozenset({str(opponent.key)}),
        },
        {str(monster.key): monster, str(opponent.key): opponent},
    )


@contextmanager
def _recorded_enumerations():
    """Capture every candidate set the decision's own producer returns.

    The wrapper forwards every argument unchanged and preserves the returned
    ``CandidateSet``, so the decision behaves exactly as it does unpatched
    while the test reads the enumeration *itself* rather than the normalized
    trace projection of it.
    """
    captured = []
    producer = enumerate_candidates

    def recording(*args, **kwargs):
        result = producer(*args, **kwargs)
        captured.append(result)
        return result

    with patch("world.rules.monster_ai.enumerate_candidates", recording):
        yield captured


class FleeModeScopeTests(SyntheticTuningMixin, EvenniaTestCase):
    """The flee boundary belongs to legacy mode; utility mode never flees."""

    def setUp(self):
        _scope(self)
        super().setUp()
        self.room = create_object(Room, key="flee scope arena")
        self.opponent = _player("t_flee_scope_foe")
        self.opponent.location = self.room
        self.opponent.traits.hp.base = 200
        self.opponent.traits.hp.current = 200

    def _case(self, mode, *, hp, owned=(STRIKE.key,), innate=False):
        """Return one real monster row resolved to ``mode``, and its field.

        The tuning, the monster's own row and the resolution are all rebuilt
        per case, and the resolved mode plus a null invalid reason are asserted
        before any policy call, so a case proves it is the mode it claims
        instead of inheriting one from a fixture.
        """
        if not innate:
            _suppress_innate_skills(self)
        self.open_tuning(
            archetypes={ARCHETYPE: dict(ARCHETYPE_FIELDS)},
            modes={} if mode is DecisionMode.LEGACY else {VARIANT: mode.value},
            intelligence={VARIANT: 50},
        )
        monster = construct_species_individual(
            SPECIES, VARIANT, key=f"t_flee_scope_{mode.value}_{hp}"
        )
        monster.location = self.room
        monster.traits.hp.base = MAX_HP
        monster.traits.hp.current = hp
        monster.traits.mp.base = MAX_HP
        monster.traits.mp.current = MAX_HP
        monster.db.skills = {"active": list(owned), "passive": []}
        resolution = resolve_monster_ai(monster)
        self.assertIsNotNone(resolution)
        self.assertIs(resolution.mode, mode)
        self.assertIsNone(resolution.invalid_reason)
        return monster, _field(monster, self.opponent)

    @covers_requirement(
        "monster-flee-policy::the-policy-checks-current-to-maximum-true-hp-at-an-inclusive-boundary",
        "monster-flee-policy::utility-mode-never-voluntarily-flees",
    )
    def test_only_legacy_mode_flees_at_the_shared_authored_boundary(self):
        for mode, expected in (
            (DecisionMode.LEGACY, FLEE_SKILL_KEY),
            (DecisionMode.UTILITY, STRIKE.key),
        ):
            with self.subTest(mode=mode.value):
                monster, field = self._case(mode, hp=BOUNDARY_HP)
                trace = []
                with _recorded_enumerations() as captured:
                    request = monster_behaviour_policy(
                        monster, field, trace=trace
                    )
                self.assertIsNotNone(request)
                self.assertEqual(request.skill_key, expected)
                if mode is DecisionMode.UTILITY:
                    # The request is the scored selection the decision made,
                    # and it is never the flee key it kept out of its own
                    # candidate set.
                    self.assertNotEqual(request.skill_key, FLEE_SKILL_KEY)
                    self.assertEqual(len(captured), 1)
                    legal = {
                        item.identity.skill_key
                        for item in captured[0].candidates
                    }
                    self.assertTrue(legal)
                    recorded = trace[0]
                    self.assertGreaterEqual(recorded.candidates, 1)
                    self.assertEqual(
                        recorded.selected.skill_key, request.skill_key
                    )
                    for plan in recorded.plans:
                        self.assertIn(plan.skill_key, legal)
                # One HP above the same authored threshold: the boundary is
                # still a boundary in both modes.
                monster.traits.hp.current = BOUNDARY_HP + 1
                above = monster_behaviour_policy(monster, field)
                self.assertIsNotNone(above)
                self.assertEqual(above.skill_key, STRIKE.key)

    @covers_requirement("monster-flee-policy::utility-mode-never-voluntarily-flees")
    def test_below_the_boundary_the_utility_decision_still_scores(self):
        monster, field = self._case(DecisionMode.UTILITY, hp=1)
        first = monster_behaviour_policy(monster, field)
        self.assertIsNotNone(first)
        self.assertEqual(first.skill_key, STRIKE.key)
        self.assertNotEqual(first.skill_key, FLEE_SKILL_KEY)
        replay = monster_behaviour_policy(monster, field)
        self.assertEqual(replay.skill_key, first.skill_key)
        self.assertEqual(replay.targets, first.targets)

    @covers_requirement("monster-flee-policy::utility-mode-never-voluntarily-flees")
    def test_an_empty_utility_candidate_set_stays_no_action(self):
        for hp in (1, BOUNDARY_HP):
            with self.subTest(hp=hp):
                monster, field = self._case(
                    DecisionMode.UTILITY, hp=hp, owned=()
                )
                # The stored ownership is empty: no active row, no passive row
                # and no innate order. (``owned_keys()`` additionally appends
                # the species' unlocked sexual acts, which is a separate
                # surface and contributes no scored candidate here.)
                self.assertEqual(monster.db.skills, {"active": [], "passive": []})
                self.assertEqual(monster.skills.base_owned_keys(), [])
                with (
                    patch("world.rules.monster_behaviour.log_warn") as warning,
                    patch(
                        "world.rules.monster_behaviour._should_flee",
                        side_effect=AssertionError("the legacy flee gate ran"),
                    ),
                ):
                    request = monster_behaviour_policy(monster, field)
                # No action is the decision's own boundary: no flee request is
                # built and the legacy body is never consulted.
                self.assertIsNone(request)
                warning.assert_not_called()

    @covers_requirement("monster-flee-policy::utility-mode-never-voluntarily-flees")
    def test_the_owned_flee_key_is_no_enumerated_candidate(self):
        monster, field = self._case(DecisionMode.UTILITY, hp=MAX_HP, innate=True)
        self.assertIn(FLEE_SKILL_KEY, monster.skills.owned_keys())
        for hp in (MAX_HP, BOUNDARY_HP, BOUNDARY_HP - 1, 1):
            with self.subTest(hp=hp):
                monster.traits.hp.current = hp
                trace = []
                with _recorded_enumerations() as captured:
                    request = monster_behaviour_policy(
                        monster, field, trace=trace
                    )
                self.assertEqual(len(captured), 1)
                candidates = captured[0]
                legal = {item.identity.skill_key for item in candidates.candidates}
                for item in candidates.candidates:
                    self.assertNotEqual(item.identity.skill_key, FLEE_SKILL_KEY)
                for item in candidates.rejections:
                    self.assertNotEqual(item.identity.skill_key, FLEE_SKILL_KEY)
                for item in candidates.exclusions:
                    self.assertNotEqual(item.identity.skill_key, FLEE_SKILL_KEY)
                for item in candidates.unavailable:
                    self.assertNotEqual(item.skill_key, FLEE_SKILL_KEY)
                for plan in trace[0].plans:
                    self.assertNotEqual(plan.skill_key, FLEE_SKILL_KEY)
                    self.assertIn(plan.skill_key, legal)
                self.assertIsNotNone(request)
                self.assertNotEqual(request.skill_key, FLEE_SKILL_KEY)
                self.assertIn(request.skill_key, legal)

    @covers_requirement("monster-flee-policy::utility-mode-never-voluntarily-flees")
    def test_the_typed_invalid_state_fallback_keeps_the_legacy_body(self):
        monster, field = self._case(DecisionMode.UTILITY, hp=BOUNDARY_HP)
        self.assertIs(invalid_state_fallback(), InvalidStateFallback.LEGACY)
        with (
            patch(
                "world.rules.monster_behaviour._utility_action",
                side_effect=MonsterAIStateError("a raised utility state"),
            ),
            patch("world.rules.monster_behaviour.log_warn") as warning,
        ):
            request = monster_behaviour_policy(monster, field)
        # The fallback's legacy decision, inclusive flee request included.
        self.assertIsNotNone(request)
        self.assertEqual(request.skill_key, FLEE_SKILL_KEY)
        self.assertEqual(request.targets, [monster])
        warning.assert_called_once()
        event, = warning.call_args.args
        self.assertEqual(event, "monster_ai_invalid_state")
        self.assertEqual(
            warning.call_args.kwargs["context"]["action"],
            invalid_state_fallback().value,
        )
        self.assertIsInstance(warning.call_args.kwargs["exc"], MonsterAIStateError)