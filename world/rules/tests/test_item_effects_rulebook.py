"""Validation tests for the declarative item-effect model (consolidate-item-authoring).

A usable item authors its ordered, typed effect list on its own row in
``content/items/``; the runtime mechanics flags stay separate and the shared
out-of-combat use time lives in ``rulebook/item_effects.yaml``. Every
``item-effect-rulebook`` scenario is exercised here against injected catalogs
(fabricated registries, raw inline inputs, buff tables) so no shipped
magnitude or key is restated; the frozen shipped-row contract lives in
``test_shipped_item_use_regression``.
"""

from types import SimpleNamespace
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from world.lore.items import ITEM_REGISTRY, load_item_catalog
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
    scope_targeting_rule,
)

# A fabricated registry/buff table: the validator resolves the usable key set
# through ``use_mechanics``, so a bare namespace suffices.
_USABLE = SimpleNamespace(use_mechanics=SimpleNamespace())
_UNUSABLE = SimpleNamespace(use_mechanics=None)
_REGISTRY = {"t_test_item": _USABLE, "t_test_sword": _UNUSABLE}
_BUFFS = {"t_test_buff": SimpleNamespace(polarity="buff")}


def _document(seconds: int = 6) -> dict:
    return {"item_use_seconds": seconds}


def _inputs(*effect_entries: dict) -> dict:
    return {"t_test_item": list(effect_entries)}


def _load_via_validate(document: dict | None = None, inputs: dict | None = None):
    from world.rules.item_effects import validate_item_effect_rules

    return validate_item_effect_rules(
        document if document is not None else _document(),
        _REGISTRY,
        inputs if inputs is not None else _inputs({"stat": "hp", "amount": 5}),
        _BUFFS,
    )


class CanonicalRulebookTests(unittest.TestCase):
    """The shipped catalog loads, aligns, and stays self-scoped."""

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
        "item-effect-rulebook::an-effect-s-scope-is-fixed-by-the-rulebook-and-maps-to-one-targeting-requirement"
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
            yaml.safe_dump(_document(), handle, allow_unicode=True)
            handle.close()
            loaded = load_item_effect_rules(
                Path(handle.name),
                registry=_REGISTRY,
                use_effect_inputs=_inputs({"stat": "hp", "amount": 5}),
                buff_definitions=_BUFFS,
            )
        finally:
            Path(handle.name).unlink(missing_ok=True)
        self.assertEqual(loaded["item_use_seconds"], 6)
        profile = loaded["profiles"]["t_test_item"]
        self.assertEqual(profile.effects[0].amount, 5)

    def test_duplicate_mapping_keys_fail_loud(self):
        # Fail-loud contract: the loaded data must never silently diverge from
        # the reviewed file.
        text = "item_use_seconds: 6\nitem_use_seconds: 7\n"
        handle = tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        )
        try:
            handle.write(text)
            handle.close()
            with self.assertRaises(ItemEffectsRulebookError):
                load_item_effect_rules(
                    Path(handle.name),
                    registry=_REGISTRY,
                    use_effect_inputs=_inputs({"stat": "hp", "amount": 5}),
                    buff_definitions=_BUFFS,
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
            _load_via_validate(
                inputs=_inputs(
                    {"stat": "hp", "amount": 5, "apply_status": "t_test_buff"}
                )
            )

    @covers_requirement(
        "item-effect-rulebook::each-effect-declares-exactly-one-verb"
    )
    def test_verbless_entry_with_only_a_scope_fails(self):
        with self.assertRaises(ItemEffectsRulebookError):
            _load_via_validate(inputs=_inputs({"scope": "self"}))

    @covers_requirement(
        "item-effect-rulebook::each-effect-declares-exactly-one-verb"
    )
    def test_entry_with_no_scope_defaults_to_self(self):
        profile = _load_via_validate(inputs=_inputs({"stat": "hp", "amount": 5}))[
            "profiles"
        ]["t_test_item"]
        self.assertIs(profile.effects[0].scope, ItemTargetScope.SELF)

    def test_unknown_entry_field_fails(self):
        with self.assertRaises(ItemEffectsRulebookError):
            _load_via_validate(
                inputs=_inputs({"stat": "hp", "amount": 5, "cleanse": True})
            )

    @covers_requirement(
        "item-use-resolution::受洗聖水-purges-debuffs-through-an-ordinary-status-removal-effect"
    )
    def test_removal_entry_cannot_carry_an_amount(self):
        # The delta's "Cleanse entry shape is validated" scenario: the
        # removal verb accepts no magnitude.
        with self.assertRaises(ItemEffectsRulebookError):
            _load_via_validate(
                inputs=_inputs({"remove_status": "negative", "amount": 40})
            )


class StatAdjustmentTests(unittest.TestCase):
    """Delta: closed stat vocabulary, signed bounded amounts."""

    @covers_requirement(
        "item-effect-rulebook::stat-adjustments-name-a-closed-stat-vocabulary-and-carry-a-signed-bounded-amount"
    )
    def test_negative_amount_is_a_valid_declaration(self):
        profile = _load_via_validate(
            inputs=_inputs({"stat": "sp", "amount": -12})
        )["profiles"]["t_test_item"]
        self.assertEqual(
            profile.effects[0], GaugeAdjustEffect(stat=ItemStat.SP, amount=-12)
        )

    @covers_requirement(
        "item-effect-rulebook::stat-adjustments-name-a-closed-stat-vocabulary-and-carry-a-signed-bounded-amount"
    )
    def test_zero_amount_fails(self):
        with self.assertRaises(ItemEffectsRulebookError):
            _load_via_validate(inputs=_inputs({"stat": "hp", "amount": 0}))

    def test_boolean_amount_fails(self):
        with self.assertRaises(ItemEffectsRulebookError):
            _load_via_validate(inputs=_inputs({"stat": "hp", "amount": True}))

    @covers_requirement(
        "item-effect-rulebook::stat-adjustments-name-a-closed-stat-vocabulary-and-carry-a-signed-bounded-amount"
    )
    def test_out_of_bound_magnitude_fails(self):
        with self.assertRaises(ItemEffectsRulebookError):
            _load_via_validate(
                inputs=_inputs({"stat": "hp", "amount": MAX_EFFECT_AMOUNT + 1})
            )
        with self.assertRaises(ItemEffectsRulebookError):
            _load_via_validate(
                inputs=_inputs(
                    {"stat": "hp", "amount": -(MAX_EFFECT_AMOUNT + 1)}
                )
            )

    @covers_requirement(
        "item-effect-rulebook::stat-adjustments-name-a-closed-stat-vocabulary-and-carry-a-signed-bounded-amount"
    )
    def test_unknown_stat_fails(self):
        with self.assertRaises(ItemEffectsRulebookError):
            _load_via_validate(inputs=_inputs({"stat": "luck", "amount": 5}))


class StatusVerbTests(unittest.TestCase):
    """Delta: application names a concrete key; removal accepts selectors."""

    @covers_requirement(
        "item-effect-rulebook::status-application-names-a-concrete-definition-status-removal-accepts-selectors"
    )
    def test_selector_under_the_application_verb_fails(self):
        for selector in ("all", "positive", "negative"):
            with self.subTest(selector=selector):
                with self.assertRaises(ItemEffectsRulebookError):
                    _load_via_validate(
                        inputs=_inputs({"apply_status": selector})
                    )

    @covers_requirement(
        "item-effect-rulebook::status-application-names-a-concrete-definition-status-removal-accepts-selectors"
    )
    def test_each_removal_selector_is_accepted(self):
        for selector in ("negative", "positive", "all"):
            with self.subTest(selector=selector):
                profile = _load_via_validate(
                    inputs=_inputs({"remove_status": selector})
                )["profiles"]["t_test_item"]
                self.assertEqual(
                    profile.effects[0], StatusRemoveEffect(selector=selector)
                )

    @covers_requirement(
        "item-effect-rulebook::status-application-names-a-concrete-definition-status-removal-accepts-selectors"
    )
    def test_concrete_removal_key_is_accepted(self):
        profile = _load_via_validate(
            inputs=_inputs({"remove_status": "t_test_buff"})
        )["profiles"]["t_test_item"]
        self.assertEqual(
            profile.effects[0], StatusRemoveEffect(selector="t_test_buff")
        )

    @covers_requirement(
        "item-effect-rulebook::status-application-names-a-concrete-definition-status-removal-accepts-selectors"
    )
    def test_unknown_status_key_fails_in_either_position(self):
        with self.assertRaises(ItemEffectsRulebookError):
            _load_via_validate(inputs=_inputs({"apply_status": "t_no_such_buff"}))
        with self.assertRaises(ItemEffectsRulebookError):
            _load_via_validate(inputs=_inputs({"remove_status": "t_no_such_buff"}))


class RegistryAlignmentTests(unittest.TestCase):
    """Delta: the catalog and its usable rows align exactly at startup."""

    @covers_requirement(
        "item-effect-rulebook::the-rulebook-and-the-registry-align-exactly-at-startup"
    )
    def test_orphan_rulebook_entry_fails(self):
        with self.assertRaises(ItemEffectsRulebookError) as caught:
            _load_via_validate(
                inputs={
                    "t_test_item": [{"stat": "hp", "amount": 5}],
                    "t_test_sword": [{"stat": "hp", "amount": 5}],
                }
            )
        self.assertIn("t_test_sword", str(caught.exception))

    @covers_requirement(
        "lore-item-catalog::retiring-an-item-key-leaves-no-dangling-reference"
    )
    def test_usable_profile_naming_retired_key_fails_catalog_load(self):
        with self.assertRaises(ItemEffectsRulebookError) as caught:
            _load_via_validate(
                inputs={
                    "t_test_item": [{"stat": "hp", "amount": 5}],
                    "synthetic_retired_item": [{"stat": "hp", "amount": 5}],
                }
            )
        self.assertIn("synthetic_retired_item", str(caught.exception))

    @covers_requirement(
        "lore-item-catalog::retiring-an-item-key-leaves-no-dangling-reference"
    )
    def test_completed_item_effect_retirement_loads_cleanly(self):
        loaded = _load_via_validate(
            inputs={"t_test_item": [{"stat": "hp", "amount": 5}]}
        )
        self.assertEqual(set(loaded["profiles"]), {"t_test_item"})

    @covers_requirement(
        "item-effect-rulebook::the-rulebook-and-the-registry-align-exactly-at-startup"
    )
    def test_usable_item_without_an_entry_fails(self):
        with self.assertRaises(ItemEffectsRulebookError):
            _load_via_validate(inputs={})

    @covers_requirement(
        "item-effect-rulebook::the-rulebook-and-the-registry-align-exactly-at-startup"
    )
    def test_empty_effect_list_fails(self):
        with self.assertRaises(ItemEffectsRulebookError):
            _load_via_validate(inputs={"t_test_item": []})

    def test_effect_list_must_be_a_list(self):
        with self.assertRaises(ItemEffectsRulebookError):
            _load_via_validate(
                inputs={"t_test_item": {"stat": "hp", "amount": 5}}
            )

    def test_effect_entry_must_be_a_mapping(self):
        with self.assertRaises(ItemEffectsRulebookError):
            _load_via_validate(inputs={"t_test_item": [7]})


class ScopeVocabularyTests(unittest.TestCase):
    """Delta: the five-scope vocabulary loads and maps to one targeting rule each."""

    def test_every_scope_value_loads_and_maps_to_its_targeting_rule(self):
        from world.rules.targeting import (
            FactionConstraint,
            TargetRequirement,
            TargetSpec,
        )

        loaded = _load_via_validate(
            inputs=_inputs(
                {"stat": "hp", "amount": 5, "scope": "self"},
                {"stat": "mp", "amount": 5, "scope": "single"},
                {"stat": "sp", "amount": 5, "scope": "all-allies"},
                {"stat": "pleasure", "amount": 5, "scope": "all-enemies"},
                {"apply_status": "t_test_buff", "scope": "all"},
            )
        )
        scopes = [effect.scope for effect in loaded["profiles"]["t_test_item"].effects]
        self.assertEqual(
            scopes,
            [
                ItemTargetScope.SELF,
                ItemTargetScope.SINGLE,
                ItemTargetScope.ALL_ALLIES,
                ItemTargetScope.ALL_ENEMIES,
                ItemTargetScope.ALL,
            ],
        )
        rules = {scope: scope_targeting_rule(scope) for scope in ItemTargetScope}
        self.assertEqual(
            rules[ItemTargetScope.SELF].requirement,
            TargetRequirement(TargetSpec.SELF, FactionConstraint.SELF_ONLY),
        )
        self.assertIsNone(rules[ItemTargetScope.SELF].shorthand)
        self.assertEqual(
            rules[ItemTargetScope.SINGLE].requirement,
            TargetRequirement(TargetSpec.SINGLE),
        )
        self.assertIsNone(rules[ItemTargetScope.SINGLE].shorthand)
        for scope, shorthand in (
            (ItemTargetScope.ALL_ALLIES, "all-allies"),
            (ItemTargetScope.ALL_ENEMIES, "all-enemies"),
            (ItemTargetScope.ALL, "all"),
        ):
            with self.subTest(scope=scope):
                self.assertEqual(
                    rules[scope].requirement,
                    TargetRequirement(TargetSpec.AREA),
                )
                self.assertEqual(rules[scope].shorthand, shorthand)

    def test_unknown_scope_word_fails(self):
        with self.assertRaises(ItemEffectsRulebookError):
            _load_via_validate(
                inputs=_inputs({"stat": "hp", "amount": 5, "scope": "party"})
            )

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
                inputs=_inputs(
                    {"stat": "hp", "amount": 5}, {"stat": "hp", "amount": 7}
                )
            )
        self.assertIn("hp", str(caught.exception))

    @covers_requirement(
        "item-effect-rulebook::a-usable-item-s-effects-are-an-ordered-list-bound-by-item-key"
    )
    def test_distinct_stats_and_status_verbs_coexist_in_order(self):
        profile = _load_via_validate(
            inputs=_inputs(
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
        inputs = {
            key: [{"stat": "hp", "amount": 1}] for key in usable
        }
        from world.rules.item_effects import validate_item_effect_rules

        loaded = validate_item_effect_rules(
            _document(), ITEM_REGISTRY, inputs, BUFF_DEFINITIONS
        )
        self.assertEqual(set(loaded["profiles"]), set(usable))


def _temp_catalog_append(row: dict) -> Path:
    """Copy the shipped catalog into a temp dir and append ``row`` to one file."""
    source = Path(__file__).resolve().parents[3] / "content" / "items"
    root = Path(tempfile.mkdtemp())
    target = root / "items"
    shutil.copytree(source, target)
    manifest = yaml.safe_load((target / "catalog.yaml").read_text(encoding="utf-8"))
    listed = target / manifest["files"][0]
    document = yaml.safe_load(listed.read_text(encoding="utf-8"))
    document["items"].append(row)
    listed.write_text(
        yaml.safe_dump(document, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return target


_APPENDED_ROW = {
    "key": "t_append_cleanse",
    "display_name_zh": "合成淨化劑",
    "price_table_key": "t_mossmeals",
    "sellable": True,
    "presentation": {
        "kind": "potion",
        "icon_key": "potion",
        "rarity": "common",
        "summary_zh": "供作者流程驗證使用的合成淨化劑。",
    },
    "use_mechanics": {
        "consumable": True,
        "combat_allowed": True,
        # Order is load-bearing: removal first, then the poisoned application,
        # so a settled result proves the authored list order.
        "effects": [
            {"remove_status": "negative"},
            {"apply_status": "poisoned"},
        ],
    },
}


class OneRowAppendAcceptanceTests(unittest.TestCase):
    """Task 1.4: one authored row reaches the real loaders and the use path."""

    @covers_requirement(
        "item-effect-rulebook::a-usable-item-s-effects-are-an-ordered-list-bound-by-item-key"
    )
    def test_appended_row_loads_through_the_production_loaders(self):
        from world.rules.buffs import BUFF_DEFINITIONS
        from world.rules.equipment_effects import load_equipment_effect_rules

        root = _temp_catalog_append(_APPENDED_ROW)
        self.addCleanup(shutil.rmtree, root, True)
        catalog = load_item_catalog(root)
        rulebook = (
            Path(__file__).resolve().parents[1] / "rulebook" / "item_effects.yaml"
        )
        loaded = load_item_effect_rules(
            path=rulebook,
            registry=catalog.definitions,
            use_effect_inputs=catalog.use_effect_inputs,
            buff_definitions=BUFF_DEFINITIONS,
            sources=catalog.sources,
        )
        equipment = load_equipment_effect_rules(
            registry=catalog.definitions,
            equipment_effect_inputs=catalog.equipment_effect_inputs,
            buff_definitions=BUFF_DEFINITIONS,
            sources=catalog.sources,
        )
        self.assertIn(_APPENDED_ROW["key"], loaded["profiles"])
        self.assertEqual(
            [type(effect).__name__ for effect in loaded["profiles"][_APPENDED_ROW["key"]].effects],
            ["StatusRemoveEffect", "StatusApplyEffect"],
        )
        self.assertIn("plain_sword", equipment)


class AppendedRowUseAcceptanceTests(EvenniaTest):
    """A settled use of the appended row, on a reloaded legacy-shaped actor."""

    def _scope(self, catalog, loaded, equipment):
        from world.rules.tests._combat_session_helpers import open_synthetic_scope

        open_synthetic_scope(
            self,
            "items",
            extra={
                "items": dict(catalog.definitions),
                "item_effect_profiles": dict(loaded["profiles"]),
                "equipment_effect_rules": dict(equipment),
            },
        )

    def test_appended_use_is_ordered_and_charges_the_shared_time(self):
        from evennia.objects.models import ObjectDB
        from evennia.utils.create import create_object
        from typeclasses.characters import PlayerCharacter
        from world.rules.buffs import BUFF_DEFINITIONS, entity_active_buffs
        from world.rules.clock import WorldClock
        from world.rules.equipment_effects import load_equipment_effect_rules
        from world.rules.items import use_item
        from world.skills.equipment import list_items

        root = _temp_catalog_append(_APPENDED_ROW)
        self.addCleanup(shutil.rmtree, root, True)
        catalog = load_item_catalog(root)
        rulebook = (
            Path(__file__).resolve().parents[1] / "rulebook" / "item_effects.yaml"
        )
        loaded = load_item_effect_rules(
            path=rulebook,
            registry=catalog.definitions,
            use_effect_inputs=catalog.use_effect_inputs,
            buff_definitions=BUFF_DEFINITIONS,
            sources=catalog.sources,
        )
        equipment = load_equipment_effect_rules(
            registry=catalog.definitions,
            equipment_effect_inputs=catalog.equipment_effect_inputs,
            buff_definitions=BUFF_DEFINITIONS,
            sources=catalog.sources,
        )
        self._scope(catalog, loaded, equipment)

        actor = create_object(PlayerCharacter, key="append acceptance actor")
        actor.race = "human"
        actor.apply_race_baseline()
        legacy_equipment = {
            "weapon_main": "plain_sword",
            "weapon_off": None,
            "armor": None,
            "accessories": [],
        }
        actor.db.inventory = [_APPENDED_ROW["key"]]
        actor.db.equipment = dict(legacy_equipment)
        actor.save()
        for model in (ObjectDB,):
            model.flush_instance_cache(force=True)
        fresh = PlayerCharacter.objects.get(pk=actor.pk)
        self.assertIsNot(fresh, actor)

        clock = WorldClock()
        settlement = use_item(fresh, _APPENDED_ROW["key"], clock=clock)
        self.assertEqual(settlement.result.outcome, "success")
        self.assertIn("poisoned", entity_active_buffs(fresh))
        self.assertEqual(list_items(fresh), [])
        self.assertEqual(dict(fresh.db.equipment), legacy_equipment)
        self.assertEqual(clock.tick, ITEM_USE_SECONDS)

        # Cross-key control: another usable row keeps its own effects.
        control = create_object(PlayerCharacter, key="append control actor")
        control.race = "human"
        control.apply_race_baseline()
        maximum = int(control.traits.hp.max)
        control.traits.hp.current = maximum - 60
        control.db.inventory = ["healing_potion"]
        before = int(control.traits.hp.current)
        control_clock = WorldClock()
        control_result = use_item(control, "healing_potion", clock=control_clock)
        self.assertEqual(control_result.result.outcome, "success")
        self.assertGreater(int(control.traits.hp.current), before)
        self.assertNotIn("poisoned", entity_active_buffs(control))
        self.assertEqual(control_clock.tick, ITEM_USE_SECONDS)


if __name__ == "__main__":
    unittest.main()
