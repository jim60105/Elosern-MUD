"""Data-contract test: equipment effect rulebook contract
Validation tests for the equipment-effect rulebook loader.

Pure unittest. Deviant rulebook copies are built by mutating a fresh parse
of the canonical YAML and loading it through the path override, so every
rejection case is exactly one deviation from the shipped data. The
synthetic-registry cases (orphan entry, unbound equipment key, duplicate
modifier bindings) run through the loader's injectable-registry seam,
because the production dict cannot produce them: every modifier key value
equals its item key.
"""

from tools.spec_traceability import covers_requirement

import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import MappingProxyType, SimpleNamespace

import yaml

from world.lore.economy import PRICE_TABLE
from world.lore.items import (
    ITEM_REGISTRY,
    EquipmentModifierKey,
    ItemDefinition,
    ItemRarity,
)
from world.lore.shops import SHOP_REGISTRY
from world.rules.buffs import BUFF_DEFINITIONS
from world.rules.equipment_effects import (
    EQUIPMENT_EFFECT_RULES,
    EquipmentEffectRule,
    EquipmentEffectsRulebookError,
    equipment_adjustment_text,
    load_equipment_effect_rules,
    reload_equipment_effect_rules,
    validate_equipment_effect_rules,
)

_CANONICAL_PATH = Path(__file__).parents[1] / "rulebook" / "equipment_effects.yaml"


def _canonical_document() -> dict:
    return yaml.safe_load(_CANONICAL_PATH.read_text(encoding="utf-8"))


def _write_rulebook(document: dict) -> Path:
    handle = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    yaml.safe_dump(document, handle, allow_unicode=True)
    handle.close()
    return Path(handle.name)


class EquipmentEffectRulebookTests(unittest.TestCase):
    def _expect_rejection(self, mutate) -> None:
        document = _canonical_document()
        mutate(document)
        with self.assertRaises(EquipmentEffectsRulebookError):
            load_equipment_effect_rules(_write_rulebook(document))

    # --- canonical data -------------------------------------------------------

    @covers_requirement(
        "equipment-effects::the-equipment-effect-rulebook-validates-a-closed-schema-at-load-time"
    )
    def test_canonical_rulebook_loads_the_full_roster(self):
        loaded = load_equipment_effect_rules()
        self.assertEqual(len(loaded), 62)
        self.assertEqual(
            set(loaded),
            {
                definition.modifier_key
                for definition in ITEM_REGISTRY.values()
                if definition.equipment_slot is not None
            },
        )
        self.assertEqual(dict(EQUIPMENT_EFFECT_RULES), loaded)

    @covers_requirement(
        "equipment-effects::the-equipment-effect-rulebook-validates-a-closed-schema-at-load-time"
    )
    def test_reload_is_idempotent(self):
        before = dict(EQUIPMENT_EFFECT_RULES)
        reload_equipment_effect_rules()
        reload_equipment_effect_rules()
        self.assertEqual(dict(EQUIPMENT_EFFECT_RULES), before)

    @covers_requirement(
        "equipment-effects::the-equipment-effect-rulebook-validates-a-closed-schema-at-load-time"
    )
    def test_valid_override_path_loads(self):
        document = _canonical_document()
        document["effects"]["wooden_club"]["adjustments"]["atk_phys"] = 4
        loaded = load_equipment_effect_rules(_write_rulebook(document))
        self.assertEqual(
            loaded[EquipmentModifierKey.WOODEN_CLUB].adjustments["atk_phys"], 4
        )

    @covers_requirement(
        "equipment-effects::equipment-items-bind-one-to-one-to-a-closed-effect-identity"
    )
    def test_storage_pouch_is_explicitly_empty(self):
        rule = EQUIPMENT_EFFECT_RULES[EquipmentModifierKey.STORAGE_POUCH]
        self.assertEqual(dict(rule.adjustments), {})
        self.assertEqual(dict(rule.gauge_caps), {})
        self.assertEqual(rule.immune, ())
        self.assertEqual(rule.attached_buffs, ())
        self.assertEqual(rule.exposure_bias, 0)

    # --- closed vocabularies ---------------------------------------------------

    @covers_requirement(
        "equipment-effects::the-equipment-effect-rulebook-validates-a-closed-schema-at-load-time"
    )
    def test_unknown_top_level_key_is_rejected(self):
        self._expect_rejection(lambda d: d.update({"stray": 1}))

    @covers_requirement(
        "equipment-effects::the-equipment-effect-rulebook-validates-a-closed-schema-at-load-time"
    )
    def test_missing_top_level_key_is_rejected(self):
        self._expect_rejection(lambda d: d.pop("budgets"))

    @covers_requirement(
        "equipment-effects::the-equipment-effect-rulebook-validates-a-closed-schema-at-load-time"
    )
    def test_non_mapping_root_is_rejected(self):
        with self.assertRaises(EquipmentEffectsRulebookError):
            load_equipment_effect_rules(
                _write_rulebook({"budgets": [], "effects": {}})
            )

    @covers_requirement(
        "equipment-effects::the-equipment-effect-rulebook-validates-a-closed-schema-at-load-time"
    )
    def test_unknown_entry_field_is_rejected(self):
        self._expect_rejection(
            lambda d: d["effects"]["wooden_club"].update({"damage_aura": 9})
        )

    @covers_requirement(
        "equipment-effects::the-equipment-effect-rulebook-validates-a-closed-schema-at-load-time"
    )
    def test_unknown_adjustment_field_is_rejected(self):
        self._expect_rejection(
            lambda d: d["effects"]["wooden_club"]["adjustments"].update({"luck": 4})
        )

    @covers_requirement(
        "equipment-effects::the-equipment-effect-rulebook-validates-a-closed-schema-at-load-time"
    )
    def test_entry_that_is_not_a_mapping_is_rejected(self):
        self._expect_rejection(lambda d: d["effects"].update({"wooden_club": 7}))

    # --- percent/flat kinds ------------------------------------------------------

    @covers_requirement(
        "equipment-effects::the-equipment-effect-rulebook-validates-a-closed-schema-at-load-time"
    )
    def test_flat_int_on_percent_field_is_rejected(self):
        self._expect_rejection(
            lambda d: d["effects"]["knight_platemail"]["adjustments"].update(
                {"mp_cost": -5}
            )
        )

    @covers_requirement(
        "equipment-effects::the-equipment-effect-rulebook-validates-a-closed-schema-at-load-time"
    )
    def test_percent_string_on_flat_field_is_rejected(self):
        self._expect_rejection(
            lambda d: d["effects"]["plain_sword"]["adjustments"].update(
                {"atk_phys": "+3%"}
            )
        )

    @covers_requirement(
        "equipment-effects::the-equipment-effect-rulebook-validates-a-closed-schema-at-load-time"
    )
    def test_malformed_percent_strings_are_rejected(self):
        # "+١%" is an Arabic-Indic digit: the grammar is ASCII-only because
        # int() would otherwise silently accept it.
        for value in ("10%", "5", "-10", "", "+", "-1O%", "5pct", "+١%", True, 10):
            with self.subTest(value=value):
                self._expect_rejection(
                    lambda d, value=value: d["effects"]["knight_platemail"][
                        "adjustments"
                    ].update({"agility": value})
                )

    @covers_requirement(
        "equipment-effects::the-equipment-effect-rulebook-validates-a-closed-schema-at-load-time"
    )
    def test_bool_on_flat_field_is_rejected(self):
        self._expect_rejection(
            lambda d: d["effects"]["wooden_club"]["adjustments"].update(
                {"atk_phys": True}
            )
        )

    @covers_requirement(
        "equipment-effects::the-equipment-effect-rulebook-validates-a-closed-schema-at-load-time"
    )
    def test_bool_on_exposure_bias_is_rejected(self):
        self._expect_rejection(
            lambda d: d["effects"]["black_maid_dress"].update({"exposure_bias": True})
        )

    # --- raw-text malformed YAML ------------------------------------------------

    def _write_raw(self, text: str) -> Path:
        handle = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        handle.write(text)
        handle.close()
        return Path(handle.name)

    @covers_requirement(
        "equipment-effects::the-equipment-effect-rulebook-validates-a-closed-schema-at-load-time"
    )
    def test_duplicate_keys_at_every_nesting_level_are_rejected(self):
        # PyYAML's default loader silently keeps the LAST duplicate, so the
        # reviewed file and the loaded data could disagree. Fail-loud
        # contract: the custom loader must reject duplicates anywhere, even
        # before any schema validation would notice.
        # Each text also carries a schema-malformed (empty) budgets block, so
        # the assertion pins the loader's duplicate-key diagnostic: without
        # it, a regressed guard could still "pass" via a later schema error.
        for text in (
            "budgets: {}\neffects: {}\nbudgets: {}\n",
            "budgets: {}\neffects:\n"
            "  wooden_club: {adjustments: {atk_phys: 1}}\n"
            "  wooden_club: {adjustments: {atk_phys: 2}}\n",
            "budgets: {}\neffects:\n"
            "  wooden_club:\n"
            "    adjustments: {atk_phys: 1, atk_phys: 2}\n",
        ):
            with self.subTest(text=text):
                with self.assertRaises(EquipmentEffectsRulebookError) as caught:
                    load_equipment_effect_rules(self._write_raw(text))
                self.assertIn("duplicate YAML mapping key", str(caught.exception))

    # --- budgets ------------------------------------------------------------------

    @covers_requirement(
        "equipment-effects::per-rarity-budgets-mechanically-bound-every-authored-value"
    )
    def test_flat_budget_overflow_is_rejected(self):
        # wooden_club is common (flat ceiling 4).
        self._expect_rejection(
            lambda d: d["effects"]["wooden_club"]["adjustments"].update(
                {"atk_phys": 5}
            )
        )

    @covers_requirement(
        "equipment-effects::per-rarity-budgets-mechanically-bound-every-authored-value"
    )
    def test_flat_negative_budget_overflow_is_rejected(self):
        self._expect_rejection(
            lambda d: d["effects"]["wooden_club"]["adjustments"].update(
                {"atk_phys": -5}
            )
        )

    @covers_requirement(
        "equipment-effects::per-rarity-budgets-mechanically-bound-every-authored-value"
    )
    def test_percent_budget_overflow_is_rejected(self):
        # knight_platemail is rare (percent ceiling 10).
        self._expect_rejection(
            lambda d: d["effects"]["knight_platemail"]["adjustments"].update(
                {"agility": "-11%"}
            )
        )

    @covers_requirement(
        "equipment-effects::per-rarity-budgets-mechanically-bound-every-authored-value"
    )
    def test_soft_percent_budget_overflow_is_rejected(self):
        # pilgrim_medallion is uncommon (soft_percent ceiling 15).
        self._expect_rejection(
            lambda d: d["effects"]["pilgrim_medallion"]["adjustments"].update(
                {"heal_gain": "+16%"}
            )
        )

    @covers_requirement(
        "equipment-effects::per-rarity-budgets-mechanically-bound-every-authored-value"
    )
    def test_bias_budget_overflow_is_rejected(self):
        # black_maid_dress is uncommon (bias ceiling 1).
        self._expect_rejection(
            lambda d: d["effects"]["black_maid_dress"].update({"exposure_bias": 2})
        )

    @covers_requirement(
        "equipment-effects::per-rarity-budgets-mechanically-bound-every-authored-value"
    )
    def test_negative_bias_budget_overflow_is_rejected(self):
        # abs() counts against the uncommon bias ceiling of 1.
        self._expect_rejection(
            lambda d: d["effects"]["black_maid_dress"].update({"exposure_bias": -2})
        )

    @covers_requirement(
        "equipment-effects::per-rarity-budgets-mechanically-bound-every-authored-value"
    )
    def test_gauge_budget_overflow_is_rejected(self):
        # knight_platemail is rare (gauge ceiling 15).
        self._expect_rejection(
            lambda d: d["effects"]["knight_platemail"]["gauge_caps"].update({"hp": 16})
        )

    @covers_requirement(
        "equipment-effects::per-rarity-budgets-mechanically-bound-every-authored-value"
    )
    def test_non_positive_or_malformed_gauge_cap_is_rejected(self):
        for cap in (-5, 0, True, "10", 25.5):
            with self.subTest(cap=cap):
                self._expect_rejection(
                    lambda d, cap=cap: d["effects"]["knight_platemail"][
                        "gauge_caps"
                    ].update({"hp": cap})
                )

    @covers_requirement(
        "equipment-effects::the-equipment-effect-rulebook-validates-a-closed-schema-at-load-time"
    )
    def test_unknown_gauge_target_is_rejected(self):
        self._expect_rejection(
            lambda d: d["effects"]["knight_platemail"]["gauge_caps"].update(
                {"stamina": 1}
            )
        )

    @covers_requirement(
        "equipment-effects::per-rarity-budgets-mechanically-bound-every-authored-value"
    )
    def test_budgets_table_malformations_are_rejected(self):
        def rename_rarity(d):
            d["budgets"]["mythic"] = d["budgets"].pop("legendary")

        def drop_rarity(d):
            d["budgets"].pop("legendary")

        def rename_column(d):
            d["budgets"]["common"]["luck"] = d["budgets"]["common"].pop("flat")

        def drop_column(d):
            d["budgets"]["common"].pop("gauge")

        mutations = {
            "unknown-rarity": rename_rarity,
            "missing-rarity": drop_rarity,
            "unknown-column": rename_column,
            "missing-column": drop_column,
            "boolean-cell": lambda d: d["budgets"]["common"].update({"flat": True}),
            "zero-cell": lambda d: d["budgets"]["common"].update({"flat": 0}),
            "negative-cell": lambda d: d["budgets"]["common"].update({"flat": -1}),
            "float-cell": lambda d: d["budgets"]["common"].update({"flat": 4.5}),
        }
        for name, mutate in mutations.items():
            with self.subTest(case=name):
                self._expect_rejection(mutate)

    # --- buff references ------------------------------------------------------------

    @covers_requirement(
        "equipment-effects::state-effect-references-resolve-against-the-buff-rulebook"
    )
    def test_unknown_buff_reference_is_rejected(self):
        for field in ("immune", "attached_buffs"):
            with self.subTest(field=field):
                self._expect_rejection(
                    lambda d, field=field: d["effects"]["purified_pendant"].update(
                        {field: ["bogus_buff"]}
                    )
                )

    @covers_requirement(
        "equipment-effects::state-effect-references-resolve-against-the-buff-rulebook"
    )
    def test_self_contradictory_entry_is_rejected(self):
        self._expect_rejection(
            lambda d: d["effects"]["purified_pendant"].update(
                {"attached_buffs": ["poisoned"]}
            )
        )
    @covers_requirement(
        "equipment-effects::attached-buffs-never-carry-gauge-ceiling-modifiers"
    )
    def test_attached_buff_with_gauge_bounds_is_rejected(self):
        # Synthetic rulebook-copy buffs with gauge-bound modifiers must be
        # rejected for attached entries: attached instances never carry
        # gauge-ceiling modifiers (P3 design D2).
        document = _canonical_document()
        document["effects"]["apothecary_beads"]["attached_buffs"] = [
            "test_gauge_bounds_buff"
        ]
        buff_definitions = dict(BUFF_DEFINITIONS)
        buff_definitions["test_gauge_bounds_buff"] = replace(
            BUFF_DEFINITIONS["focus"],
            key="test_gauge_bounds_buff",
            modifiers={"bounds": {"target": "hp", "ceiling": 5}},
        )
        registry = {
            definition.key: definition
            for definition in ITEM_REGISTRY.values()
            if definition.equipment_slot is not None
        }
        with self.assertRaises(EquipmentEffectsRulebookError):
            validate_equipment_effect_rules(
                document, registry, buff_definitions
            )

    @covers_requirement(
        "equipment-effects::attached-buffs-never-carry-gauge-ceiling-modifiers"
    )
    def test_attached_regen_rate_buff_is_accepted(self):
        # item_regen_light's HP rate is the shipped attached-buff precedent
        # and must keep validating (rates are not ceiling modifiers).
        loaded = load_equipment_effect_rules()
        self.assertEqual(
            loaded[EquipmentModifierKey.APOTHECARY_BEADS].attached_buffs,
            ("item_regen_light",),
        )

    @covers_requirement(
        "equipment-effects::state-effect-references-resolve-against-the-buff-rulebook"
    )
    def test_duplicate_buff_list_members_are_rejected(self):
        self._expect_rejection(
            lambda d: d["effects"]["purified_pendant"].update(
                {"immune": ["poisoned", "poisoned"]}
            )
        )

    @covers_requirement(
        "equipment-effects::state-effect-references-resolve-against-the-buff-rulebook"
    )
    def test_malformed_buff_list_members_are_rejected(self):
        for member in (True, 1, {"a": 1}):
            with self.subTest(member=member):
                self._expect_rejection(
                    lambda d, member=member: d["effects"]["purified_pendant"].update(
                        {"immune": [member]}
                    )
                )

    @covers_requirement(
        "equipment-effects::state-effect-references-resolve-against-the-buff-rulebook"
    )
    def test_buff_reference_as_bare_string_is_rejected(self):
        self._expect_rejection(
            lambda d: d["effects"]["purified_pendant"].update({"immune": "poisoned"})
        )

    # --- triple bijection (injectable registry seam) -----------------------------------

    def _two_entry_setup(self):
        registry = {
            "wooden_club": ITEM_REGISTRY["wooden_club"],
            "knight_platemail": ITEM_REGISTRY["knight_platemail"],
        }
        document = {
            "budgets": _canonical_document()["budgets"],
            "effects": {
                "wooden_club": {"adjustments": {"atk_phys": 3, "agility": -2}},
                "knight_platemail": {
                    "adjustments": {
                        "atk_phys": -2,
                        "defense": 8,
                        "agility": "-10%",
                    },
                    "gauge_caps": {"hp": 15},
                },
            },
        }
        return registry, document

    def _validate(self, registry, document):
        return validate_equipment_effect_rules(document, registry, BUFF_DEFINITIONS)

    @covers_requirement(
        "equipment-effects::equipment-items-bind-one-to-one-to-a-closed-effect-identity"
    )
    def test_injectable_registry_happy_path_loads(self):
        registry, document = self._two_entry_setup()
        rules = self._validate(registry, document)
        self.assertEqual(
            set(rules),
            {EquipmentModifierKey.WOODEN_CLUB, EquipmentModifierKey.KNIGHT_PLATEMAIL},
        )

    @covers_requirement(
        "equipment-effects::equipment-items-bind-one-to-one-to-a-closed-effect-identity"
    )
    def test_orphan_entry_is_rejected(self):
        registry, document = self._two_entry_setup()
        del registry["knight_platemail"]
        with self.assertRaises(EquipmentEffectsRulebookError) as caught:
            self._validate(registry, document)
        self.assertIn("knight_platemail", str(caught.exception))

    @covers_requirement(
        "equipment-effects::equipment-items-bind-one-to-one-to-a-closed-effect-identity"
    )
    def test_unbound_equipment_key_is_rejected(self):
        registry, document = self._two_entry_setup()
        registry["chainmail"] = ITEM_REGISTRY["chainmail"]
        with self.assertRaises(EquipmentEffectsRulebookError) as caught:
            self._validate(registry, document)
        self.assertIn("chainmail", str(caught.exception))

    @covers_requirement(
        "lore-item-catalog::retiring-an-item-key-leaves-no-dangling-reference"
    )
    def test_retired_equipment_entry_and_binding_fail_closed_naming_key(self):
        registry, document = self._two_entry_setup()
        del registry["knight_platemail"]
        with self.assertRaises(EquipmentEffectsRulebookError) as caught:
            self._validate(registry, document)
        self.assertIn("knight_platemail", str(caught.exception))

    @covers_requirement(
        "lore-item-catalog::retiring-an-item-key-leaves-no-dangling-reference"
    )
    def test_completed_equipment_retirement_loads_cleanly(self):
        registry, document = self._two_entry_setup()
        del registry["knight_platemail"]
        del document["effects"]["knight_platemail"]
        rules = self._validate(registry, document)
        self.assertEqual(set(rules), {EquipmentModifierKey.WOODEN_CLUB})

    @covers_requirement(
        "equipment-effects::equipment-items-bind-one-to-one-to-a-closed-effect-identity"
    )
    def test_duplicate_modifier_binding_is_rejected(self):
        # Borrowing another item's binding is the hijack this guards: the
        # load-time identity rule (value must equal the item's own key)
        # rejects it first; the post-loop collapse check remains as
        # defence in depth. Unreachable through the production dict either
        # way, so the injectable seam carries the case.
        registry, document = self._two_entry_setup()
        registry["iron_shield"] = replace(
            ITEM_REGISTRY["iron_shield"],
            modifier_key=EquipmentModifierKey.WOODEN_CLUB,
        )
        with self.assertRaises(EquipmentEffectsRulebookError):
            self._validate(registry, document)

    @covers_requirement(
        "equipment-effects::equipment-items-bind-one-to-one-to-a-closed-effect-identity"
    )
    def test_non_equipment_with_modifier_key_is_rejected(self):
        # Construction validation normally bars this shape; the loader
        # re-checks defensively. A frozen dataclass cannot be replaced into
        # the shape, so the synthetic registry row is a bare namespace.
        registry, document = self._two_entry_setup()
        registry["meal"] = SimpleNamespace(equipment_slot=None, modifier_key="meal")
        with self.assertRaises(EquipmentEffectsRulebookError):
            self._validate(registry, document)

    @covers_requirement(
        "equipment-effects::per-rarity-budgets-mechanically-bound-every-authored-value"
    )
    def test_override_cannot_redefine_registry_rarity(self):
        # Budget lookup follows the REAL registry rarity: the untouched
        # budgets table still rejects a common club exceeding flat 4.
        self._expect_rejection(
            lambda d: d["effects"]["wooden_club"]["adjustments"].update(
                {"atk_phys": 5}
            )
        )

    @covers_requirement(
        "equipment-effects::registration-and-tradeability-are-independent"
    )
    def test_unstocked_equipment_item_loads_clean(self):
        registry, document = self._two_entry_setup()
        self.assertNotIn("wooden_club", SHOP_REGISTRY["altoria_general_store"].offered_item_keys)
        rules = self._validate(registry, document)
        self.assertIn(EquipmentModifierKey.WOODEN_CLUB, rules)
        self.assertEqual(rules[EquipmentModifierKey.WOODEN_CLUB].adjustments["atk_phys"], 3)
        from world.rules.guild_config import validate_shop_configs
        economy_path = Path(__file__).parents[1] / "rulebook" / "guild_economy.yaml"
        raw_economy = yaml.safe_load(economy_path.read_text(encoding="utf-8"))
        configs = validate_shop_configs(raw_economy["shops"])
        self.assertFalse(
            any(offer.item_key == "wooden_club" for offer in configs["altoria_general_store"].offers)
        )

    @covers_requirement(
        "equipment-effects::per-rarity-budgets-mechanically-bound-every-authored-value"
    )
    def test_rulebook_load_rejects_over_budget_entry(self):
        registry, document = self._two_entry_setup()
        document["effects"]["wooden_club"] = {"adjustments": {"defense": 10}}
        with self.assertRaises(EquipmentEffectsRulebookError) as caught:
            self._validate(registry, document)
        self.assertIn("defense", str(caught.exception))
        self.assertIn("4", str(caught.exception))


class EquipmentRosterCoverageTests(unittest.TestCase):
    """The 62-key bijection plus the ten Church/Kingdom items' trade identity."""

    NEW_ITEM_KEYS = (
        "purified_pendant",
        "fearless_brooch",
        "knight_platemail",
        "apothecary_beads",
        "archmage_mending_robe",
        "enticing_lace_set",
        "passion_silk_choker",
        "sister_vestments",
        "radiant_holy_emblem",
        "saintess_vestments",
    )

    @covers_requirement(
        "equipment-effects::equipment-items-bind-one-to-one-to-a-closed-effect-identity"
    )
    def test_enum_registry_and_rulebook_are_triple_bijective(self):
        equipment_keys = {
            definition.key
            for definition in ITEM_REGISTRY.values()
            if definition.equipment_slot is not None
        }
        enum_values = {member.value for member in EquipmentModifierKey}
        self.assertEqual(equipment_keys, enum_values)
        self.assertEqual(enum_values, set(EQUIPMENT_EFFECT_RULES))
        self.assertEqual(len(enum_values), 62)
        for member in EquipmentModifierKey:
            self.assertEqual(member.value, member.name.lower())
        for definition in ITEM_REGISTRY.values():
            if definition.equipment_slot is not None:
                self.assertEqual(definition.modifier_key.value, definition.key)

    @covers_requirement(
        "equipment-effects::the-new-equipment-roster-is-registered-and-tradeable"
    )
    def test_new_items_are_registered_offered_and_price_resolvable(self):
        shop = SHOP_REGISTRY["altoria_general_store"]
        for key in self.NEW_ITEM_KEYS:
            with self.subTest(item=key):
                definition = ITEM_REGISTRY[key]
                self.assertIsNotNone(definition.equipment_slot)
                self.assertIsNotNone(definition.modifier_key)
                self.assertTrue(definition.sellable)
                self.assertIn(definition.price_table_key, PRICE_TABLE)
                self.assertIn(key, shop.offered_item_keys)
                self.assertIn(definition.modifier_key, EQUIPMENT_EFFECT_RULES)

    @covers_requirement(
        "equipment-effects::the-new-equipment-roster-is-registered-and-tradeable"
    )
    def test_every_equipment_price_table_key_resolves(self):
        for key, definition in ITEM_REGISTRY.items():
            with self.subTest(item=key):
                self.assertIn(definition.price_table_key, PRICE_TABLE)


CHURCH_VESTMENTS_AND_EMBLEMS = (
    "sister_vestments",
    "radiant_holy_emblem",
    "saintess_vestments",
    "pilgrim_medallion",
)

CHURCH_SANCTUARY_DEVICES = (
    "nymph_buds_clamp",
    "warm_honey_orb",
    "hyperesthesia_charm",
)


def _percent_magnitude(value: str) -> int:
    return int(value[:-1])


def check_church_vestments_and_emblems(
    rules, keys=CHURCH_VESTMENTS_AND_EMBLEMS
) -> None:
    """Raise ValueError when one named Church vestment or emblem breaks doctrine.

    Canon (坦露與歡愉為正向、光之治療與淨化): non-negative exposure bias and
    pleasure, at least one of heal_gain or an immunity, no suppression
    values. Ordinary combat trade-offs remain permitted.
    """
    for key in keys:
        rule = rules[EquipmentModifierKey(key)]
        if rule.exposure_bias < 0:
            raise ValueError(f"{key}: negative exposure_bias suppresses canon")
        pleasure = rule.adjustments.get("pleasure_gain")
        if pleasure is not None and _percent_magnitude(pleasure) < 0:
            raise ValueError(f"{key}: negative pleasure_gain suppresses canon")
        heal = rule.adjustments.get("heal_gain")
        if heal is not None and _percent_magnitude(heal) < 0:
            raise ValueError(f"{key}: negative heal_gain breaks healing canon")
        has_heal = heal is not None and _percent_magnitude(heal) > 0
        if not has_heal and not rule.immune:
            raise ValueError(
                f"{key}: neither heal_gain nor an immunity breaks healing canon"
            )


def check_church_sanctuary_devices(
    rules, keys=CHURCH_SANCTUARY_DEVICES
) -> None:
    """Raise ValueError when one named Church sanctuary device breaks doctrine.

    Sanctuary devices: non-negative exposure_bias, positive pleasure_gain,
    no suppression values. Healing-or-immunity is NOT required.
    """
    for key in keys:
        rule = rules[EquipmentModifierKey(key)]
        if rule.exposure_bias < 0:
            raise ValueError(f"{key}: negative exposure_bias suppresses canon")
        pleasure = rule.adjustments.get("pleasure_gain")
        if pleasure is None or _percent_magnitude(pleasure) <= 0:
            raise ValueError(
                f"{key}: non-positive or absent pleasure_gain breaks sanctuary canon"
            )


def check_church_doctrine(rules) -> None:
    """Raise ValueError when any named Church item breaks canon doctrine."""
    check_church_vestments_and_emblems(rules, CHURCH_VESTMENTS_AND_EMBLEMS)
    check_church_sanctuary_devices(rules, CHURCH_SANCTUARY_DEVICES)


class ChurchDoctrineTests(unittest.TestCase):
    def _with_rule(self, key: str, rule: EquipmentEffectRule) -> dict:
        rules = dict(EQUIPMENT_EFFECT_RULES)
        rules[EquipmentModifierKey(key)] = rule
        return rules

    @covers_requirement(
        "equipment-effects::church-of-light-equipment-obeys-its-canon-doctrine"
    )
    def test_named_church_set_satisfies_doctrine(self):
        check_church_vestments_and_emblems(EQUIPMENT_EFFECT_RULES)
        check_church_sanctuary_devices(EQUIPMENT_EFFECT_RULES)
        check_church_doctrine(EQUIPMENT_EFFECT_RULES)

    @covers_requirement(
        "equipment-effects::church-of-light-equipment-obeys-its-canon-doctrine"
    )
    def test_sanctuary_devices_satisfy_doctrine_without_healing(self):
        check_church_sanctuary_devices(EQUIPMENT_EFFECT_RULES)
        for key in CHURCH_SANCTUARY_DEVICES:
            rule = EQUIPMENT_EFFECT_RULES[EquipmentModifierKey(key)]
            self.assertGreaterEqual(rule.exposure_bias, 0)
            self.assertIn("pleasure_gain", rule.adjustments)
            self.assertGreater(_percent_magnitude(rule.adjustments["pleasure_gain"]), 0)

    @covers_requirement(
        "equipment-effects::church-of-light-equipment-obeys-its-canon-doctrine"
    )
    def test_vestment_cannot_borrow_sanctuary_device_healing_exemption(self):
        rule = EQUIPMENT_EFFECT_RULES[EquipmentModifierKey.SISTER_VESTMENTS]
        deviant = replace(
            rule,
            adjustments=MappingProxyType(
                {k: v for k, v in rule.adjustments.items() if k != "heal_gain"}
            ),
            immune=(),
        )
        deviant_rules = self._with_rule("sister_vestments", deviant)
        # Sanctuary-device check passes for this rule in isolation:
        check_church_sanctuary_devices(deviant_rules, keys=("sister_vestments",))
        # But Church doctrine verification still fails because sister_vestments is in the vestment set:
        with self.assertRaises(ValueError) as caught:
            check_church_vestments_and_emblems(deviant_rules)
        self.assertIn("sister_vestments", str(caught.exception))
        self.assertIn("healing canon", str(caught.exception))
        with self.assertRaises(ValueError):
            check_church_doctrine(deviant_rules)

    @covers_requirement(
        "equipment-effects::church-of-light-equipment-obeys-its-canon-doctrine"
    )
    def test_imperial_and_elven_items_are_excluded_from_church_subsets(self):
        church_items = set(CHURCH_VESTMENTS_AND_EMBLEMS) | set(
            CHURCH_SANCTUARY_DEVICES
        )
        self.assertNotIn("warmth_rune_egg", church_items)
        self.assertNotIn("tremor_crystal", church_items)

    def test_sister_vestments_numbers_refused_at_uncommon_rarity(self):
        document = _canonical_document()
        registry = {
            definition.key: definition
            for definition in ITEM_REGISTRY.values()
            if definition.equipment_slot is not None
        }
        registry["sister_vestments"] = replace(
            registry["sister_vestments"],
            presentation=replace(
                registry["sister_vestments"].presentation,
                rarity=ItemRarity.UNCOMMON,
            ),
        )
        with self.assertRaises(EquipmentEffectsRulebookError) as caught:
            validate_equipment_effect_rules(document, registry, BUFF_DEFINITIONS)
        self.assertIn("sister_vestments.pleasure_gain", str(caught.exception))
        self.assertIn("soft_percent budget", str(caught.exception))

    def _expect_violation(self, key: str, mutate) -> None:
        original = EQUIPMENT_EFFECT_RULES[EquipmentModifierKey(key)]
        deviant = replace(original, **mutate(original))
        with self.assertRaises(ValueError):
            check_church_doctrine(self._with_rule(key, deviant))

    @covers_requirement(
        "equipment-effects::church-of-light-equipment-obeys-its-canon-doctrine"
    )
    def test_negative_pleasure_gain_violates_doctrine(self):
        self._expect_violation(
            "sister_vestments",
            lambda rule: {
                "adjustments": MappingProxyType(
                    {**rule.adjustments, "pleasure_gain": "-5%"}
                )
            },
        )

    @covers_requirement(
        "equipment-effects::church-of-light-equipment-obeys-its-canon-doctrine"
    )
    def test_negative_bias_violates_doctrine(self):
        self._expect_violation(
            "radiant_holy_emblem", lambda rule: {"exposure_bias": -1}
        )

    @covers_requirement(
        "equipment-effects::church-of-light-equipment-obeys-its-canon-doctrine"
    )
    def test_negative_heal_gain_violates_doctrine(self):
        self._expect_violation(
            "sister_vestments",
            lambda rule: {
                "adjustments": MappingProxyType(
                    {**rule.adjustments, "heal_gain": "-5%"}
                )
            },
        )

    @covers_requirement(
        "equipment-effects::church-of-light-equipment-obeys-its-canon-doctrine"
    )
    def test_church_item_without_heal_or_immunity_violates_doctrine(self):
        self._expect_violation(
            "pilgrim_medallion",
            lambda rule: {
                "adjustments": MappingProxyType(
                    {
                        field: value
                        for field, value in rule.adjustments.items()
                        if field != "heal_gain"
                    }
                )
            },
        )


class ShippedAdjustmentProseContractTests(unittest.TestCase):
    """The shipped roster's authored prose renders exactly as composed.

    Relocated from the migrated behavior file
    (migrate-rules-equipment-item-tests-off-real-data): the D4 formatter
    itself is behavior-tested against synthetic rows in
    ``test_equipment_prose.py``; the shipped rows' exact prose is a
    data-contract claim owned by this registered file.
    """

    @covers_requirement(
        "equipment-effects::equipment-adjustments-render-as-deterministic-prose"
    )
    def test_shipped_roster_rows_render_their_exact_authored_prose(self):
        # The tradeoff heavy armor: flat atk penalty + flat defense +
        # percent agility + hp ceiling, in the fixed vocabulary order.
        self.assertEqual(
            equipment_adjustment_text("knight_platemail"),
            "攻擊 −2｜防禦 +8｜敏捷 −10%｜生命上限 +15",
        )
        # Immunity-only accessory.
        self.assertEqual(equipment_adjustment_text("fearless_brooch"), "免疫恐懼")
        # Flat defense with poison immunity.
        self.assertEqual(
            equipment_adjustment_text("purified_pendant"), "防禦 +2｜免疫中毒"
        )
        # Flat weapon.
        self.assertEqual(equipment_adjustment_text("plain_sword"), "攻擊 +2")
        # Flat defense with a percent agility tradeoff.
        self.assertEqual(
            equipment_adjustment_text("chainmail"), "防禦 +5｜敏捷 −5%"
        )
        # Explicit empty entry renders nothing.
        self.assertEqual(equipment_adjustment_text("storage_pouch"), "")
        # P4-only vocabulary (pleasure_gain/exposure_bias) stays absent.
        self.assertEqual(
            equipment_adjustment_text("sister_vestments"), "防禦 −4｜治療 +10%"
        )


if __name__ == "__main__":
    unittest.main()
