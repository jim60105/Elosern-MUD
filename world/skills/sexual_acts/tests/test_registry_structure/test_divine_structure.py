"""Data-contract test: sexual act registry structure contract
Slice of ``test_registry_structure``: DivineEighthRowStructuralTests, OwnershipDriftGuardTests, HalfMigrationAgreementTests, SoleDivineArtsClaimantTests.
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
    check_registries_agree,
    _seed_act_row,
    _PRE_INTEGRATION_DIVINE_KEYS,
    _main_registry_source,
)

class DivineEighthRowStructuralTests(unittest.TestCase):
    """The integrated eighth hand-built pair (integrate-divine-sexual-arts-catalog)."""

    def _eighth(self) -> tuple[SkillDef, SexualActDef]:
        return next(
            (skill, act) for skill, act in DIVINE_ACTS if skill.key == "divine_sexual_arts"
        )

    @covers_requirement("sexual-act-registry::divine-sexual-arts-is-the-eighth-hand-built-神之秘法-row")
    def test_eighth_pair_declares_the_shared_hand_built_fields(self):
        skill, act = self._eighth()
        self.assertEqual(len(DIVINE_ACTS), 8)
        self.assertEqual(skill.key, act.key)
        self.assertTrue(skill.requires_divine_arts)
        self.assertEqual(act.unlock, {})
        self.assertTrue(act.ownership_gated)
        self.assertIsNone(act.target_part)
        self.assertTrue(act.resistible)
        self.assertEqual(act.actor_counters, ())
        self.assertEqual(act.participant_counters, ())
        self.assertEqual(act.sexual_events, ())
        self.assertIs(skill.category.value, "sexual_act")
        self.assertEqual(skill.group, "神之秘法")
        self.assertEqual(skill.cost, {})
        self.assertTrue(skill.usable_out_of_combat)
        self.assertIs(skill.kind, SkillKind.ACTIVE)
        self.assertEqual(skill.effects, ["sexual_event_target:stimulus_applied"])

    @covers_requirement("sexual-act-registry::divine-sexual-arts-is-the-eighth-hand-built-神之秘法-row")
    def test_registry_entry_is_the_catalog_object_not_a_main_registry_row(self):
        skill, _act = self._eighth()
        # Same object identity: the catalogue import installed the pair, and
        # world/skills/registry.py defines no inline entry for the key.
        self.assertIs(SKILL_REGISTRY["divine_sexual_arts"], skill)
        self.assertNotIn("divine_sexual_arts", _main_registry_source())

    def test_parsed_effect_is_the_target_scoped_event_effect(self):
        # The parse contract belongs to sexual-act-effects; this asserts only
        # the shipped row's parsed shape.
        skill, _act = self._eighth()
        self.assertEqual(
            skill.parsed_effects,
            (TargetSexualEventEffect(event_name="stimulus_applied"),),
        )

    def test_first_seven_pairs_and_their_ordering_are_unchanged(self):
        self.assertEqual(
            [skill.key for skill, _act in DIVINE_ACTS[:7]],
            list(_PRE_INTEGRATION_DIVINE_KEYS),
        )

    def test_placeholder_pleasure_field_is_referenced_by_no_effect(self):
        skill, act = self._eighth()
        self.assertEqual(act.base_pleasure, 1)
        self.assertFalse(
            [effect for effect in skill.effects if effect.startswith("pleasure:")],
            "no pleasure: effect may read the placeholder base_pleasure",
        )

    @covers_requirement("sexual-act-registry::sexualactdef-carries-exactly-the-metadata-a-sex-act-needs-beyond-skilldef")
    def test_act_family_exposes_no_ownership_gated_knob(self):
        self.assertNotIn(
            "ownership_gated",
            inspect.signature(_act_family).parameters,
            "catalogue rows are never ownership-gated; only hand-built rows set it",
        )

    @covers_requirement("sexual-act-registry::sexualactdef-carries-exactly-the-metadata-a-sex-act-needs-beyond-skilldef")
    def test_ownership_gated_row_is_constructible_and_reads_back(self):
        act = SexualActDef(
            key="gated_row",
            unlock={},
            base_pleasure=10,
            actor_part="私處",
            target_part=None,
            actor_pleasure_ratio=0.5,
            actor_counters=(),
            participant_counters=(),
            sexual_events=(),
            resistible=True,
            ownership_gated=True,
        )
        self.assertEqual(act.unlock, {})
        self.assertTrue(act.ownership_gated)

class OwnershipDriftGuardTests(EvenniaTestCase):
    """owned_keys() equals base_owned_keys() plus the unconditionally-unlocked seed acts."""

    # Only the non-ownership-gated acts with an empty unlock mapping are owned
    # by a fresh entity; counter-gated rows stay absent until their thresholds
    # are met and ownership-gated rows are never derived at all (D6).
    _SEED_KEYS = sorted(
        key
        for key, act in SEXUAL_ACT_REGISTRY.items()
        if not act.unlock and not act.ownership_gated
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
                    if not act.unlock and not act.ownership_gated
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

class HalfMigrationAgreementTests(unittest.TestCase):
    """The exclusion set no longer hides a half-migrated registry (tasks 5.2)."""

    def test_registry_missing_the_catalog_row_fails_the_agreement_check(self):
        # The pre-integration exclusion for divine_sexual_arts is gone: with
        # only the catalogue row removed (SKILL_REGISTRY still categorising
        # the key SEXUAL_ACT), the comparison fails naming the key.
        removed = SEXUAL_ACT_REGISTRY.pop("divine_sexual_arts")
        try:
            with self.assertRaises(AssertionError) as caught:
                check_registries_agree(SEXUAL_ACT_REGISTRY, SKILL_REGISTRY)
        finally:
            SEXUAL_ACT_REGISTRY["divine_sexual_arts"] = removed
        self.assertIn("divine_sexual_arts", str(caught.exception))

class SoleDivineArtsClaimantTests(unittest.TestCase):
    """Only Yuna's authored preset claims the signature act (tasks 5.1).

    The scan covers the authored preset surface only — the sole shipped
    authored skill-kit surface today, since shipped NPC companions build from
    preset cards. It makes no claim about arbitrary runtime ``db.skills``
    writes.
    """

    _CLAIMED_KEY = "divine_sexual_arts"

    def _claimants(self, registry) -> list[str]:
        return sorted(
            preset.key
            for preset in registry.values()
            if self._CLAIMED_KEY in (*preset.active_skills, *preset.passive_skills)
        )

    @covers_requirement("sexual-act-registry::the-only-claim-of-divine-sexual-arts-in-shipped-data-is-yuna-s-preset")
    def test_yuna_is_the_sole_claimant(self):
        self.assertEqual(self._claimants(PLAYER_PRESET_REGISTRY), ["yuna_darknight"])

    @covers_requirement("sexual-act-registry::the-only-claim-of-divine-sexual-arts-in-shipped-data-is-yuna-s-preset")
    def test_a_second_hypothetical_claimant_fails_the_uniqueness(self):
        intruder = replace(
            PLAYER_PRESET_REGISTRY["elysa_snow"],
            key="hypothetical_claimant",
            active_skills=(self._CLAIMED_KEY,),
            passive_skills=(),
        )
        with patch.dict(PLAYER_PRESET_REGISTRY, {"hypothetical_claimant": intruder}):
            claimants = self._claimants(PLAYER_PRESET_REGISTRY)
        self.assertEqual(claimants, ["hypothetical_claimant", "yuna_darknight"])

    def test_the_scan_input_resolves_against_the_live_registry(self):
        # Count-check: every name the uniqueness scan reads (each preset's
        # full active+passive kit) is a live SKILL_REGISTRY key, so the
        # flattened claim list cannot silently be scanning stale names.
        claimed = [
            (preset.key, key)
            for preset in PLAYER_PRESET_REGISTRY.values()
            for key in (*preset.active_skills, *preset.passive_skills)
        ]
        # The flattening itself loses nothing: one entry per declared name.
        self.assertEqual(
            len(claimed),
            sum(
                len(preset.active_skills) + len(preset.passive_skills)
                for preset in PLAYER_PRESET_REGISTRY.values()
            ),
        )
        for _preset_key, key in claimed:
            self.assertIn(key, SKILL_REGISTRY)
