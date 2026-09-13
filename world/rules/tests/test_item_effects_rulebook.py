"""Validation tests for the declarative item-effect rulebook (design D1–D6).

The rulebook binds an ordered typed effect list to each usable ITEM key;
every ``item-effect-rulebook`` delta scenario is exercised here against
injected catalogs — fabricated registries and buff tables — so no shipped
magnitude or key is restated (the frozen shipped-row contract lives in
``test_shipped_item_use_regression``).
"""

from types import SimpleNamespace
import tempfile
import unittest
from pathlib import Path

import yaml

from tools.spec_traceability import covers_requirement
from world.lore.items import ITEM_REGISTRY
from world.rules.item_effects import (
    GaugeAdjustEffect,
    ItemEffectProfile,
    ItemEffectsRulebookError,
    ItemStat,
    ItemTargetScope,
    ITEM_EFFECT_PROFILES,
    ITEM_USE_SECONDS,
    MAX_EFFECT_AMOUNT,
    StatusApplyEffect,
    StatusRemoveEffect,
    load_item_effect_rules,
    reload_item_effect_rules,
)

# A fabricated one-entry registry/buff table: the validator resolves the
# usable key set through ``use_mechanics``, so a bare namespace suffices.
_USABLE = SimpleNamespace(use_mechanics=SimpleNamespace())
_UNUSABLE = SimpleNamespace(use_mechanics=None)
_REGISTRY = {"t_test_item": _USABLE, "t_test_sword": _UNUSABLE}
_BUFFS = {"t_test_buff": SimpleNamespace(polarity="buff")}


def _document(*effect_entries: dict, seconds: int = 6, items: dict | None = None):
    return {
        "item_use_seconds": seconds,
        "items": items
        if items is not None
        else {"t_test_item": {"effects": list(effect_entries)}},
    }


def _load_via_validate(document: dict):
    from world.rules.item_effects import validate_item_effect_rules

    return validate_item_effect_rules(document, _REGISTRY, _BUFFS)


class CanonicalRulebookTests(unittest.TestCase):
    """The shipped rulebook loads, aligns, and stays self-scoped."""

    @covers_requirement(
        "item-effect-rulebook::a-usable-item-s-effects-are-an-ordered-list-bound-by-item-key"
    )
    def test_canonical_rulebook_validates(self):
        loaded = load_item_effect_rules()
        self.assertEqual(loaded["item_use_seconds"], ITEM_USE_SECONDS)
        self.assertGreaterEqual(ITEM_USE_SECONDS, 1)

    @covers_requirement(
        "item-effect-rulebook::a-usable-item-s-effects-are-an-ordered-list-bound-by-item-key",
        "item-effect-rulebook::the-rulebook-and-the-registry-align-exactly-at-startup"
    )
    def test_profiles_align_with_the_usable_registry_keys(self):
        loaded = load_item_effect_rules()
        usable = {
            key
            for key, definition in ITEM_REGISTRY.items()
            if definition.use_mechanics is not None
        }
        self.assertEqual(set(loaded["profiles"]), usable)
        self.assertEqual(set(ITEM_EFFECT_PROFILES), usable)

    @covers_requirement(
        "item-effect-rulebook::only-the-acting-entity-is-an-accepted-scope-until-item-targeting-ships"
    )
    def test_every_shipped_effect_is_self_scoped(self):
        # Delta scenario: "Every shipped item is self-scoped".
        for profile in load_item_effect_rules()["profiles"].values():
            for effect in profile.effects:
                self.assertIs(effect.scope, ItemTargetScope.SELF)

    def test_reload_is_idempotent(self):
        before = dict(ITEM_EFFECT_PROFILES)
        before_seconds = ITEM_USE_SECONDS
        reload_item_effect_rules()
        self.assertEqual(ITEM_USE_SECONDS, before_seconds)
        self.assertEqual(dict(ITEM_EFFECT_PROFILES), before)

    def test_valid_override_path_loads(self):
        handle = tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        )
        try:
            yaml.safe_dump(
                _document({"stat": "hp", "amount": 5}), handle, allow_unicode=True
            )
            handle.close()
            loaded = load_item_effect_rules(
                Path(handle.name), registry=_REGISTRY, buff_definitions=_BUFFS
            )
        finally:
            Path(handle.name).unlink(missing_ok=True)
        self.assertEqual(loaded["item_use_seconds"], 6)
        profile = loaded["profiles"]["t_test_item"]
        self.assertEqual(profile.effects[0].amount, 5)

    def test_duplicate_mapping_keys_fail_loud(self):
        # Fail-loud contract (mirrors equipment_effects.py): the loaded data
        # must never silently diverge from the reviewed file.
        text = yaml.safe_dump(
            _document({"stat": "hp", "amount": 5}), allow_unicode=True
        )
        text += "  t_test_item:\n    effects:\n      - stat: hp\n        amount: 9999\n"
        handle = tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        )
        try:
            handle.write(text)
            handle.close()
            with self.assertRaises(ItemEffectsRulebookError):
                load_item_effect_rules(
                    Path(handle.name), registry=_REGISTRY, buff_definitions=_BUFFS
                )
        finally:
            Path(handle.name).unlink(missing_ok=True)


class EffectVerbShapeTests(unittest.TestCase):
    """Delta: each effect declares exactly one verb."""

    @covers_requirement(
        "item-effect-rulebook::each-effect-declares-exactly-one-verb"
    )
    def test_two_verb_entry_fails(self):
        with self.assertRaises(ItemEffectsRulebookError):
            _load_via_validate(_document({"stat": "hp", "amount": 5, "apply_status": "t_test_buff"}))

    @covers_requirement(
        "item-effect-rulebook::each-effect-declares-exactly-one-verb"
    )
    def test_verbless_entry_with_only_a_scope_fails(self):
        with self.assertRaises(ItemEffectsRulebookError):
            _load_via_validate(_document({"scope": "self"}))

    @covers_requirement(
        "item-effect-rulebook::each-effect-declares-exactly-one-verb"
    )
    def test_entry_with_no_scope_defaults_to_self(self):
        profile = _load_via_validate(_document({"stat": "hp", "amount": 5}))["profiles"][
            "t_test_item"
        ]
        self.assertIs(profile.effects[0].scope, ItemTargetScope.SELF)

    def test_unknown_entry_field_fails(self):
        with self.assertRaises(ItemEffectsRulebookError):
            _load_via_validate(_document({"stat": "hp", "amount": 5, "cleanse": True}))

    @covers_requirement(
        "item-use-resolution::受洗聖水-purges-debuffs-through-an-ordinary-status-removal-effect"
    )
    def test_removal_entry_cannot_carry_an_amount(self):
        # The delta's "Cleanse entry shape is validated" scenario: the
        # removal verb accepts no magnitude.
        with self.assertRaises(ItemEffectsRulebookError):
            _load_via_validate(_document({"remove_status": "negative", "amount": 40}))


class StatAdjustmentTests(unittest.TestCase):
    """Delta: closed stat vocabulary, signed bounded amounts."""

    @covers_requirement(
        "item-effect-rulebook::stat-adjustments-name-a-closed-stat-vocabulary-and-carry-a-signed-bounded-amount"
    )
    def test_negative_amount_is_a_valid_declaration(self):
        profile = _load_via_validate(_document({"stat": "sp", "amount": -12}))["profiles"][
            "t_test_item"
        ]
        self.assertEqual(profile.effects[0], GaugeAdjustEffect(stat=ItemStat.SP, amount=-12))

    @covers_requirement(
        "item-effect-rulebook::stat-adjustments-name-a-closed-stat-vocabulary-and-carry-a-signed-bounded-amount"
    )
    def test_zero_amount_fails(self):
        with self.assertRaises(ItemEffectsRulebookError):
            _load_via_validate(_document({"stat": "hp", "amount": 0}))

    def test_boolean_amount_fails(self):
        with self.assertRaises(ItemEffectsRulebookError):
            _load_via_validate(_document({"stat": "hp", "amount": True}))

    @covers_requirement(
        "item-effect-rulebook::stat-adjustments-name-a-closed-stat-vocabulary-and-carry-a-signed-bounded-amount"
    )
    def test_out_of_bound_magnitude_fails(self):
        with self.assertRaises(ItemEffectsRulebookError):
            _load_via_validate(
                _document({"stat": "hp", "amount": MAX_EFFECT_AMOUNT + 1})
            )
        with self.assertRaises(ItemEffectsRulebookError):
            _load_via_validate(
                _document({"stat": "hp", "amount": -(MAX_EFFECT_AMOUNT + 1)})
            )

    @covers_requirement(
        "item-effect-rulebook::stat-adjustments-name-a-closed-stat-vocabulary-and-carry-a-signed-bounded-amount"
    )
    def test_unknown_stat_fails(self):
        with self.assertRaises(ItemEffectsRulebookError):
            _load_via_validate(_document({"stat": "luck", "amount": 5}))


class StatusVerbTests(unittest.TestCase):
    """Delta: application names a concrete key; removal accepts selectors."""

    @covers_requirement(
        "item-effect-rulebook::status-application-names-a-concrete-definition-status-removal-accepts-selectors"
    )
    def test_selector_under_the_application_verb_fails(self):
        for selector in ("all", "positive", "negative"):
            with self.subTest(selector=selector):
                with self.assertRaises(ItemEffectsRulebookError):
                    _load_via_validate(_document({"apply_status": selector}))

    @covers_requirement(
        "item-effect-rulebook::status-application-names-a-concrete-definition-status-removal-accepts-selectors"
    )
    def test_each_removal_selector_is_accepted(self):
        for selector in ("negative", "positive", "all"):
            with self.subTest(selector=selector):
                profile = _load_via_validate(
                    _document({"remove_status": selector})
                )["profiles"]["t_test_item"]
                self.assertEqual(
                    profile.effects[0], StatusRemoveEffect(selector=selector)
                )

    @covers_requirement(
        "item-effect-rulebook::status-application-names-a-concrete-definition-status-removal-accepts-selectors"
    )
    def test_concrete_removal_key_is_accepted(self):
        profile = _load_via_validate(_document({"remove_status": "t_test_buff"}))[
            "profiles"
        ]["t_test_item"]
        self.assertEqual(
            profile.effects[0], StatusRemoveEffect(selector="t_test_buff")
        )

    @covers_requirement(
        "item-effect-rulebook::status-application-names-a-concrete-definition-status-removal-accepts-selectors"
    )
    def test_unknown_status_key_fails_in_either_position(self):
        with self.assertRaises(ItemEffectsRulebookError):
            _load_via_validate(_document({"apply_status": "t_no_such_buff"}))
        with self.assertRaises(ItemEffectsRulebookError):
            _load_via_validate(_document({"remove_status": "t_no_such_buff"}))


class RegistryAlignmentTests(unittest.TestCase):
    """Delta: rulebook and registry align exactly at startup."""

    @covers_requirement(
        "item-effect-rulebook::the-rulebook-and-the-registry-align-exactly-at-startup"
    )
    def test_orphan_rulebook_entry_fails(self):
        with self.assertRaises(ItemEffectsRulebookError):
            _load_via_validate(
                _document(
                    {"stat": "hp", "amount": 5},
                    items={
                        "t_test_item": {"effects": [{"stat": "hp", "amount": 5}]},
                        "t_test_sword": {"effects": [{"stat": "hp", "amount": 5}]},
                    },
                )
            )

    @covers_requirement(
        "item-effect-rulebook::the-rulebook-and-the-registry-align-exactly-at-startup"
    )
    def test_usable_item_without_an_entry_fails(self):
        with self.assertRaises(ItemEffectsRulebookError):
            _load_via_validate(_document(items={}))

    @covers_requirement(
        "item-effect-rulebook::the-rulebook-and-the-registry-align-exactly-at-startup"
    )
    def test_empty_effect_list_fails(self):
        with self.assertRaises(ItemEffectsRulebookError):
            _load_via_validate(_document(items={"t_test_item": {"effects": []}}))

    def test_item_entry_must_carry_exactly_effects(self):
        with self.assertRaises(ItemEffectsRulebookError):
            _load_via_validate(
                _document(
                    items={"t_test_item": {"effects": [{"stat": "hp", "amount": 5}], "extra": 1}}
                )
            )


class ScopeVocabularyTests(unittest.TestCase):
    """Delta: only the acting entity is accepted until targeting ships."""

    @covers_requirement(
        "item-effect-rulebook::only-the-acting-entity-is-an-accepted-scope-until-item-targeting-ships"
    )
    def test_every_non_self_scope_is_refused_naming_its_owner(self):
        for scope in ("single", "all-allies", "all-enemies", "all"):
            with self.subTest(scope=scope):
                with self.assertRaises(ItemEffectsRulebookError) as caught:
                    _load_via_validate(
                        _document({"stat": "hp", "amount": 5, "scope": scope})
                    )
                self.assertIn("add-item-effect-targeting", str(caught.exception))

    def test_unknown_scope_word_fails(self):
        with self.assertRaises(ItemEffectsRulebookError):
            _load_via_validate(_document({"stat": "hp", "amount": 5, "scope": "party"}))

    def test_scope_vocabulary_is_closed(self):
        self.assertEqual(
            {scope.value for scope in ItemTargetScope},
            {"self", "single", "all-allies", "all-enemies", "all"},
        )


class ProfileShapeTests(unittest.TestCase):
    """Design D3: one stat adjustment per stat per item, ordered effects."""

    def test_two_adjustments_to_one_stat_fail_the_profile(self):
        with self.assertRaises(ItemEffectsRulebookError) as caught:
            _load_via_validate(
                _document(
                    {"stat": "hp", "amount": 5}, {"stat": "hp", "amount": 7}
                )
            )
        self.assertIn("hp", str(caught.exception))

    @covers_requirement(
        "item-effect-rulebook::a-usable-item-s-effects-are-an-ordered-list-bound-by-item-key"
    )
    def test_distinct_stats_and_status_verbs_coexist_in_order(self):
        profile = _load_via_validate(
            _document(
                {"remove_status": "negative"},
                {"stat": "hp", "amount": 5},
                {"apply_status": "t_test_buff"},
                {"stat": "pleasure", "amount": -3},
            )
        )["profiles"]["t_test_item"]
        self.assertEqual(
            profile.effects,
            (
                StatusRemoveEffect(selector="negative"),
                GaugeAdjustEffect(stat=ItemStat.HP, amount=5),
                StatusApplyEffect(status="t_test_buff"),
                GaugeAdjustEffect(stat=ItemStat.PLEASURE, amount=-3),
            ),
        )


class DataclassConstructionTests(unittest.TestCase):
    """Task 2.1: each typed effect rejects a malformed construction."""

    def test_gauge_adjust_rejects_bad_construction(self):
        for kwargs in (
            {"stat": "hp", "amount": 5},
            {"stat": ItemStat.HP, "amount": True},
            {"stat": ItemStat.HP, "amount": 0},
            {"stat": ItemStat.HP, "amount": 5, "scope": "self"},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    GaugeAdjustEffect(**kwargs)

    def test_status_apply_rejects_selectors_and_bad_scope(self):
        for kwargs in (
            {"status": "all"},
            {"status": ""},
            {"status": "t_test_buff", "scope": "all"},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    StatusApplyEffect(**kwargs)

    def test_status_remove_rejects_empty_selector(self):
        with self.assertRaises(ValueError):
            StatusRemoveEffect(selector="")

    def test_profile_rejects_empty_or_foreign_effects(self):
        with self.assertRaises(ValueError):
            ItemEffectProfile(effects=())
        with self.assertRaises(ValueError):
            ItemEffectProfile(effects=("stat:hp",))
        with self.assertRaises(ValueError):
            ItemEffectProfile(
                effects=(
                    GaugeAdjustEffect(stat=ItemStat.HP, amount=1),
                    GaugeAdjustEffect(stat=ItemStat.HP, amount=2),
                )
            )


class LiveBuffTableTests(unittest.TestCase):
    """The default buff table is the live BUFF_DEFINITIONS map."""

    def test_default_buff_definitions_are_the_live_map(self):
        from world.rules.buffs import BUFF_DEFINITIONS

        usable = {
            key: definition
            for key, definition in ITEM_REGISTRY.items()
            if definition.use_mechanics is not None
        }
        document = {
            "item_use_seconds": 6,
            "items": {
                key: {"effects": [{"stat": "hp", "amount": 1}]} for key in usable
            },
        }
        from world.rules.item_effects import validate_item_effect_rules

        loaded = validate_item_effect_rules(document, ITEM_REGISTRY, BUFF_DEFINITIONS)
        self.assertEqual(set(loaded["profiles"]), set(usable))


if __name__ == "__main__":
    unittest.main()
