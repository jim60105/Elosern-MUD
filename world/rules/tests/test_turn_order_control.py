"""Focused behavior tests for turn-order control mechanics (turn-order-control).

Covers:
1. BuffDefinition round_order clause:
   - Well-formed order clause loads and cycles through BuffHandler lifecycle
   - Malformed order clauses fail load closed naming the definition key
2. State reaction mark_order_op verb:
   - Well-formed mark_order_op rule loads cleanly
   - Dispatch on physical_hit applies the marker buff to event source
   - Sourceless write and dead source are silent no-ops
   - Malformed rules fail load closed naming the rule id
3. Combat modifier chance gate validation:
   - Well-formed chance rule loads cleanly
   - Malformed chance rules fail load closed naming rule id
   - Pure evaluation and preview never roll dice
4. Round loop order fold:
   - Advance to head reorders not-yet-acted tail preserving relative order
   - Retreat to tail pushes combatant behind remaining tail
   - Already-acted combatant receiving an order op is a no-op
   - Following round re-rolls initiative clean
   - Relocation never changes action count
   - Collapse same-key ops: last-applied-wins
"""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.rules.buffs import (
    BUFF_DEFINITIONS,
    BuffDefinition,
    apply_buff,
    blocks_action,
    entity_active_buffs,
    load_buff_definitions,
    tick_buffs,
)
from world.rules.combat import (
    Battlefield,
    roll_initiative,
    run_round,
)
from world.rules.combat_modifiers import (
    evaluate_combat_modifiers,
    validate_combat_modifier_rules,
)
from world.rules.rulebook.schema import Rule
from world.rules.state_reactions import (
    dispatch_outcome_reaction,
    validate_state_reaction_rules,
)
from world.rules.tests.combat_fixtures import FakeEntity


def _write_yaml(content: str) -> Path:
    handle = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    handle.write(content)
    handle.close()
    return Path(handle.name)


def _synth_order_buff(key: str, action: str) -> BuffDefinition:
    return BuffDefinition(
        key=key,
        duration=60,
        tick_interval=None,
        stacking="refresh",
        modifiers={},
        polarity="buff",
        round_order={"action": action},
    )


class OrderFoldTests(unittest.TestCase):
    """Behavior tests for the local snapshot order fold in run_round."""

    def setUp(self):
        self.fast = FakeEntity("fast", agility=30)
        self.mid = FakeEntity("mid", agility=20)
        self.slow = FakeEntity("slow", agility=10)
        self.battlefield = Battlefield(
            {"team_a": frozenset({"fast", "mid"}), "team_b": frozenset({"slow"})},
            {"fast": self.fast, "mid": self.mid, "slow": self.slow},
        )
        self.advance_def = _synth_order_buff("synth_advance", "advance_to_head")
        self.retreat_def = _synth_order_buff("synth_retreat", "retreat_to_tail")

    def _attach_marker(self, entity: FakeEntity, defn: BuffDefinition) -> None:
        BUFF_DEFINITIONS[defn.key] = defn
        if not hasattr(entity, "buffs") or not hasattr(entity.buffs, "all"):
            entity.buffs = SimpleNamespace(all={})
        entity.buffs.all[defn.key] = SimpleNamespace(
            buffkey=defn.key,
            definition_key=defn.key,
            paused=False,
            stacks=1,
            remaining_seconds=60,
        )

    def tearDown(self):
        BUFF_DEFINITIONS.pop("synth_advance", None)
        BUFF_DEFINITIONS.pop("synth_retreat", None)

    def test_advance_to_head_reorders_tail_preserving_relative_order(self):
        # Initial rolled initiative: fast, mid, slow
        # slow carries advance_to_head
        self._attach_marker(self.slow, self.advance_def)

        calls = []
        with (
            patch("world.rules.combat.roll_initiative", return_value=["fast", "mid", "slow"]),
            patch("world.rules.combat.evaluate_combat_modifiers", return_value={}),
            patch("world.rules.combat.tick_buffs"),
            patch("world.rules.combat.decay_tick"),
        ):
            run_round(self.battlefield, lambda entity, field: calls.append(entity.key) or None)

        # slow was advanced ahead of the remaining tail; fast and mid kept their relative order
        self.assertEqual(calls, ["slow", "fast", "mid"])

    def test_retreat_to_tail_pushes_combatant_behind_remaining_tail(self):
        # Initial rolled initiative: fast, mid, slow
        # fast carries retreat_to_tail
        self._attach_marker(self.fast, self.retreat_def)

        calls = []
        with (
            patch("world.rules.combat.roll_initiative", return_value=["fast", "mid", "slow"]),
            patch("world.rules.combat.evaluate_combat_modifiers", return_value={}),
            patch("world.rules.combat.tick_buffs"),
            patch("world.rules.combat.decay_tick"),
        ):
            run_round(self.battlefield, lambda entity, field: calls.append(entity.key) or None)

        # fast was pushed behind the remaining tail; mid and slow kept their relative order
        self.assertEqual(calls, ["mid", "slow", "fast"])

    def test_already_acted_key_receiving_order_op_is_noop(self):
        # fast acts first. During fast's turn, fast receives retreat_to_tail
        calls = []

        def provider(entity, field):
            calls.append(entity.key)
            if entity.key == "fast":
                self._attach_marker(self.fast, self.retreat_def)
            return None

        with (
            patch("world.rules.combat.roll_initiative", return_value=["fast", "mid", "slow"]),
            patch("world.rules.combat.evaluate_combat_modifiers", return_value={}),
            patch("world.rules.combat.tick_buffs"),
            patch("world.rules.combat.decay_tick"),
        ):
            run_round(self.battlefield, provider)

        # fast acted once, the retreat applied after fast acted was a no-op; mid and slow acted
        self.assertEqual(calls, ["fast", "mid", "slow"])

    def test_following_round_initiative_rerolls_clean(self):
        # Round 1: slow advances to head
        self._attach_marker(self.slow, self.advance_def)
        calls_r1 = []
        with (
            patch("world.rules.combat.roll_initiative", return_value=["fast", "mid", "slow"]),
            patch("world.rules.combat.evaluate_combat_modifiers", return_value={}),
            patch("world.rules.combat.tick_buffs"),
            patch("world.rules.combat.decay_tick"),
        ):
            run_round(self.battlefield, lambda entity, field: calls_r1.append(entity.key) or None)
        self.assertEqual(calls_r1, ["slow", "fast", "mid"])

        # Round 2: marker expired or cleared
        self.slow.buffs.all.clear()
        calls_r2 = []
        with (
            patch("world.rules.combat.roll_initiative", return_value=["fast", "mid", "slow"]),
            patch("world.rules.combat.evaluate_combat_modifiers", return_value={}),
            patch("world.rules.combat.tick_buffs"),
            patch("world.rules.combat.decay_tick"),
        ):
            run_round(self.battlefield, lambda entity, field: calls_r2.append(entity.key) or None)
        # Clean rolled order
        self.assertEqual(calls_r2, ["fast", "mid", "slow"])

    def test_relocation_never_changes_action_count(self):
        # fast has actions_per_turn = 2 and is retreated to tail
        self._attach_marker(self.fast, self.retreat_def)
        calls = []
        with (
            patch("world.rules.combat.roll_initiative", return_value=["fast", "mid", "slow"]),
            patch(
                "world.rules.combat.evaluate_combat_modifiers",
                side_effect=lambda entity: {"actions_per_turn": 2} if entity.key == "fast" else {},
            ),
            patch("world.rules.combat.tick_buffs"),
            patch("world.rules.combat.decay_tick"),
        ):
            run_round(self.battlefield, lambda entity, field: calls.append(entity.key) or None)

        # fast acts at tail, but still provisions exactly 2 slots
        self.assertEqual(calls, ["mid", "slow", "fast", "fast"])

    def test_same_key_ops_collapse_last_applied_wins(self):
        # Entity has both advance and retreat attached; retreat attached second (last in dict)
        BUFF_DEFINITIONS[self.advance_def.key] = self.advance_def
        BUFF_DEFINITIONS[self.retreat_def.key] = self.retreat_def
        self.fast.buffs = SimpleNamespace(all={})
        self.fast.buffs.all[self.advance_def.key] = SimpleNamespace(
            buffkey=self.advance_def.key,
            definition_key=self.advance_def.key,
            paused=False,
            stacks=1,
            remaining_seconds=60,
        )
        self.fast.buffs.all[self.retreat_def.key] = SimpleNamespace(
            buffkey=self.retreat_def.key,
            definition_key=self.retreat_def.key,
            paused=False,
            stacks=1,
            remaining_seconds=60,
        )

        calls = []
        with (
            patch("world.rules.combat.roll_initiative", return_value=["fast", "mid", "slow"]),
            patch("world.rules.combat.evaluate_combat_modifiers", return_value={}),
            patch("world.rules.combat.tick_buffs"),
            patch("world.rules.combat.decay_tick"),
        ):
            run_round(self.battlefield, lambda entity, field: calls.append(entity.key) or None)

        # Last applied was retreat_to_tail, so fast moves to tail
        self.assertEqual(calls, ["mid", "slow", "fast"])


class BuffDefinitionRoundOrderValidationTests(unittest.TestCase):
    """Load validation tests for the round_order clause on buff definitions."""

    def test_well_formed_round_order_loads_successfully(self):
        yaml_content = """
- key: synth_advance_test
  duration: 60
  stacking: refresh
  polarity: buff
  round_order:
    action: advance_to_head

- key: synth_retreat_test
  duration: 30
  stacking: refresh
  polarity: debuff
  round_order:
    action: retreat_to_tail
"""
        path = _write_yaml(yaml_content)
        try:
            defs = load_buff_definitions(path)
            self.assertIn("synth_advance_test", defs)
            self.assertEqual(
                defs["synth_advance_test"].round_order,
                {"action": "advance_to_head"},
            )
            self.assertIn("synth_retreat_test", defs)
            self.assertEqual(
                defs["synth_retreat_test"].round_order,
                {"action": "retreat_to_tail"},
            )
        finally:
            path.unlink(missing_ok=True)

    def test_malformed_round_order_fails_closed(self):
        cases = [
            ("unknown action verb", "round_order:\n    action: warp_ahead"),
            ("bare string instead of mapping", "round_order: advance_to_head"),
            ("boolean mapping", "round_order: true"),
            ("boolean action", "round_order:\n    action: true"),
            ("integer mapping", "round_order: 42"),
            ("integer action", "round_order:\n    action: 42"),
            ("extra keys in wrapper", "round_order:\n    action: advance_to_head\n    speed: 5"),
            ("empty wrapper mapping", "round_order: {}"),
        ]
        for label, snippet in cases:
            with self.subTest(label=label):
                yaml_content = f"""
- key: bad_buff_{label.replace(' ', '_')}
  duration: 60
  stacking: refresh
  polarity: buff
  {snippet}
"""
                path = _write_yaml(yaml_content)
                try:
                    with self.assertRaises(ValueError) as cm:
                        load_buff_definitions(path)
                    self.assertIn(f"bad_buff_{label.replace(' ', '_')}", str(cm.exception))
                finally:
                    path.unlink(missing_ok=True)


class BuffDefinitionRoundOrderLifecycleTests(EvenniaTestCase):
    """Lifecycle tests proving round_order buffs use ordinary BuffHandler path."""

    def _entity(self):
        entity = create_object(PlayerCharacter, key="round_order_target")
        entity.race = "human"
        entity.apply_race_baseline()
        return entity

    def test_round_order_buff_mounts_refreshes_and_expires(self):
        defn = _synth_order_buff("synth_lifecycle_buff", "advance_to_head")
        BUFF_DEFINITIONS[defn.key] = defn
        try:
            entity = self._entity()
            apply_buff(entity, defn.key)
            self.assertIn(defn.key, entity_active_buffs(entity))

            # Refresh does not duplicate
            apply_buff(entity, defn.key)
            self.assertIn(defn.key, entity_active_buffs(entity))

            # Ticking advances time and expires naturally
            tick_buffs(entity, 60)
            self.assertNotIn(defn.key, entity_active_buffs(entity))
        finally:
            BUFF_DEFINITIONS.pop(defn.key, None)


class StateReactionMarkOrderOpTests(EvenniaTestCase):
    """Validation and dispatch tests for mark_order_op state reactions."""

    def setUp(self):
        super().setUp()
        self.order_buff = _synth_order_buff("synth_retreat_reaction", "retreat_to_tail")
        BUFF_DEFINITIONS[self.order_buff.key] = self.order_buff

    def tearDown(self):
        super().tearDown()
        BUFF_DEFINITIONS.pop(self.order_buff.key, None)

    def _character(self, key: str):
        char = create_object(PlayerCharacter, key=key)
        char.race = "human"
        char.apply_race_baseline()
        return char

    def test_well_formed_mark_order_op_loads_successfully(self):
        rule = Rule(
            "r_mark_test",
            when={"event": "physical_hit"},
            then={"mark_order_op": self.order_buff.key},
        )
        validate_state_reaction_rules([rule])

    def test_mark_order_op_dispatch_marks_source(self):
        attacker = self._character("attacker")
        reactor = self._character("reactor")

        rule = Rule(
            "r_static_ward_like",
            when={"event": "physical_hit"},
            then={"mark_order_op": self.order_buff.key},
        )

        dispatch_outcome_reaction(
            reactor,
            "physical_hit",
            source=attacker,
            rules=[rule],
        )

        # Attacker received the retreat marker, attributed to reactor
        self.assertIn(self.order_buff.key, entity_active_buffs(attacker))
        self.assertNotIn(self.order_buff.key, entity_active_buffs(reactor))

    def test_sourceless_and_dead_source_are_noops(self):
        reactor = self._character("reactor_noop")
        rule = Rule(
            "r_noop_test",
            when={"event": "physical_hit"},
            then={"mark_order_op": self.order_buff.key},
        )

        # Sourceless: source=None
        dispatch_outcome_reaction(
            reactor,
            "physical_hit",
            source=None,
            rules=[rule],
        )

        # Dead source: source hp <= 0
        dead_attacker = self._character("dead_attacker")
        dead_attacker.traits.hp.base = 0
        dispatch_outcome_reaction(
            reactor,
            "physical_hit",
            source=dead_attacker,
            rules=[rule],
        )
        self.assertNotIn(self.order_buff.key, entity_active_buffs(dead_attacker))

    def test_malformed_mark_order_op_fails_load_closed(self):
        cases = [
            ("unknown buff definition", {"mark_order_op": "totally_unknown_buff"}),
            ("buff without round_order", {"mark_order_op": "t_synth_plain"}),
            ("boolean value", {"mark_order_op": True}),
            ("empty string value", {"mark_order_op": ""}),
            (
                "alongside counter_damage",
                {"mark_order_op": self.order_buff.key, "counter_damage": 0.5},
            ),
            (
                "alongside apply_buff_to_source",
                {"mark_order_op": self.order_buff.key, "apply_buff_to_source": self.order_buff.key},
            ),
        ]

        plain_buff = BuffDefinition(
            key="t_synth_plain",
            duration=60,
            tick_interval=None,
            stacking="refresh",
            modifiers={},
            polarity="buff",
        )
        BUFF_DEFINITIONS["t_synth_plain"] = plain_buff
        try:
            for label, then_clause in cases:
                with self.subTest(label=label):
                    rule = Rule(
                        f"bad_rule_{label.replace(' ', '_')}",
                        when={"event": "physical_hit"},
                        then=then_clause,
                    )
                    with self.assertRaises(ValueError) as cm:
                        validate_state_reaction_rules([rule])
                    self.assertIn(f"bad_rule_{label.replace(' ', '_')}", str(cm.exception))
        finally:
            BUFF_DEFINITIONS.pop("t_synth_plain", None)


class CombatModifierChanceValidationTests(unittest.TestCase):
    """Validation and purity tests for combat modifier chance rules."""

    def test_well_formed_chance_rule_validates(self):
        rule = Rule(
            "r_chance_valid",
            when={},
            then={"actions_per_turn": 0, "chance": 15},
        )
        validate_combat_modifier_rules([rule])

    def test_malformed_chance_rules_fail_closed(self):
        cases = [
            ("negative chance", {"actions_per_turn": 0, "chance": -1}),
            ("chance over 100", {"actions_per_turn": 0, "chance": 101}),
            ("float chance", {"actions_per_turn": 0, "chance": 15.5}),
            ("boolean chance", {"actions_per_turn": 0, "chance": True}),
            ("string chance", {"actions_per_turn": 0, "chance": "15"}),
            ("chance on positive actions_per_turn", {"actions_per_turn": 1, "chance": 15}),
            ("chance without actions_per_turn", {"chance": 15}),
            ("boolean actions_per_turn", {"actions_per_turn": False, "chance": 15}),
        ]
        for label, then_clause in cases:
            with self.subTest(label=label):
                rule = Rule(f"r_bad_{label.replace(' ', '_')}", when={}, then=then_clause)
                with self.assertRaises(ValueError) as cm:
                    validate_combat_modifier_rules([rule])
                self.assertIn(f"r_bad_{label.replace(' ', '_')}", str(cm.exception))

    def test_pure_queries_never_roll_dice(self):
        entity = FakeEntity("test_char")
        with patch("world.rules.dice.roll_d100") as mock_roll:
            evaluate_combat_modifiers(entity)
            blocks_action(entity)
        mock_roll.assert_not_called()
