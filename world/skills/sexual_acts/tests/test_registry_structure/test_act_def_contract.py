"""Slice of ``test_registry_structure``: SexualActDefContractTests, PairEventValidationTests, LineModuleTests.
"""
from tools.spec_traceability import covers_requirement
import inspect
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase
from typeclasses.characters import PlayerCharacter
from world.lore.sexual_vocab import BODY_PARTS, GENERIC_BODY_PART
from world.lore.player_presets import PLAYER_PRESET_REGISTRY
from world.rules.rulebook.schema import load_rules
from world.rules.sexual_state import _LIFETIME_COUNTER_KEYS
from world.skills import handler
from world.skills.handler import SkillHandler
from world.skills.registry import (
    SKILL_REGISTRY,
    SkillCategory,
    SkillDef,
    SkillKind,
    TargetSpec,
)
import world.skills.registry as registry_module
from world.skills import sexual_acts
import world.skills.sexual_acts._builder as _builder_module
from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY
from world.skills.effects import TargetSexualEventEffect
from world.skills.sexual_acts.divine import DIVINE_ACTS
from world.skills.sexual_acts._builder import (
    _ACTOR_SCOPED_EVENTS,
    _FORBIDDEN_SEXUAL_EVENTS,
    SexualActDef,
    _act_family,
)

from ._support import (
    check_names_resolve,
    _seed_act_row,
)

class SexualActDefContractTests(unittest.TestCase):
    """The SexualActDef field contract (design D-1)."""

    @covers_requirement("sexual-act-registry::sexualactdef-carries-exactly-the-metadata-a-sex-act-needs-beyond-skilldef")
    def test_seed_act_accepts_an_empty_unlock_mapping(self):
        act = SexualActDef(
            key="seed",
            unlock={},
            base_pleasure=10,
            actor_part="私處",
            target_part=None,
            actor_pleasure_ratio=0.5,
            actor_counters=(),
            participant_counters=(),
            sexual_events=(),
            resistible=True,
        )
        self.assertEqual(act.unlock, {})

    @covers_requirement("sexual-act-registry::sexualactdef-carries-exactly-the-metadata-a-sex-act-needs-beyond-skilldef")
    def test_unlock_mapping_is_immutable_and_detached_from_the_input(self):
        raw = {"restraint_count": 1}
        act = SexualActDef(
            key="frozen_unlock",
            unlock=raw,
            base_pleasure=10,
            actor_part="私處",
            target_part=None,
            actor_pleasure_ratio=0.5,
            actor_counters=(),
            participant_counters=(),
            sexual_events=(),
            resistible=True,
        )
        raw["restraint_count"] = 99
        self.assertEqual(act.unlock, {"restraint_count": 1})
        with self.assertRaises(TypeError):
            act.unlock["restraint_count"] = 2

    @covers_requirement("sexual-act-registry::sexualactdef-carries-exactly-the-metadata-a-sex-act-needs-beyond-skilldef")
    def test_sexualactdef_declares_no_line_field(self):
        fields = {field.name for field in SexualActDef.__dataclass_fields__.values()}
        self.assertNotIn("line", fields)
        skill, act = _seed_act_row()
        self.assertEqual(skill.group, "獨處線")
        self.assertFalse(hasattr(act, "line"))

    @covers_requirement("sexual-act-registry::every-counter-and-event-an-act-names-actually-exists-checked-across-the-whole-assembled-registry")
    def test_unrecognized_counter_name_fails_the_structural_check(self):
        bad = SexualActDef(
            key="bad_counter",
            unlock={"自慰次數": 10},
            base_pleasure=10,
            actor_part="私處",
            target_part=None,
            actor_pleasure_ratio=0.5,
            actor_counters=(),
            participant_counters=(),
            sexual_events=(),
            resistible=True,
        )
        with self.assertRaises(AssertionError) as caught:
            check_names_resolve(bad)
        self.assertIn("bad_counter", str(caught.exception))
        self.assertIn("自慰次數", str(caught.exception))

    @covers_requirement("sexual-act-registry::every-counter-and-event-an-act-names-actually-exists-checked-across-the-whole-assembled-registry")
    def test_unrecognized_event_name_fails_the_structural_check(self):
        bad = SexualActDef(
            key="bad_event",
            unlock={},
            base_pleasure=10,
            actor_part="私處",
            target_part=None,
            actor_pleasure_ratio=0.5,
            actor_counters=(),
            participant_counters=(),
            sexual_events=("a_fake_event",),
            resistible=True,
        )
        with self.assertRaises(AssertionError) as caught:
            check_names_resolve(bad)
        self.assertIn("bad_event", str(caught.exception))
        self.assertIn("a_fake_event", str(caught.exception))

    @covers_requirement("sexual-act-registry::every-counter-and-event-an-act-names-actually-exists-checked-across-the-whole-assembled-registry")
    def test_unrecognized_pair_event_name_fails_the_structural_check(self):
        bad = SexualActDef(
            key="bad_pair_event",
            unlock={},
            base_pleasure=10,
            actor_part="私處",
            target_part=None,
            actor_pleasure_ratio=0.5,
            actor_counters=(),
            participant_counters=(),
            sexual_events=(),
            resistible=True,
            pair_events=((("female", "male"), "a_fake_event"),),
        )
        with self.assertRaises(AssertionError) as caught:
            check_names_resolve(bad)
        self.assertIn("bad_pair_event", str(caught.exception))
        self.assertIn("a_fake_event", str(caught.exception))

class PairEventValidationTests(unittest.TestCase):
    """The _act_family() pair-events contract (sexual-intercourse-acts D-1)."""

    _CANONICAL = (("female", "male"), "first_vaginal_penetration")

    def _row(self, key: str, *, target_spec: TargetSpec = TargetSpec.SINGLE, **kwargs):
        return _seed_act_row(key, target_spec=target_spec, **kwargs)

    @covers_requirement("sexual-act-registry::an-act-declaring-pair-events-shall-be-a-single-target-act-whose-entries-are-sorted-two-sex-tuples-naming-real-rulebook-events")
    def test_pair_events_require_a_single_target_spec(self):
        with self.assertRaises(ValueError) as caught:
            self._row(
                "bad_pair_area",
                target_spec=TargetSpec.AREA,
                pair_events=(self._CANONICAL,),
            )
        self.assertIn("bad_pair_area", str(caught.exception))

    @covers_requirement("sexual-act-registry::an-act-declaring-pair-events-shall-be-a-single-target-act-whose-entries-are-sorted-two-sex-tuples-naming-real-rulebook-events")
    def test_unsorted_pair_events_entry_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            self._row(
                "bad_pair_unsorted",
                pair_events=((("male", "female"), "first_vaginal_penetration"),),
            )
        self.assertIn("bad_pair_unsorted", str(caught.exception))

    @covers_requirement("sexual-act-registry::an-act-declaring-pair-events-shall-be-a-single-target-act-whose-entries-are-sorted-two-sex-tuples-naming-real-rulebook-events")
    def test_unknown_sex_pair_is_rejected(self):
        for bad_pair in (("female", "futa"), ("male", "unknown")):
            with self.subTest(pair=bad_pair):
                with self.assertRaises(ValueError) as caught:
                    self._row(
                        "bad_pair_sex",
                        pair_events=((bad_pair, "first_vaginal_penetration"),),
                    )
                self.assertIn("bad_pair_sex", str(caught.exception))

    @covers_requirement("sexual-act-registry::an-act-declaring-pair-events-shall-be-a-single-target-act-whose-entries-are-sorted-two-sex-tuples-naming-real-rulebook-events")
    def test_repeated_pair_events_entry_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            self._row(
                "bad_pair_repeat",
                pair_events=(
                    self._CANONICAL,
                    (("female", "male"), "penetrative_sex_with_female"),
                ),
            )
        self.assertIn("bad_pair_repeat", str(caught.exception))

    @covers_requirement("sexual-act-registry::an-act-declaring-pair-events-shall-be-a-single-target-act-whose-entries-are-sorted-two-sex-tuples-naming-real-rulebook-events")
    def test_pair_events_naming_a_forbidden_event_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            self._row(
                "bad_pair_event",
                pair_events=((("female", "male"), "climax_ends"),),
            )
        message = str(caught.exception)
        self.assertIn("bad_pair_event", message)
        self.assertIn("climax_ends", message)

    @covers_requirement("sexual-act-registry::an-act-declaring-pair-events-shall-be-a-single-target-act-whose-entries-are-sorted-two-sex-tuples-naming-real-rulebook-events")
    def test_non_tuple_pair_events_container_is_rejected(self):
        for bad in ([self._CANONICAL], {"not": "a tuple"}):
            with self.subTest(container=type(bad).__name__):
                with self.assertRaises(ValueError) as caught:
                    self._row("bad_pair_container", pair_events=bad)
                self.assertIn("bad_pair_container", str(caught.exception))

    @covers_requirement("sexual-act-registry::an-act-declaring-pair-events-shall-be-a-single-target-act-whose-entries-are-sorted-two-sex-tuples-naming-real-rulebook-events")
    def test_malformed_pair_events_entry_is_rejected(self):
        for bad in (("female",), ("female", "male", "event"), "not-a-tuple"):
            with self.subTest(entry=bad):
                with self.assertRaises(ValueError) as caught:
                    self._row(
                        "bad_pair_entry",
                        pair_events=(bad,),
                    )
                self.assertIn("bad_pair_entry", str(caught.exception))

    @covers_requirement("sexual-act-registry::an-act-declaring-pair-events-shall-be-a-single-target-act-whose-entries-are-sorted-two-sex-tuples-naming-real-rulebook-events")
    def test_canonical_pair_events_table_is_accepted(self):
        skill, act = self._row(
            "ok_pair_act",
            pair_events=(
                self._CANONICAL,
                (("female", "female"), "penetrative_sex_with_female"),
                (("male", "male"), "penetrative_sex_with_male"),
            ),
        )
        self.assertEqual(act.pair_events[0][1], "first_vaginal_penetration")
        self.assertEqual(skill.effects[-1], "act_pair_event:ok_pair_act")

class LineModuleTests(unittest.TestCase):
    """Every content module carries act rows once its catalog proposal lands."""

    @covers_requirement("sexual-act-registry::the-six-line-modules-ship-pre-declared-and-pre-imported")
    def test_every_line_module_is_importable_and_non_empty(self):
        for module, constant in (
            (sexual_acts.solo, "SOLO_ACTS"),
            (sexual_acts.shame, "SHAME_ACTS"),
            (sexual_acts.partner, "PARTNER_ACTS"),
            (sexual_acts.combat, "COMBAT_ACTS"),
            (sexual_acts.interspecies, "INTERSPECIES_ACTS"),
            (sexual_acts.divine, "DIVINE_ACTS"),
        ):
            with self.subTest(module=module.__name__):
                self.assertTrue(getattr(module, constant))
