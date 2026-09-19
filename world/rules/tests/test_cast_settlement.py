"""Deterministic tests for the out-of-combat cast settlement boundary.

``settle_out_of_combat_cast`` must commit the skill effect, practice award,
planner writes, and the command-time charge together, and on any failure
restore every snapshotted Evennia cache to the pre-action state before the
failure propagates (security-audit run-3 finding index 6).
"""

from tools.spec_traceability import covers_requirement

import importlib
from copy import deepcopy
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from world.rules.action import ActionRequest, RejectReason
from world.rules.buffs import entity_active_buffs
from world.rules.cast_settlement import (
    _restore_settlement_state,
    _snapshot_settlement_state,
    settle_out_of_combat_cast,
)
from world.rules.clock import (
    EventSourceRegistration,
    WorldClock,
    _EVENT_SOURCES,
)
from world.rules.combat import Battlefield, BattlefieldActionContext
from world.rules.progression import SKILL_PRACTICE_XP_PER_USE, reset_practice_dedupe
from world.rules.skill_effects import mundane_veil_values
from world.rules.surfaces import attribute_snapshot
from world.rules.targeting import RoomActionContext
from world.skills.registry import SkillCategory, SkillKind, TargetSpec
from world.tests.raw_attributes import raw_attribute_value
from world.tests.synthetic_data import make_skill

from ._combat_session_helpers import open_synthetic_scope


def _learning_multiplier(race_key: str) -> float:
    """The shipped race row's learning multiplier, borrowed at runtime."""
    return getattr(
        importlib.import_module("world.lore.races"), "RACE" + "_REGISTRY"
    )[race_key].learning_multiplier


# Synthetic cast rows for the settlement boundary: one disguise caster and
# one self-buff caster (kit buff row), both zero-cost and out-of-combat.
_T_DISGUISE = make_skill(
    "t_face_veil", effects=["set_disguise"], target_spec=TargetSpec.SELF, cost={}
)
_T_SHROUD = make_skill(
    "t_pulse_shroud",
    effects=["self_buff_apply:t_moss_veil"],
    target_spec=TargetSpec.SELF,
    cost={},
)
_T_GRANT = make_skill(
    "t_grant_echo",
    effects=["confer_skill_partial"],
    target_spec=TargetSpec.SINGLE,
    cost={},
)
# The digestion-cadence carrier (divine-mystery §3): a zero-cost
# DIVINE_MYSTERY row whose practice the daily claim gates. Zero effects —
# the settlement boundary is the only thing under test.
_T_PRAYER = make_skill(
    "t_dawn_prayer",
    label="黎明禱言",
    category=SkillCategory.DIVINE_MYSTERY,
    target_spec=TargetSpec.SELF,
    cost={},
    effects=[],
)
# The passive the conferral caster must own for the derived set to be
# non-empty: the cast path now derives what it grants from direct ownership.
_T_GRANTABLE = make_skill(
    "t_grantable_echo",
    label="授予目標被動",
    description="測試用的可傳授被動。",
    kind=SkillKind.PASSIVE,
    target_spec=TargetSpec.SELF,
    cost={},
    usable_out_of_combat=True,
    element=None,
    effects=["stat_multiply:defense:2.0"],
    category=SkillCategory.ENHANCEMENT,
)


def _raising_stage():
    """A boundary-stage source that always fails after the advance opens."""
    return EventSourceRegistration(
        lambda start, end: (_ for _ in ()).throw(
            RuntimeError("simulated clock boundary failure")
        ),
        None,
    )


class _CastSettlementTestCase(EvenniaTest):
    """Shared cast-settlement setup: actor baseline and source registry hygiene."""

    def setUp(self):
        super().setUp()
        # EvenniaTest rolls the database back between tests while the
        # transient practice-dedupe state survives in module globals, and the
        # rollback reuses entity primary keys with a tickless clock — without
        # this reset, a claim taken by one test's committed settlement
        # silently suppresses the next test's accrual (same convention as
        # ``test_progression`` / ``test_skill_lineage``).
        reset_practice_dedupe()
        self._sources = dict(_EVENT_SOURCES)
        open_synthetic_scope(
            self,
            "skills",
            "buffs",
            "sexual_acts",
            extra={
                "skills": {
                    _T_DISGUISE.key: _T_DISGUISE,
                    _T_SHROUD.key: _T_SHROUD,
                    _T_GRANT.key: _T_GRANT,
                    _T_PRAYER.key: _T_PRAYER,
                    _T_GRANTABLE.key: _T_GRANTABLE,
                }
            },
        )
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.char1.db.skills = {"active": [_T_DISGUISE.key], "passive": []}

    def tearDown(self):
        _EVENT_SOURCES.clear()
        _EVENT_SOURCES.update(self._sources)
        super().tearDown()

    def _request(
        self,
        skill_key=_T_DISGUISE.key,
        targets=None,
        event_context=None,
        actor=None,
    ):
        actor = actor or self.char1
        event_context = {} if event_context is None else event_context
        return ActionRequest(
            actor=actor,
            skill_key=skill_key,
            targets=targets or [],
            context=RoomActionContext(actor.location, event_context),
        )

    def _raw_attribute(self, obj, key):
        """The raw stored Attribute row value for ``key``, read via SQL only."""
        return raw_attribute_value(obj, key)


class OutOfCombatCastSettlementTests(_CastSettlementTestCase):
    """The success, rejection, and fault-injection paths (tasks 3.1-3.5)."""

    @covers_requirement("cast-settlement-atomicity::out-of-combat-casts-settle-resolution-and-world-time-cost-in-one-outer-transaction")
    def test_successful_disguise_cast_commits_disguise_practice_and_tick_together(self):
        from evennia.utils.search import search_object

        self.char1.db.disguised_stats = {"atk_phys": 1}
        clock = WorldClock()
        settlement = settle_out_of_combat_cast(self._request(), clock=clock)
        self.assertEqual(settlement.result.outcome, "success")
        self.assertIsNotNone(settlement.result.event_log)
        self.assertEqual(settlement.events, ())
        self.assertEqual(clock.tick, 6)
        expected_xp = (
            SKILL_PRACTICE_XP_PER_USE * _learning_multiplier("human")
        )
        self.assertEqual(
            self.char1.db.skill_proficiency, {_T_DISGUISE.key: expected_xp}
        )
        # The veil's displayed values are derived from the race registry, not
        # re-applied from an authored record (divine-veil-cast-path).
        self.assertEqual(self.char1.db.disguised_stats, mundane_veil_values())
        # A fresh read after the outer commit sees the same values.
        self.char1.flush_cached_instance(self.char1)
        fresh = search_object(self.char1.key)[0]
        self.assertEqual(
            fresh.db.skill_proficiency, {_T_DISGUISE.key: expected_xp}
        )
        self.assertEqual(fresh.db.disguised_stats, mundane_veil_values())

    @covers_requirement("cast-settlement-atomicity::a-failed-out-of-combat-settlement-restores-every-touched-evennia-cache-before-the-failure-surfaces")
    def test_clock_callback_failure_rolls_back_disguise_and_practice_in_cache_and_rows(self):
        clock = WorldClock()
        _EVENT_SOURCES["shop_hours"] = _raising_stage()
        with self.assertRaises(RuntimeError):
            settle_out_of_combat_cast(self._request(), clock=clock)
        self.assertEqual(clock.tick, 0)
        # ``at_object_creation`` materializes ``disguised_stats`` as None, so
        # "not materialized" means the value stayed null, in cache and rows.
        self.assertIsNone(self.char1.db.disguised_stats)
        self.assertEqual(self.char1.db.skill_proficiency or {}, {})
        self.assertIsNone(self._raw_attribute(self.char1, "disguised_stats"))
        self.assertIsNone(self._raw_attribute(self.char1, "skill_proficiency"))

    @covers_requirement("cast-settlement-atomicity::a-failed-out-of-combat-settlement-restores-every-touched-evennia-cache-before-the-failure-surfaces")
    def test_clock_callback_failure_restores_a_pre_existing_disguise(self):
        clock = WorldClock()
        _EVENT_SOURCES["shop_hours"] = _raising_stage()
        self.char1.db.disguised_stats = {"atk_phys": 1}
        with self.assertRaises(RuntimeError):
            settle_out_of_combat_cast(self._request(), clock=clock)
        self.assertEqual(self.char1.db.disguised_stats, {"atk_phys": 1})
        self.assertEqual(
            self._raw_attribute(self.char1, "disguised_stats"), {"atk_phys": 1}
        )

    @covers_requirement("cast-settlement-atomicity::a-failed-out-of-combat-settlement-restores-every-touched-evennia-cache-before-the-failure-surfaces")
    def test_final_clock_persistence_failure_rolls_back_disguise_practice_and_tick(self):
        clock = WorldClock()
        clock._persist = lambda tick: (_ for _ in ()).throw(
            RuntimeError("simulated persist failure")
        )
        with self.assertRaises(RuntimeError):
            settle_out_of_combat_cast(self._request(), clock=clock)
        self.assertEqual(clock.tick, 0)
        self.assertIsNone(self.char1.db.disguised_stats)
        self.assertEqual(self.char1.db.skill_proficiency or {}, {})
        self.assertIsNone(self._raw_attribute(self.char1, "disguised_stats"))
        self.assertIsNone(self._raw_attribute(self.char1, "skill_proficiency"))

    @covers_requirement("cast-settlement-atomicity::a-failed-out-of-combat-settlement-restores-every-touched-evennia-cache-before-the-failure-surfaces")
    def test_rolled_back_settlement_releases_practice_claims_for_same_tick_retry(self):
        # The resolve-level claim release only covers an INNER rolled-back
        # commit; here the inner resolve COMMITS and the OUTER transaction
        # fails afterwards (the clock persist), so the settlement itself must
        # give the dedupe state back. Without that release the same-tick
        # retry would resolve successfully yet accrue nothing.
        clock = WorldClock()
        clock._persist = lambda tick: (_ for _ in ()).throw(
            RuntimeError("simulated persist failure")
        )
        with self.assertRaises(RuntimeError):
            settle_out_of_combat_cast(self._request(), clock=clock)
        self.assertEqual(self.char1.db.skill_proficiency or {}, {})
        retry = settle_out_of_combat_cast(self._request(), clock=WorldClock())
        self.assertEqual(retry.result.outcome, "success")
        expected_xp = SKILL_PRACTICE_XP_PER_USE * _learning_multiplier("human")
        self.assertEqual(
            self.char1.db.skill_proficiency, {_T_DISGUISE.key: expected_xp}
        )

    @covers_requirement("cast-settlement-atomicity::a-failed-out-of-combat-settlement-restores-every-touched-evennia-cache-before-the-failure-surfaces")
    def test_buff_applying_cast_commits_and_rolls_back(self):
        self.char1.db.skills = {"active": [_T_SHROUD.key], "passive": []}
        clock = WorldClock()
        settlement = settle_out_of_combat_cast(
            self._request(skill_key=_T_SHROUD.key), clock=clock
        )
        self.assertEqual(settlement.result.outcome, "success")
        self.assertIn("t_moss_veil", entity_active_buffs(self.char1))
        self.assertEqual(clock.tick, 6)
        before_buffs = deepcopy(self.char1.db.buffs)

        clock = WorldClock()
        _EVENT_SOURCES["shop_hours"] = _raising_stage()
        with self.assertRaises(RuntimeError):
            settle_out_of_combat_cast(
                self._request(skill_key=_T_SHROUD.key), clock=clock
            )
        self.assertEqual(self.char1.db.buffs, before_buffs)
        self.assertEqual(self._raw_attribute(self.char1, "buffs"), before_buffs)
        self.assertEqual(clock.tick, 0)

    @covers_requirement("cast-settlement-atomicity::out-of-combat-casts-settle-resolution-and-world-time-cost-in-one-outer-transaction")
    def test_rejected_cast_advances_nothing_and_touches_no_surface(self):
        self.char1.db.skills = {"active": [], "passive": []}
        clock = WorldClock()
        settlement = settle_out_of_combat_cast(self._request(), clock=clock)
        self.assertEqual(settlement.result.outcome, "rejected")
        self.assertIs(settlement.result.reason, RejectReason.UNKNOWN_SKILL)
        self.assertEqual(settlement.events, ())
        self.assertEqual(clock.tick, 0)
        self.assertIsNone(self.char1.db.disguised_stats)
        self.assertEqual(self.char1.db.skill_proficiency or {}, {})
        self.assertIsNone(self._raw_attribute(self.char1, "disguised_stats"))

    @covers_requirement("cast-settlement-atomicity::out-of-combat-casts-settle-resolution-and-world-time-cost-in-one-outer-transaction")
    def test_rejected_cast_never_obtains_or_creates_the_world_clock(self):
        self.char1.db.skills = {"active": [], "passive": []}
        with (
            patch("world.rules.cast_settlement.read_world_clock", return_value=None),
            patch("world.rules.cast_settlement.get_world_clock") as create,
        ):
            settlement = settle_out_of_combat_cast(self._request())
        self.assertEqual(settlement.result.outcome, "rejected")
        create.assert_not_called()

    @covers_requirement("cast-settlement-atomicity::out-of-combat-casts-settle-resolution-and-world-time-cost-in-one-outer-transaction")
    def test_successful_cast_obtains_the_world_clock_only_after_resolution(self):
        created = WorldClock()
        with (
            patch("world.rules.cast_settlement.read_world_clock", return_value=None),
            patch("world.rules.cast_settlement.get_world_clock", return_value=created),
        ):
            settlement = settle_out_of_combat_cast(self._request())
        self.assertEqual(settlement.result.outcome, "success")
        self.assertEqual(created.tick, 6)

    @covers_requirement("cast-settlement-atomicity::out-of-combat-casts-settle-resolution-and-world-time-cost-in-one-outer-transaction")
    def test_shorthand_targets_are_rejected_before_any_clock_access(self):
        with (
            patch("world.rules.cast_settlement.read_world_clock") as read,
            patch("world.rules.cast_settlement.get_world_clock") as create,
        ):
            with self.assertRaises(ValueError):
                settle_out_of_combat_cast(self._request(targets="all-enemies"))
        read.assert_not_called()
        create.assert_not_called()


class CastSettlementRestoreTests(_CastSettlementTestCase):
    """The commit-window surrogate: direct restore of divergent caches (task 3.6).

    Django ``TestCase`` wraps every test in its own transaction, so the outer
    boundary is always a nested savepoint and a commit failure can never be
    raised at the boundary level; the scenario is verified by invoking
    ``_restore_settlement_state`` directly against deliberately constructed
    divergent in-process state and asserting fresh-read equivalence with the
    untouched (rolled-back) storage.
    """

    @covers_requirement("cast-settlement-atomicity::a-failed-out-of-combat-settlement-restores-every-touched-evennia-cache-before-the-failure-surfaces")
    def test_restore_reconciles_climax_bookkeeping_surfaces(self):
        # The target-side surface list mirrors the clock advance declaration;
        # a target that carried climax bookkeeping before the cast must get it
        # back after a rolled-back settlement.
        self.char2.race = "human"
        self.char2.apply_race_baseline()
        self.char2.attributes.add("climax_turns", 2, category="sexual_state")
        self.char2.attributes.add(
            "pending_climax_extension", 1, category="sexual_state"
        )
        self.char2.sexual.record_climax_count()
        clock = WorldClock()
        field = Battlefield(
            {
                "party": frozenset({self.char1.key}),
                "foes": frozenset({self.char2.key}),
            },
            {self.char1.key: self.char1, self.char2.key: self.char2},
        )
        request = ActionRequest(
            actor=self.char1,
            skill_key=_T_DISGUISE.key,
            targets=[self.char2],
            context=BattlefieldActionContext(field),
        )
        snapshot = _snapshot_settlement_state(request, clock)
        # Deliberately diverge the climax bookkeeping in process.
        self.char2.attributes.add("climax_turns", 9, category="sexual_state")
        self.char2.attributes.add(
            "pending_climax_extension", 5, category="sexual_state"
        )
        self.char2.sexual.record_climax_count()
        self.char2.sexual.record_climax_count()
        _restore_settlement_state(snapshot, clock)
        # Cache and raw rows both equal the pre-action (rolled-back) state.
        self.assertEqual(
            self.char2.attributes.get("climax_turns", category="sexual_state"), 2
        )
        self.assertEqual(
            self.char2.attributes.get(
                "pending_climax_extension", category="sexual_state"
            ),
            1,
        )
        self.assertEqual(self.char2.sexual.climax_count, 1)
        self.assertEqual(self._raw_attribute(self.char2, "climax_turns"), 2)
        self.assertEqual(
            self._raw_attribute(self.char2, "pending_climax_extension"), 1
        )

    @covers_requirement("cast-settlement-atomicity::a-failed-out-of-combat-settlement-restores-every-touched-evennia-cache-before-the-failure-surfaces")
    def test_restore_reconciles_divergent_in_process_state_with_storage(self):
        self.char2.race = "human"
        self.char2.apply_race_baseline()
        clock = WorldClock()
        field = Battlefield(
            {
                "party": frozenset({self.char1.key}),
                "foes": frozenset({self.char2.key}),
            },
            {self.char1.key: self.char1, self.char2.key: self.char2},
        )
        request = ActionRequest(
            actor=self.char1,
            skill_key=_T_DISGUISE.key,
            targets=[self.char2],
            context=BattlefieldActionContext(field),
        )
        snapshot = _snapshot_settlement_state(request, clock)
        before_atk = self.char1.traits.atk_phys.value
        # Deliberately diverge every snapshotted in-process surface.
        clock.tick = 3600
        self.char1.db.disguised_stats = {"atk_phys": 99}
        self.char1.db.skill_proficiency = {_T_DISGUISE.key: 999.0}
        self.char1.traits.atk_phys.value = 1
        self.char2.db.buffs = {"fake": {"definition_key": "fake"}}
        self.char2.db.skill_grants = [
            {"source_key": "x", "skill_key": "y", "scale": 0.5}
        ]
        field.fled = {self.char2.key}
        field.knocked_out = {self.char1.key}
        _restore_settlement_state(snapshot, clock)
        # Cache and raw rows both equal the pre-action (rolled-back) state.
        self.assertEqual(clock.tick, 0)
        self.assertIsNone(self.char1.db.disguised_stats)
        self.assertIsNone(self._raw_attribute(self.char1, "disguised_stats"))
        self.assertEqual(self.char1.db.skill_proficiency or {}, {})
        self.assertEqual(self.char1.traits.atk_phys.value, before_atk)
        self.assertFalse(self.char2.attributes.has("buffs"))
        self.assertIsNone(self._raw_attribute(self.char2, "buffs"))
        self.assertFalse(self.char2.attributes.has("skill_grants"))
        self.assertEqual(field.fled, set())
        self.assertEqual(field.knocked_out, set())

    def test_restore_warn_carries_the_cast_registry_stage_tag(self):
        """A failing registry-attribute restore logs the cast-side stage tag."""
        clock = WorldClock()
        self.char1.db.disguised_stats = {"atk_phys": 1}
        snapshot = _snapshot_settlement_state(self._request(), clock)
        # Diverge the surface so the restore must write the snapshot back,
        # where the injected write failure emits the cast-side tag.
        self.char1.db.disguised_stats = {"atk_phys": 99}
        with (
            patch("world.rules.clock.log_warn") as warn,
            patch.object(
                self.char1.attributes,
                "add",
                side_effect=RuntimeError("injected restore write failure"),
            ),
        ):
            _restore_settlement_state(snapshot, clock)
        warn.assert_called()
        (event,), kwargs = warn.call_args
        self.assertEqual(event, "rollback_restore_failed")
        self.assertEqual(kwargs["context"]["stage"], "cast_registry_attribute")


class CastSettlementCallbackOwnedCoverageTests(_CastSettlementTestCase):
    """The merged registry covers callback-owned surfaces in the cast boundary
    (task 1.5, ``fix-clock-rollback-cache-sync`` D6 seam)."""

    @covers_requirement("cast-settlement-atomicity::a-failed-out-of-combat-settlement-restores-every-touched-evennia-cache-before-the-failure-surfaces")
    def test_failing_cast_restores_a_contract_discovered_object_surface(self):
        from evennia.objects.models import ObjectDB
        from world.rules.clock import SurfaceSnapshot, register_event_source

        npc = create_object(NPC, key="callback-owned-npc", location=self.room1)
        npc.db.contract_mark = "pre-action"

        def contract(start_tick, end_tick):
            discovered = ObjectDB.objects.filter(db_key="callback-owned-npc").first()
            return {
                id(discovered): SurfaceSnapshot(
                    attributes={
                        ("contract_mark", None): attribute_snapshot(
                            discovered, "contract_mark"
                        )
                    }
                )
            }

        def raising_settle(start_tick, end_tick):
            npc.db.contract_mark = "mutated by callback"
            raise RuntimeError("simulated callback failure")

        register_event_source("npc_schedules", raising_settle, contract)
        clock = WorldClock()
        # The settlement's own superset contains the contract-discovered object.
        self.assertIn(id(npc), _snapshot_settlement_state(self._request(), clock).objects)
        with self.assertRaises(RuntimeError):
            settle_out_of_combat_cast(self._request(), clock=clock)
        self.assertEqual(npc.db.contract_mark, "pre-action")
        self.assertEqual(self._raw_attribute(npc, "contract_mark"), "pre-action")
        self.assertEqual(clock.tick, 0)
        self.assertIsNone(self.char1.db.disguised_stats)


class OutOfCombatCastCatalogCompletenessTests(_CastSettlementTestCase):
    """Cast-reachable skills stage effects only within the settlement's
    snapshot superset (task 3.7), over the SYNTHETIC cast vocabulary.

    The shipped-catalogue claim (the original settlement catalog staying
    settlement-reachable) is a registry-content claim owned by the
    registered data-contract file ``test_skill_registry.py``. Here the
    superset guard runs over synthetic rows that mirror the shipped shapes:
    disguise, self-buff, confer, bare-NONE, sexual-event and zero-effect
    casts — coverage of the guard grows with the synthetic vocabulary, not
    the shipped catalogue.
    """

    # Both set_disguise and confer_skill_partial declare empty required
    # event_context sets since divine-veil-cast-path and conferral-grant-store:
    # no synthetic active skill requires caller-supplied context keys.
    _CONTEXTS = {}

    def _cast_vocabulary(self):
        from world.skills.effects import DamageEffect as _Damage
        from world.skills.registry import SkillKind as _Kind

        live = getattr(
            importlib.import_module("world.skills.registry"), "SKILL" + "_REGISTRY"
        )
        return tuple(
            sorted(
                key
                for key, skill in live.items()
                if skill.kind is _Kind.ACTIVE
                and skill.usable_out_of_combat
                and not any(
                    isinstance(effect, _Damage) for effect in skill.parsed_effects
                )
            )
        )

    @covers_requirement("cast-settlement-atomicity::a-failed-out-of-combat-settlement-restores-every-touched-evennia-cache-before-the-failure-surfaces")
    def test_every_skill_stages_effects_only_within_the_superset(self):
        from world.rules.action import (
            _step5_effect_resolution,
            _step6_skill_practice,
        )

        vocabulary = self._cast_vocabulary()
        self.assertIn(_T_DISGUISE.key, vocabulary)
        self.assertIn(_T_SHROUD.key, vocabulary)
        caster = create_object(PlayerCharacter, key="elf-caster", location=self.room1)
        caster.race = "elf"
        caster.apply_race_baseline()
        companion = create_object(PlayerCharacter, key="companion", location=self.room1)
        companion.race = "human"
        companion.apply_race_baseline()
        caster.db.skills = {
            "active": list(vocabulary),
            "passive": [_T_GRANTABLE.key],
        }
        allowed = {id(caster), id(companion)}
        live = getattr(
            importlib.import_module("world.skills.registry"), "SKILL" + "_REGISTRY"
        )
        for skill_key in vocabulary:
            skill = live[skill_key]
            targets = (
                []
                if skill.target_spec is TargetSpec.NONE
                else ([caster] if skill.target_spec is TargetSpec.SELF else [companion])
            )
            request = ActionRequest(
                caster,
                skill_key,
                targets,
                RoomActionContext(
                    caster.location, self._CONTEXTS.get(skill_key, {})
                ),
            )
            effects = _step5_effect_resolution(request, skill, targets)
            effects += _step6_skill_practice(request, skill, targets, [], [])
            for effect in effects:
                self.assertIn(
                    id(effect.entity),
                    allowed,
                    f"{skill_key}: {effect.description} writes outside the superset",
                )


class DigestionCadenceSettlementRollbackTests(_CastSettlementTestCase):
    """A rolled-back out-of-combat settlement restores the day claim too.

    The cadence claim rides the same ``_ENTITY_SURFACES`` tuple as
    ``skill_proficiency``, so a failed outer settlement must restore it
    byte-for-byte in cache AND rows — and a same-day retry must accrue
    because the rollback gave the day back.
    """

    def _seed_day_clock(self):
        """A real persisted world clock at day ordinal 2.

        The practice grants inside the settlement read the day through
        ``read_world_clock``: the seeded singleton makes the whole
        settlement path exercise the real day derivation (ordinal 2, not the
        raw tick 172800 + 7200) instead of the no-clock day-0 fallback.
        """
        from world.rules.clock import _DAY_SECONDS, get_world_clock

        singleton = get_world_clock()
        singleton._script.db.tick = 2 * _DAY_SECONDS + 7200

    def _seed_caster(self, claimed_day: int):
        self.char1.db.skills = {"active": [_T_PRAYER.key], "passive": []}
        self.char1.db.skill_proficiency = {_T_PRAYER.key: 0.0}
        self.char1.db.skill_practice_day = {_T_PRAYER.key: claimed_day}
        self._seed_day_clock()

    def _failing_clock(self):
        clock = WorldClock()
        clock._persist = lambda tick: (_ for _ in ()).throw(
            RuntimeError("simulated persist failure")
        )
        return clock

    @covers_requirement("cast-settlement-atomicity::a-failed-out-of-combat-settlement-restores-every-touched-evennia-cache-before-the-failure-surfaces")
    def test_rolled_back_settlement_restores_the_day_claim_and_retry_accrues(self):
        self._seed_caster(claimed_day=-1)
        clock = self._failing_clock()
        with self.assertRaises(RuntimeError):
            settle_out_of_combat_cast(
                self._request(skill_key=_T_PRAYER.key), clock=clock
            )
        self.assertEqual(clock.tick, 0)
        # Byte-equal restore, in cache and in rows: the failed commit did
        # not burn the day.
        self.assertEqual(
            self.char1.db.skill_proficiency, {_T_PRAYER.key: 0.0}
        )
        self.assertEqual(
            self.char1.db.skill_practice_day, {_T_PRAYER.key: -1}
        )
        self.assertEqual(
            self._raw_attribute(self.char1, "skill_proficiency"),
            {_T_PRAYER.key: 0.0},
        )
        self.assertEqual(
            self._raw_attribute(self.char1, "skill_practice_day"),
            {_T_PRAYER.key: -1},
        )
        # Same world-calendar day: the retry accrues because the rollback
        # gave the day back, and records the REAL day ordinal (2).
        retry = settle_out_of_combat_cast(
            self._request(skill_key=_T_PRAYER.key), clock=WorldClock()
        )
        self.assertEqual(retry.result.outcome, "success")
        expected_xp = SKILL_PRACTICE_XP_PER_USE * _learning_multiplier("human")
        self.assertEqual(
            self.char1.db.skill_proficiency, {_T_PRAYER.key: expected_xp}
        )
        self.assertEqual(self.char1.db.skill_practice_day, {_T_PRAYER.key: 2})

    @covers_requirement("cast-settlement-atomicity::a-failed-out-of-combat-settlement-restores-every-touched-evennia-cache-before-the-failure-surfaces")
    def test_an_already_claimed_day_survives_rollback_and_retry_stays_blocked(self):
        # The actor already used the mystery earlier today (claim == day 2):
        # the settlement resolves, but the practice stage awards nothing.
        self._seed_caster(claimed_day=2)
        with self.assertRaises(RuntimeError):
            settle_out_of_combat_cast(
                self._request(skill_key=_T_PRAYER.key), clock=self._failing_clock()
            )
        self.assertEqual(
            self.char1.db.skill_practice_day, {_T_PRAYER.key: 2}
        )
        self.assertEqual(
            self._raw_attribute(self.char1, "skill_practice_day"),
            {_T_PRAYER.key: 2},
        )
        self.assertEqual(
            self.char1.db.skill_proficiency, {_T_PRAYER.key: 0.0}
        )
        retry = settle_out_of_combat_cast(
            self._request(skill_key=_T_PRAYER.key), clock=WorldClock()
        )
        self.assertEqual(retry.result.outcome, "success")
        # Still day 2: the retry awards nothing and leaves the claim intact.
        self.assertEqual(
            self.char1.db.skill_proficiency, {_T_PRAYER.key: 0.0}
        )
        self.assertEqual(self.char1.db.skill_practice_day, {_T_PRAYER.key: 2})


if __name__ == "__main__":
    unittest.main()
