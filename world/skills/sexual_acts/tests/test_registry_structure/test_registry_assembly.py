"""Data-contract test: sexual act registry structure contract
Slice of ``test_registry_structure``: RegistryAssemblyTests, WholeRegistryStructuralTests, SexualActEffectsStructuralTests, ActorScopedEventChannelTests, LegacyTargetScopedEventTests.
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
    _KNOWN_EVENTS,
    check_names_resolve,
    check_registries_agree,
    check_solo_acts_declare_no_participant_counters,
    check_external_acts_declare_a_target_part,
    _seed_act_row,
)

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

    @covers_requirement("sexual-act-registry::sexual-act-registry-s-keys-and-skill-registry-s-sexual-act-categorised-keys-agree-exactly-modulo-the-two-named-mastery-exclusions")
    def test_registries_agree_with_zero_acts_registered(self):
        check_registries_agree(SEXUAL_ACT_REGISTRY, SKILL_REGISTRY)

    @covers_requirement("sexual-act-registry::sexual-act-registry-s-keys-and-skill-registry-s-sexual-act-categorised-keys-agree-exactly-modulo-the-two-named-mastery-exclusions")
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
    """The builder keeps no recipient-scope table; only the emission ban remains."""

    def test_builder_namespace_has_no_legacy_recipient_table(self):
        self.assertFalse(
            hasattr(_builder_module, "_LEGACY_TARGET_SCOPED_EVENTS"),
            "_builder.py must not resurrect a name-based recipient scope table",
        )

    def test_forbidden_events_remains_present_and_unchanged(self):
        self.assertEqual(
            set(_FORBIDDEN_SEXUAL_EVENTS),
            {
                "stimulus_applied",
                "sustained_stimulus_applied",
                "extreme_stimulus_applied",
                "climax_ends",
                "climax_extended",
            },
        )
