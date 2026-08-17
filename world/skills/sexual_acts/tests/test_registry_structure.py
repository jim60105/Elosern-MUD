"""Whole-registry structural invariants for the sexual act catalogue.

The per-row checks run inside ``_act_family()`` at import time; the
whole-registry checks below are test-time, mirroring ``sexual.yaml``'s own
``test_every_rule_id_has_a_test()`` precedent, because they need the fully
assembled ``SKILL_REGISTRY`` and a parsed rulebook that no single module is
guaranteed to have while still importing.
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
from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY
from world.skills.sexual_acts._builder import (
    _ACTOR_SCOPED_EVENTS,
    _LEGACY_TARGET_SCOPED_EVENTS,
    SexualActDef,
    _act_family,
)

_SEXUAL_YAML_PATH = Path(__file__).parents[3] / "rules" / "rulebook" / "sexual.yaml"
# The three pre-existing mastery/mystery skills categorised SEXUAL_ACT that
# carry no SexualActDef by design (acquisition-path skills, not acts).
_MASTERY_EXCLUSIONS = frozenset(
    {"divine_sexual_arts", "divine_sexual_mastery", "reincarnation_boon_yuna"}
)

_KNOWN_EVENTS = frozenset(
    rule.when["event"]
    for rule in load_rules(_SEXUAL_YAML_PATH)
    if "event" in rule.when
)


def check_names_resolve(act: SexualActDef) -> None:
    """Assert every counter/event an act names actually exists.

    Raises ``AssertionError`` naming the act's key and the unrecognized
    string, so the failure points at the offending catalog row. Pair-event
    names are checked exactly like ``sexual_events`` names: both are
    rulebook ``when["event"]`` values.
    """
    for name in (*act.unlock, *act.actor_counters, *act.participant_counters):
        if name not in _LIFETIME_COUNTER_KEYS:
            raise AssertionError(
                f"act {act.key!r} names unknown counter {name!r}"
            )
    for name in (*act.sexual_events, *(event for _, event in act.pair_events)):
        if name not in _KNOWN_EVENTS:
            raise AssertionError(f"act {act.key!r} names unknown event {name!r}")


def check_registries_agree(act_registry, skill_registry) -> None:
    """Assert both registries carry exactly the same act keys.

    ``SKILL_REGISTRY``'s ``SEXUAL_ACT``-categorised keys must equal
    ``SEXUAL_ACT_REGISTRY``'s keys, modulo the named mastery/mystery
    exclusions. Raises ``AssertionError`` naming any unmatched key.
    """
    skill_act_keys = {
        key
        for key, skill in skill_registry.items()
        if skill.category is SkillCategory.SEXUAL_ACT
    } - _MASTERY_EXCLUSIONS
    unmatched = skill_act_keys ^ set(act_registry)
    if unmatched:
        raise AssertionError(
            "SEXUAL_ACT_REGISTRY and SKILL_REGISTRY disagree on act keys: "
            f"{sorted(unmatched)}"
        )


def check_solo_acts_declare_no_participant_counters(act_registry, skill_registry) -> None:
    """Assert every SELF-target act declares ``participant_counters=()``.

    A solo act has no other participant to credit, so a non-empty
    participant counter list would silently mis-credit nobody.
    """
    for key, act in act_registry.items():
        skill = skill_registry[key]
        if skill.target_spec is TargetSpec.SELF and act.participant_counters:
            raise AssertionError(
                f"act {key!r} is SELF-targeted but declares "
                f"participant_counters {act.participant_counters}"
            )


def check_external_acts_declare_a_target_part(act_registry, skill_registry) -> None:
    """Assert every non-異種/神之秘法 act targeting others declares a target part.

    The two parless lines may omit ``target_part`` by design (monsters are
    arbitrarily shaped, divine arts operate through divinity); any other line
    targeting a second entity must declare the part that entity's pleasure is
    computed against, or ``resolve_part`` would silently fall back to the
    generic channel (design risk mitigation).
    """
    for key, act in act_registry.items():
        skill = skill_registry[key]
        if skill.group in ("異種", "神之秘法"):
            continue
        if skill.target_spec in (TargetSpec.SELF, TargetSpec.NONE):
            continue
        if act.target_part is None:
            raise AssertionError(
                f"act {key!r} on line {skill.group!r} targets others "
                "but declares no target_part"
            )


def _seed_act_row(
    key: str = "test_act",
    *,
    line: str = "獨處線",
    target_spec: TargetSpec = TargetSpec.SELF,
    unlock: dict[str, int] | None = None,
    base_pleasure: int = 10,
    actor_part: str | None = "私處",
    target_part: str | None = None,
    actor_pleasure_ratio: float = 0.5,
    actor_counters: tuple[str, ...] = ("restraint_count",),
    participant_counters: tuple[str, ...] = (),
    sexual_events: tuple[str, ...] = (),
    resistible: bool = True,
    pair_events: tuple[tuple[tuple[str, str], str], ...] = (),
    requires_divine_arts: bool = False,
) -> tuple[SkillDef, SexualActDef]:
    """Build one synthetic act row for contract tests without catalog content.

    A non-empty ``pair_events`` table becomes the row's optional 14th field,
    keeping ordinary rows at the 13-field length.
    """
    row = (
        key,
        "測試行為",
        "僅存在於測試中的合成行為。",
        target_spec,
        {} if unlock is None else unlock,
        base_pleasure,
        actor_part,
        target_part,
        actor_pleasure_ratio,
        actor_counters,
        participant_counters,
        sexual_events,
        resistible,
    )
    if pair_events:
        row = (*row, pair_events)
    (skill, act), = _act_family(
        line,
        row,
        requires_divine_arts=requires_divine_arts,
    )
    return skill, act


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


class ActFamilyTests(unittest.TestCase):
    """The _act_family() pairing contract and its five per-row checks."""

    @covers_requirement("sexual-act-registry::every-sexualactdef-is-paired-with-an-ordinary-skilldef-under-the-same-key-categorised-sexual-act")
    def test_row_produces_a_matching_skilldef_and_sexualactdef(self):
        skill, act = _seed_act_row("test_act")
        self.assertIs(skill.category, SkillCategory.SEXUAL_ACT)
        self.assertEqual(skill.key, "test_act")
        self.assertEqual(act.key, "test_act")
        self.assertEqual(act.unlock, {})

    @covers_requirement("sexual-act-registry::every-sexualactdef-is-paired-with-an-ordinary-skilldef-under-the-same-key-categorised-sexual-act")
    def test_sex_act_costs_no_resource_and_casts_out_of_combat(self):
        skill, _ = _seed_act_row()
        self.assertEqual(skill.cost, {})
        self.assertTrue(skill.usable_out_of_combat)
        self.assertIs(skill.kind, SkillKind.ACTIVE)

    @covers_requirement("sexual-act-registry::every-act-applying-pleasure-to-another-participant-applies-non-zero-pleasure-to-its-own-actor-unless-it-requires-divine-arts")
    def test_zero_actor_pleasure_ratio_is_rejected_for_a_non_divine_family(self):
        with self.assertRaises(ValueError) as caught:
            _seed_act_row("bad_ratio", actor_pleasure_ratio=0.0)
        self.assertIn("bad_ratio", str(caught.exception))

    @covers_requirement("sexual-act-registry::every-act-applying-pleasure-to-another-participant-applies-non-zero-pleasure-to-its-own-actor-unless-it-requires-divine-arts")
    def test_zero_actor_pleasure_ratio_is_accepted_for_a_divine_family(self):
        skill, act = _seed_act_row(
            "divine_row",
            actor_pleasure_ratio=0.0,
            requires_divine_arts=True,
        )
        self.assertTrue(skill.requires_divine_arts)
        self.assertEqual(act.actor_pleasure_ratio, 0.0)

    @covers_requirement("sexual-act-registry::every-act-applying-pleasure-to-another-participant-applies-non-zero-pleasure-to-its-own-actor-unless-it-requires-divine-arts")
    def test_non_finite_actor_pleasure_ratio_is_rejected_for_every_family(self):
        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(ratio=bad):
                with self.assertRaises(ValueError) as caught:
                    _seed_act_row("bad_finite_ratio", actor_pleasure_ratio=bad)
                self.assertIn("bad_finite_ratio", str(caught.exception))
            with self.subTest(ratio=bad, divine=True):
                with self.assertRaises(ValueError):
                    _seed_act_row(
                        "bad_finite_ratio_divine",
                        actor_pleasure_ratio=bad,
                        requires_divine_arts=True,
                    )

    def test_non_integer_unlock_threshold_is_rejected(self):
        for bad in (True, 1.5, "1"):
            with self.subTest(threshold=bad):
                with self.assertRaises(ValueError) as caught:
                    _seed_act_row("bad_threshold", unlock={"restraint_count": bad})
                self.assertIn("bad_threshold", str(caught.exception))

    def test_non_mapping_unlock_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            _seed_act_row("bad_unlock_shape", unlock=("restraint_count", 1))
        self.assertIn("bad_unlock_shape", str(caught.exception))

    @covers_requirement("sexual-act-registry::no-act-declares-the-generic-body-part-channel-only-異種-and-神之秘法-acts-may-omit-a-target-part")
    def test_declaring_the_generic_body_part_is_rejected(self):
        for part_field in ("actor_part", "target_part"):
            with self.subTest(part_field=part_field):
                kwargs = {"actor_part": "私處", "target_part": None}
                kwargs[part_field] = GENERIC_BODY_PART
                with self.assertRaises(ValueError) as caught:
                    _seed_act_row(f"bad_part_{part_field}", **kwargs)
                self.assertIn(f"bad_part_{part_field}", str(caught.exception))

    @covers_requirement("sexual-act-registry::no-act-declares-the-generic-body-part-channel-only-異種-and-神之秘法-acts-may-omit-a-target-part")
    def test_interspecies_act_declaring_a_target_part_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            _seed_act_row("bad_interspecies", line="異種", target_part="私處")
        self.assertIn("bad_interspecies", str(caught.exception))

    @covers_requirement("sexual-act-registry::no-act-declares-the-generic-body-part-channel-only-異種-and-神之秘法-acts-may-omit-a-target-part")
    def test_divine_act_declaring_a_target_part_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            _seed_act_row(
                "bad_divine",
                line="神之秘法",
                target_part="私處",
                requires_divine_arts=True,
            )
        self.assertIn("bad_divine", str(caught.exception))

    @covers_requirement("sexual-act-registry::no-act-declares-the-generic-body-part-channel-only-異種-and-神之秘法-acts-may-omit-a-target-part")
    def test_part_outside_body_parts_is_rejected_naming_key_and_part(self):
        with self.assertRaises(ValueError) as caught:
            _seed_act_row("bad_body_part", actor_part="觸手")
        message = str(caught.exception)
        self.assertIn("bad_body_part", message)
        self.assertIn("觸手", message)

    def test_non_positive_base_pleasure_is_rejected(self):
        for bad in (0, -5, 1.5):
            with self.subTest(base_pleasure=bad):
                with self.assertRaises(ValueError):
                    _seed_act_row("bad_pleasure", base_pleasure=bad)

    def test_non_bare_bool_resistible_is_rejected(self):
        with self.assertRaises(ValueError):
            _seed_act_row("bad_resistible", resistible=1)

    @covers_requirement("sexual-act-registry::act-family-populates-every-row-s-effects-with-the-pleasure-and-sexual-counter-prefixes-for-that-row-s-own-key-plus-one-sexual-event-entry-per-declared-event-and-one-act-pair-event-entry-when-the-row-declares-pair-events")
    def test_row_effects_carry_both_new_prefixes_keyed_to_its_own_act(self):
        skill, _ = _seed_act_row("test_act")
        self.assertEqual(
            skill.effects,
            ["pleasure:test_act", "sexual_counter:test_act"],
        )

    @covers_requirement("sexual-act-registry::act-family-populates-every-row-s-effects-with-the-pleasure-and-sexual-counter-prefixes-for-that-row-s-own-key-plus-one-sexual-event-entry-per-declared-event-and-one-act-pair-event-entry-when-the-row-declares-pair-events")
    def test_declared_sexual_events_gain_one_entry_per_name_in_order(self):
        # A name in the actor-scoped vocabulary (watched_during_activity) is
        # emitted through the sexual_event_actor: prefix; a participant-scoped
        # name keeps the plain sexual_event: prefix.
        skill, _ = _seed_act_row(
            "test_act",
            sexual_events=("frequent_stimulation", "watched_during_activity"),
        )
        self.assertEqual(
            skill.effects,
            [
                "pleasure:test_act",
                "sexual_counter:test_act",
                "sexual_event:frequent_stimulation",
                "sexual_event_actor:watched_during_activity",
            ],
        )

    @covers_requirement("sexual-act-registry::act-family-populates-every-row-s-effects-with-the-pleasure-and-sexual-counter-prefixes-for-that-row-s-own-key-plus-one-sexual-event-entry-per-declared-event-and-one-act-pair-event-entry-when-the-row-declares-pair-events")
    def test_pair_events_row_gains_exactly_one_trailing_act_pair_event_entry(self):
        skill, _ = _seed_act_row(
            "test_act",
            target_spec=TargetSpec.SINGLE,
            pair_events=((("female", "male"), "first_vaginal_penetration"),),
        )
        self.assertEqual(
            skill.effects,
            [
                "pleasure:test_act",
                "sexual_counter:test_act",
                "act_pair_event:test_act",
            ],
        )

    @covers_requirement("sexual-act-registry::act-family-populates-every-row-s-effects-with-the-pleasure-and-sexual-counter-prefixes-for-that-row-s-own-key-plus-one-sexual-event-entry-per-declared-event-and-one-act-pair-event-entry-when-the-row-declares-pair-events")
    def test_plain_row_never_gains_an_act_pair_event_entry(self):
        skill, _ = _seed_act_row("test_act", sexual_events=("frequent_stimulation",))
        self.assertEqual(
            skill.effects,
            [
                "pleasure:test_act",
                "sexual_counter:test_act",
                "sexual_event:frequent_stimulation",
            ],
        )

    @covers_requirement("sexual-act-registry::act-family-populates-every-row-s-effects-with-the-pleasure-and-sexual-counter-prefixes-for-that-row-s-own-key-plus-one-sexual-event-entry-per-declared-event-and-one-act-pair-event-entry-when-the-row-declares-pair-events")
    def test_multiple_rows_each_name_only_their_own_key(self):
        rows = (
            (
                "first_act",
                "第一行為",
                "測試用第一行為。",
                TargetSpec.SELF,
                {},
                10,
                "私處",
                None,
                0.5,
                (),
                (),
                (),
                True,
            ),
            (
                "second_act",
                "第二行為",
                "測試用第二行為。",
                TargetSpec.SELF,
                {},
                10,
                "私處",
                None,
                0.5,
                (),
                (),
                (),
                True,
            ),
        )
        pairs = _act_family("獨處線", *rows)
        self.assertEqual(len(pairs), 2)
        for skill, act in pairs:
            for effect in skill.effects:
                if effect.startswith("pleasure:") or effect.startswith("sexual_counter:"):
                    self.assertEqual(
                        effect.partition(":")[2],
                        act.key,
                        f"{skill.key!r} names another act's key in {effect!r}",
                    )

    @covers_requirement("sexual-act-registry::an-act-s-sexual-events-never-names-a-pleasure-wetness-or-climax-settlement-owned-event")
    def test_forbidden_event_fails_at_construction_naming_key_and_event(self):
        with self.assertRaises(ValueError) as caught:
            _seed_act_row("bad_event_act", sexual_events=("stimulus_applied",))
        message = str(caught.exception)
        self.assertIn("bad_event_act", message)
        self.assertIn("stimulus_applied", message)

    @covers_requirement("sexual-act-registry::an-act-s-sexual-events-never-names-a-pleasure-wetness-or-climax-settlement-owned-event")
    def test_direct_stimulus_applied_is_permitted(self):
        skill, _ = _seed_act_row(
            "ok_event_act",
            sexual_events=("direct_stimulus_applied",),
        )
        self.assertIn("sexual_event:direct_stimulus_applied", skill.effects)

    def test_every_forbidden_event_name_is_rejected(self):
        for event in (
            "stimulus_applied",
            "sustained_stimulus_applied",
            "extreme_stimulus_applied",
            "climax_ends",
            "climax_extended",
        ):
            with self.subTest(event=event):
                with self.assertRaises(ValueError) as caught:
                    _seed_act_row(f"bad_{event}", sexual_events=(event,))
                self.assertIn(f"bad_{event}", str(caught.exception))

    @covers_requirement("sexual-act-registry::act-family-populates-every-row-s-effects-with-the-pleasure-and-sexual-counter-prefixes-for-that-row-s-own-key-plus-one-sexual-event-entry-per-declared-event-and-one-act-pair-event-entry-when-the-row-declares-pair-events")
    def test_row_length_guard_rejects_any_length_besides_13_or_14(self):
        base = (
            "len_act",
            "長度行為",
            "測試長度守衛的合成行為。",
            TargetSpec.SELF,
            {},
            10,
            "私處",
            None,
            0.5,
            (),
            (),
            (),
            True,
        )
        for row in (base[:12], (*base, (), ("extra",))):
            with self.subTest(length=len(row)):
                with self.assertRaises(ValueError) as caught:
                    _act_family("獨處線", row)
                self.assertIn("len_act", str(caught.exception))


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


class RegistryAssemblyTests(unittest.TestCase):
    """Import-order and agreement invariants of the assembled registries."""

    def test_registration_updates_the_shared_skill_registry_object(self):
        self.assertIs(
            sexual_acts.SKILL_REGISTRY,
            registry_module.SKILL_REGISTRY,
        )

    def test_colliding_act_key_is_rejected_by_the_assembly(self):
        skill, act = _seed_act_row("basic_attack")
        with self.assertRaises(ValueError) as caught:
            sexual_acts._register_rows(((skill, act),))
        self.assertIn("basic_attack", str(caught.exception))

    def test_duplicate_act_key_is_rejected_by_the_assembly(self):
        skill, act = _seed_act_row("dup_act")
        with patch.dict(SEXUAL_ACT_REGISTRY, {"dup_act": act}):
            with self.assertRaises(ValueError) as caught:
                sexual_acts._register_rows(((skill, act),))
        self.assertIn("dup_act", str(caught.exception))

    def test_key_disagreement_is_rejected_by_the_assembly(self):
        skill, act = _seed_act_row("agree_key")
        mismatched = replace(act, key="other_key")
        with self.assertRaises(ValueError) as caught:
            sexual_acts._register_rows(((skill, mismatched),))
        message = str(caught.exception)
        self.assertIn("agree_key", message)
        self.assertIn("other_key", message)

    @covers_requirement("sexual-act-registry::sexual-act-registry-s-keys-and-skill-registry-s-sexual-act-categorised-keys-agree-exactly-modulo-the-three-named-mastery-mystery-exclusions")
    def test_registries_agree_with_zero_acts_registered(self):
        check_registries_agree(SEXUAL_ACT_REGISTRY, SKILL_REGISTRY)

    @covers_requirement("sexual-act-registry::sexual-act-registry-s-keys-and-skill-registry-s-sexual-act-categorised-keys-agree-exactly-modulo-the-three-named-mastery-mystery-exclusions")
    def test_orphan_sexual_act_skill_fails_the_agreement_check(self):
        orphan = SkillDef(
            key="orphan_act",
            label="孤兒行為",
            description="直接注入測試中的 SEXUAL_ACT 技能，沒有配對的 SexualActDef。",
            kind=SkillKind.ACTIVE,
            target_spec=TargetSpec.SELF,
            cost={},
            usable_out_of_combat=True,
            element=None,
            effects=[],
            category=SkillCategory.SEXUAL_ACT,
            group="獨處線",
        )
        with patch.dict(SKILL_REGISTRY, {"orphan_act": orphan}):
            with self.assertRaises(AssertionError) as caught:
                check_registries_agree(SEXUAL_ACT_REGISTRY, SKILL_REGISTRY)
        self.assertIn("orphan_act", str(caught.exception))


class WholeRegistryStructuralTests(unittest.TestCase):
    """The whole-registry invariants against the assembled catalogue."""

    def test_every_named_counter_and_event_resolves(self):
        for act in SEXUAL_ACT_REGISTRY.values():
            with self.subTest(act=act.key):
                check_names_resolve(act)

    @covers_requirement("sexual-act-registry::solo-acts-declare-no-participant-counters-structurally-enforced")
    def test_solo_acts_declare_no_participant_counters(self):
        check_solo_acts_declare_no_participant_counters(SEXUAL_ACT_REGISTRY, SKILL_REGISTRY)

    @covers_requirement("sexual-act-registry::every-act-outside-the-異種-and-神之秘法-lines-targeting-another-entity-declares-a-non-null-target-part")
    def test_external_acts_declare_a_target_part(self):
        check_external_acts_declare_a_target_part(SEXUAL_ACT_REGISTRY, SKILL_REGISTRY)


class SexualActEffectsStructuralTests(unittest.TestCase):
    """Scenario-level checks for the two sexual-act-effects structural rules."""

    def test_self_target_act_with_participant_counters_fails_naming_the_key(self):
        skill, act = _seed_act_row(
            "bad_solo",
            participant_counters=("duo_act_count",),
        )
        with patch.dict(SEXUAL_ACT_REGISTRY, {act.key: act}), patch.dict(
            SKILL_REGISTRY, {skill.key: skill}
        ):
            with self.assertRaises(AssertionError) as caught:
                check_solo_acts_declare_no_participant_counters(
                    SEXUAL_ACT_REGISTRY, SKILL_REGISTRY
                )
        self.assertIn("bad_solo", str(caught.exception))

    def test_self_target_act_with_empty_participant_counters_passes(self):
        skill, act = _seed_act_row("ok_solo", participant_counters=())
        with patch.dict(SEXUAL_ACT_REGISTRY, {act.key: act}), patch.dict(
            SKILL_REGISTRY, {skill.key: skill}
        ):
            check_solo_acts_declare_no_participant_counters(
                SEXUAL_ACT_REGISTRY, SKILL_REGISTRY
            )

    def test_external_act_without_target_part_fails_naming_the_key(self):
        skill, act = _seed_act_row(
            "bad_external",
            line="關係",
            target_spec=TargetSpec.SINGLE,
            target_part=None,
        )
        with patch.dict(SEXUAL_ACT_REGISTRY, {act.key: act}), patch.dict(
            SKILL_REGISTRY, {skill.key: skill}
        ):
            with self.assertRaises(AssertionError) as caught:
                check_external_acts_declare_a_target_part(
                    SEXUAL_ACT_REGISTRY, SKILL_REGISTRY
                )
        message = str(caught.exception)
        self.assertIn("bad_external", message)
        self.assertIn("關係", message)

    def test_interspecies_external_act_without_target_part_passes(self):
        skill, act = _seed_act_row(
            "ok_interspecies",
            line="異種",
            target_spec=TargetSpec.SINGLE,
            target_part=None,
        )
        with patch.dict(SEXUAL_ACT_REGISTRY, {act.key: act}), patch.dict(
            SKILL_REGISTRY, {skill.key: skill}
        ):
            check_external_acts_declare_a_target_part(
                SEXUAL_ACT_REGISTRY, SKILL_REGISTRY
            )


class ActorScopedEventChannelTests(unittest.TestCase):
    """The actor-scoped channel classification (sexual-public-act-events D-6)."""

    @covers_requirement("sexual-act-registry::acts-classify-each-declared-event-by-name-into-the-actor-scoped-or-participant-scoped-channel")
    def test_actor_scoped_vocabulary_is_exactly_the_four_names(self):
        self.assertEqual(
            _ACTOR_SCOPED_EVENTS,
            frozenset(
                {
                    "self_exposure",
                    "public_exposure",
                    "watched_during_activity",
                    "public_sexual_activity",
                }
            ),
        )

    @covers_requirement("sexual-act-registry::acts-classify-each-declared-event-by-name-into-the-actor-scoped-or-participant-scoped-channel")
    def test_every_actor_scoped_name_is_a_real_rulebook_event(self):
        self.assertLessEqual(_ACTOR_SCOPED_EVENTS, _KNOWN_EVENTS)

    @covers_requirement("sexual-act-registry::acts-classify-each-declared-event-by-name-into-the-actor-scoped-or-participant-scoped-channel")
    def test_self_exposure_always_uses_the_actor_channel(self):
        # Two acts on different lines both declare self_exposure; neither row
        # can pick the participant channel for the name.
        for key in ("shame_hem_lift", "shame_half_expose_chest"):
            with self.subTest(key=key):
                effects = SKILL_REGISTRY[key].effects
                self.assertIn("sexual_event_actor:self_exposure", effects)
                self.assertNotIn("sexual_event:self_exposure", effects)

    @covers_requirement("sexual-act-registry::acts-classify-each-declared-event-by-name-into-the-actor-scoped-or-participant-scoped-channel")
    def test_participant_scoped_name_never_uses_the_actor_channel(self):
        effects = SKILL_REGISTRY["shame_public_masturbation"].effects
        self.assertIn("sexual_event:masturbation_climax", effects)
        self.assertNotIn("sexual_event_actor:masturbation_climax", effects)

    @covers_requirement("sexual-act-registry::acts-classify-each-declared-event-by-name-into-the-actor-scoped-or-participant-scoped-channel")
    def test_every_declared_event_resolves_to_exactly_one_channel(self):
        for key, act in SEXUAL_ACT_REGISTRY.items():
            effects = SKILL_REGISTRY[key].effects
            for name in act.sexual_events:
                with self.subTest(act=key, event=name):
                    self.assertIn(name, _KNOWN_EVENTS)
                    actor_channel = f"sexual_event_actor:{name}" in effects
                    participant_channel = f"sexual_event:{name}" in effects
                    self.assertNotEqual(
                        actor_channel,
                        participant_channel,
                        f"{key!r} declares {name!r} on both channels or neither",
                    )


class LegacyTargetScopedEventTests(unittest.TestCase):
    """The legacy target-scoped recipient set stays pinned and unreachable by acts."""

    def test_legacy_set_names_exactly_the_divine_skill_event(self):
        self.assertEqual(_LEGACY_TARGET_SCOPED_EVENTS, frozenset({"stimulus_applied"}))

    @covers_requirement("sexual-act-effects::sexual-event-name-entries-in-an-act-s-effects-reuse-the-existing-handler-and-dispatch-table-unchanged")
    def test_legacy_set_is_disjoint_from_every_acts_declared_events(self):
        declared = {
            event
            for act in SEXUAL_ACT_REGISTRY.values()
            for event in (
                *act.sexual_events,
                *(event_name for _, event_name in act.pair_events),
            )
        }
        self.assertTrue(_LEGACY_TARGET_SCOPED_EVENTS.isdisjoint(declared))


class OwnershipDriftGuardTests(EvenniaTestCase):
    """owned_keys() equals base_owned_keys() plus the unconditionally-unlocked seed acts."""

    # Only the acts with an empty unlock mapping are owned by a fresh entity;
    # counter-gated catalogue rows stay absent until their thresholds are met.
    _SEED_KEYS = sorted(
        key for key, act in SEXUAL_ACT_REGISTRY.items() if not act.unlock
    )

    def test_owned_keys_appends_the_unconditionally_unlocked_seed_acts(self):
        entity = create_object(PlayerCharacter, key="drift guard")
        entity.race = "human"
        entity.apply_race_baseline()
        entity.db.skills = {"active": ["fire_ball"], "passive": []}
        self.assertEqual(entity.sexual.unlocked_act_keys(), frozenset(self._SEED_KEYS))
        self.assertEqual(
            entity.skills.owned_keys(),
            [*entity.skills.base_owned_keys(), *self._SEED_KEYS],
        )
        self.assertEqual(
            entity.skills.owned_keys(),
            ["fire_ball", "flee", "basic_attack", *self._SEED_KEYS],
        )

    @covers_requirement("skill-handler::owned-keys-includes-every-unlocked-sexual-act-and-base-owned-keys-exposes-the-pre-extension-set")
    def test_handler_imports_nothing_from_world_rules(self):
        source = inspect.getsource(handler)
        self.assertNotIn("world.rules", source)
        self.assertIn("getattr(self.entity, \"sexual\", None)", source)

    def test_handler_has_no_sexual_import_at_module_level(self):
        source = inspect.getsource(handler)
        self.assertNotIn("from world.rules", source)
        self.assertNotIn("import sexual_state", source)

    @covers_requirement("skill-handler::owned-keys-includes-every-unlocked-sexual-act-and-base-owned-keys-exposes-the-pre-extension-set")
    def test_owned_keys_resolves_without_a_sexual_attribute(self):
        bare = SimpleNamespace(db=SimpleNamespace(skills=None))
        self.assertEqual(
            SkillHandler(bare).owned_keys(),
            [
                "flee",
                "basic_attack",
                *sorted(
                    key
                    for key, act in SEXUAL_ACT_REGISTRY.items()
                    if not act.unlock
                ),
            ],
        )

    @covers_requirement("skill-handler::owned-keys-includes-every-unlocked-sexual-act-and-base-owned-keys-exposes-the-pre-extension-set")
    def test_owned_keys_reads_seed_acts_without_materializing_sexual_state(self):
        entity = create_object(PlayerCharacter, key="no-create seed read")
        entity.race = "human"
        entity.apply_race_baseline()
        entity.db.skills = {"active": [], "passive": []}
        skill, act = _seed_act_row("seed_only_act", unlock={})
        self.assertIsNone(
            entity.attributes.get("sexual_traits", default=None, category="traits")
        )
        with patch.dict(SEXUAL_ACT_REGISTRY, {act.key: act}), patch.dict(
            SKILL_REGISTRY, {skill.key: skill}
        ):
            self.assertIn(act.key, entity.skills.owned_keys())
        self.assertIsNone(
            entity.attributes.get("sexual_traits", default=None, category="traits"),
            "owned_keys() must not materialize the sexual handler",
        )

    @covers_requirement("skill-handler::owned-keys-includes-every-unlocked-sexual-act-and-base-owned-keys-exposes-the-pre-extension-set")
    def test_owned_keys_mastery_fallback_unlocks_without_materializing(self):
        entity = create_object(PlayerCharacter, key="no-create mastery read")
        entity.race = "human"
        entity.apply_race_baseline()
        entity.db.skills = {"active": ["divine_sexual_mastery"], "passive": []}
        skill, act = _seed_act_row("mastery_only_act", unlock={"climax_count": 99})
        with patch.dict(SEXUAL_ACT_REGISTRY, {act.key: act}), patch.dict(
            SKILL_REGISTRY, {skill.key: skill}
        ):
            self.assertIn(act.key, entity.skills.owned_keys())
        self.assertIsNone(
            entity.attributes.get("sexual_traits", default=None, category="traits"),
            "owned_keys() must not materialize the sexual handler",
        )
