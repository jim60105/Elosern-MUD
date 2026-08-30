"""Deterministic tests for the out-of-combat cast settlement boundary.

``settle_out_of_combat_cast`` must commit the skill effect, practice award,
planner writes, and the command-time charge together, and on any failure
restore every snapshotted Evennia cache to the pre-action state before the
failure propagates (security-audit run-3 finding index 6).
"""

from tools.spec_traceability import covers_requirement

from copy import deepcopy
from dataclasses import replace
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from world.lore.races import RACE_REGISTRY
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
from world.rules.surfaces import attribute_snapshot
from world.rules.targeting import RoomActionContext
from world.skills.registry import SKILL_REGISTRY, SkillKind, TargetSpec
from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY


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
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.char1.db.skills = {"active": ["status_disguise"], "passive": []}

    def tearDown(self):
        _EVENT_SOURCES.clear()
        _EVENT_SOURCES.update(self._sources)
        super().tearDown()

    def _request(
        self,
        skill_key="status_disguise",
        targets=None,
        event_context=None,
        actor=None,
    ):
        actor = actor or self.char1
        if event_context is None:
            event_context = (
                {"disguise": dict(actor.db.disguised_stats or {})}
                if skill_key == "status_disguise"
                else {}
            )
        return ActionRequest(
            actor=actor,
            skill_key=skill_key,
            targets=targets or [],
            context=RoomActionContext(actor.location, event_context),
        )

    def _raw_attribute(self, obj, key):
        """The raw stored Attribute row value for ``key``, read via SQL only."""
        row = (
            obj.db_attributes.through.objects.filter(
                objectdb_id=obj.pk, attribute__db_key=key
            )
            .values_list("attribute__db_value", flat=True)
            .first()
        )
        return None if row is None else row


class OutOfCombatCastSettlementTests(_CastSettlementTestCase):
    """The success, rejection, and fault-injection paths (tasks 3.1-3.5)."""

    @covers_requirement("cast-settlement-atomicity::out-of-combat-casts-settle-resolution-and-world-time-cost-in-one-outer-transaction")
    def test_successful_status_disguise_cast_commits_disguise_practice_and_tick_together(self):
        from evennia.utils.search import search_object

        self.char1.db.disguised_stats = {"atk_phys": 1}
        clock = WorldClock()
        settlement = settle_out_of_combat_cast(self._request(), clock=clock)
        self.assertEqual(settlement.result.outcome, "success")
        self.assertIsNotNone(settlement.result.event_log)
        self.assertEqual(settlement.events, ())
        self.assertEqual(clock.tick, 6)
        expected_xp = (
            SKILL_PRACTICE_XP_PER_USE * RACE_REGISTRY["human"].learning_multiplier
        )
        self.assertEqual(
            self.char1.db.skill_proficiency, {"status_disguise": expected_xp}
        )
        self.assertEqual(self.char1.db.disguised_stats, {"atk_phys": 1})
        # A fresh read after the outer commit sees the same values.
        self.char1.flush_cached_instance(self.char1)
        fresh = search_object(self.char1.key)[0]
        self.assertEqual(
            fresh.db.skill_proficiency, {"status_disguise": expected_xp}
        )
        self.assertEqual(fresh.db.disguised_stats, {"atk_phys": 1})

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
        expected_xp = (
            SKILL_PRACTICE_XP_PER_USE * RACE_REGISTRY["human"].learning_multiplier
        )
        self.assertEqual(
            self.char1.db.skill_proficiency, {"status_disguise": expected_xp}
        )

    @covers_requirement("cast-settlement-atomicity::a-failed-out-of-combat-settlement-restores-every-touched-evennia-cache-before-the-failure-surfaces")
    def test_buff_applying_cast_commits_and_rolls_back(self):
        original = SKILL_REGISTRY["concentration"]
        SKILL_REGISTRY["test_self_buff"] = replace(
            original, key="test_self_buff", usable_out_of_combat=True, cost={}
        )
        try:
            self.char1.db.skills = {"active": ["test_self_buff"], "passive": []}
            clock = WorldClock()
            settlement = settle_out_of_combat_cast(
                self._request(skill_key="test_self_buff"), clock=clock
            )
            self.assertEqual(settlement.result.outcome, "success")
            self.assertIn("focus", entity_active_buffs(self.char1))
            self.assertEqual(clock.tick, 6)
            before_buffs = deepcopy(self.char1.db.buffs)

            clock = WorldClock()
            _EVENT_SOURCES["shop_hours"] = _raising_stage()
            with self.assertRaises(RuntimeError):
                settle_out_of_combat_cast(
                    self._request(skill_key="test_self_buff"), clock=clock
                )
            self.assertEqual(self.char1.db.buffs, before_buffs)
            self.assertEqual(self._raw_attribute(self.char1, "buffs"), before_buffs)
            self.assertEqual(clock.tick, 0)
        finally:
            del SKILL_REGISTRY["test_self_buff"]

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
            skill_key="status_disguise",
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
            skill_key="status_disguise",
            targets=[self.char2],
            context=BattlefieldActionContext(field),
        )
        snapshot = _snapshot_settlement_state(request, clock)
        before_atk = self.char1.traits.atk_phys.value
        # Deliberately diverge every snapshotted in-process surface.
        clock.tick = 3600
        self.char1.db.disguised_stats = {"atk_phys": 99}
        self.char1.db.skill_proficiency = {"status_disguise": 999.0}
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
    """Every ACTIVE out-of-combat catalog skill stages effects only within the
    settlement's snapshot superset (task 3.7)."""

    ACTIVE_OUT_OF_COMBAT_SKILLS = (
        "status_disguise",
        "dominion_art",
        "divine_sexual_arts",
        "divine_time_dilation",
        "divine_space_distortion",
        "divine_matter_transmutation",
        "divine_life_extension",
        *sorted(SEXUAL_ACT_REGISTRY),
    )

    def test_catalog_actives_are_exactly_the_declared_seven(self):
        actives = {
            key: skill
            for key, skill in SKILL_REGISTRY.items()
            if skill.kind is SkillKind.ACTIVE and skill.usable_out_of_combat
        }
        self.assertEqual(set(actives), set(self.ACTIVE_OUT_OF_COMBAT_SKILLS))

    @covers_requirement("cast-settlement-atomicity::a-failed-out-of-combat-settlement-restores-every-touched-evennia-cache-before-the-failure-surfaces")
    def test_every_skill_stages_effects_only_within_the_superset(self):
        from world.rules.action import (
            _step5_effect_resolution,
            _step6_skill_practice,
        )

        caster = create_object(PlayerCharacter, key="elf-caster", location=self.room1)
        caster.race = "elf"
        caster.apply_race_baseline()
        companion = create_object(PlayerCharacter, key="companion", location=self.room1)
        companion.race = "human"
        companion.apply_race_baseline()
        caster.db.skills = {
            "active": list(self.ACTIVE_OUT_OF_COMBAT_SKILLS),
            "passive": [],
        }
        contexts = {
            "status_disguise": {"disguise": {"atk_phys": 60}},
            "dominion_art": {"confer_skill_key": "body_enhancement", "confer_scale": 0.1},
            "divine_sexual_arts": {},
        }
        allowed = {id(caster), id(companion)}
        for skill_key in self.ACTIVE_OUT_OF_COMBAT_SKILLS:
            skill = SKILL_REGISTRY[skill_key]
            targets = (
                []
                if skill.target_spec is TargetSpec.NONE
                else ([caster] if skill.target_spec is TargetSpec.SELF else [companion])
            )
            request = ActionRequest(
                caster,
                skill_key,
                targets,
                RoomActionContext(caster.location, contexts.get(skill_key, {})),
            )
            effects = _step5_effect_resolution(request, skill, targets)
            effects += _step6_skill_practice(request, skill, targets, [], [])
            for effect in effects:
                self.assertIn(
                    id(effect.entity),
                    allowed,
                    f"{skill_key}: {effect.description} writes outside the superset",
                )
