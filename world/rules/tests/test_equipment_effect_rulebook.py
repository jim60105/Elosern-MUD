"""Data-contract test: equipment effect rulebook and item-lore liturgical-role contract
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
    LiturgicalRole,
)
from world.lore.settlements.shops import SHOP_REGISTRY
from world.rules.buffs import BUFF_DEFINITIONS
from world.rules.equipment_effects import (
    EQUIPMENT_EFFECT_RULES,
    EquipmentEffectRule,
    EquipmentEffectsRulebookError,
    equipment_adjustment_text,
    load_equipment_effect_rules,
    reload_equipment_effect_rules,
    validate_church_doctrine,
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
    def _expect_rejection(self, mutate, reason: str | None = None) -> None:
        """Load one deviant copy; optionally pin the rejection's reason.

        A reason substring is asserted where the test's point is *which*
        guard fired -- the doctrine pass runs after the schema and budget
        checks, so an unspecified reason could hide a test that passes on
        the wrong error.
        """
        document = _canonical_document()
        mutate(document)
        with self.assertRaises(EquipmentEffectsRulebookError) as caught:
            load_equipment_effect_rules(_write_rulebook(document))
        if reason is not None:
            self.assertIn(reason, str(caught.exception))

    # --- canonical data -------------------------------------------------------

    @covers_requirement(
        "equipment-effects::the-equipment-effect-rulebook-validates-a-closed-schema-at-load-time"
    )
    def test_canonical_rulebook_loads_the_full_roster(self):
        loaded = load_equipment_effect_rules()
        self.assertEqual(
            set(loaded),
            {
                definition.modifier_key
                for definition in ITEM_REGISTRY.values()
                if definition.equipment_slot is not None
            },
        )
        self.assertTrue(loaded)
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
    def test_weapon_multiplier_budget_overflow_is_rejected(self):
        # plain_sword is common (weapon_multiplier ceiling 1.0).
        self._expect_rejection(
            lambda d: d["effects"]["plain_sword"].update(
                {"weapon_damage_multiplier": 1.1}
            )
        )

    @covers_requirement(
        "equipment-effects::the-equipment-effect-rulebook-validates-a-closed-schema-at-load-time"
    )
    def test_weapon_multiplier_on_non_weapon_is_rejected(self):
        # knight_platemail is armor, not a weapon.
        self._expect_rejection(
            lambda d: d["effects"]["knight_platemail"].update(
                {"weapon_damage_multiplier": 1.0}
            )
        )

    @covers_requirement(
        "equipment-effects::the-equipment-effect-rulebook-validates-a-closed-schema-at-load-time"
    )
    def test_malformed_weapon_multiplier_values_are_rejected(self):
        for val in (True, False, 0.9, -1.0, float("nan"), float("inf"), "1.5", 10**400):
            with self.subTest(val=val):
                self._expect_rejection(
                    lambda d, v=val: d["effects"]["plain_sword"].update(
                        {"weapon_damage_multiplier": v}
                    )
                )

    @covers_requirement(
        "equipment-effects::the-equipment-effect-rulebook-validates-a-closed-schema-at-load-time"
    )
    def test_valid_synthetic_weapon_multiplier_loads(self):
        document = _canonical_document()
        document["budgets"]["common"]["weapon_multiplier"] = 2.0
        document["effects"]["plain_sword"]["weapon_damage_multiplier"] = 1.5
        loaded = load_equipment_effect_rules(_write_rulebook(document))
        self.assertEqual(loaded[EquipmentModifierKey.PLAIN_SWORD].weapon_damage_multiplier, 1.5)

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
            "weapon-multiplier-below-one": lambda d: d["budgets"]["common"].update({"weapon_multiplier": 0.9}),
            "weapon-multiplier-boolean": lambda d: d["budgets"]["common"].update({"weapon_multiplier": True}),
            "weapon-multiplier-nan": lambda d: d["budgets"]["common"].update({"weapon_multiplier": float("nan")}),
            "weapon-multiplier-inf": lambda d: d["budgets"]["common"].update({"weapon_multiplier": float("inf")}),
            "weapon-multiplier-overflow": lambda d: d["budgets"]["common"].update({"weapon_multiplier": 10**400}),
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
        # Budget lookup follows the REAL registry rarity, and an entry may not
        # declare one of its own: the closed entry schema rejects the field.
        document = _canonical_document()
        document["effects"]["wooden_club"]["rarity"] = "legendary"
        with self.assertRaisesRegex(EquipmentEffectsRulebookError, "rarity"):
            load_equipment_effect_rules(_write_rulebook(document))

    @covers_requirement(
        "equipment-effects::registration-and-tradeability-are-independent"
    )
    def test_unstocked_equipment_item_loads_clean(self):
        registry, document = self._two_entry_setup()
        self.assertNotIn("wooden_club", SHOP_REGISTRY["altoria_general_store"].offered_item_keys)
        rules = self._validate(registry, document)
        self.assertIn(EquipmentModifierKey.WOODEN_CLUB, rules)
        self.assertEqual(rules[EquipmentModifierKey.WOODEN_CLUB].adjustments["atk_phys"], 3)
        from world.rules.guild_config import (
            load_commerce_config,
            validate_assortment_configs,
            validate_price_scales,
            validate_shop_configs,
        )
        raw_commerce = load_commerce_config(
            Path(__file__).parents[1] / "rulebook" / "commerce"
        )
        assortment_offers = validate_assortment_configs(raw_commerce["assortments"])
        configs = validate_shop_configs(
            raw_commerce["shops"],
            assortment_offers,
            validate_price_scales(raw_commerce["price_scales"]),
        )
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
    """The equipment bijection and authored trade identities."""

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
        for member in EquipmentModifierKey:
            self.assertEqual(member.value, member.name.lower())
        for definition in ITEM_REGISTRY.values():
            if definition.equipment_slot is not None:
                self.assertEqual(definition.modifier_key.value, definition.key)

    @covers_requirement(
        "equipment-effects::equipment-membership-and-stocking-are-authored-data"
    )
    def test_every_registered_equipment_item_is_complete_and_price_resolvable(self):
        # No approved new-item roster: every CURRENT equipment definition must
        # be complete on its own, so a valid item edit needs no test change.
        registered = {
            definition.key
            for definition in ITEM_REGISTRY.values()
            if definition.equipment_slot is not None
        }
        self.assertTrue(registered)
        for key in sorted(registered):
            with self.subTest(item=key):
                definition = ITEM_REGISTRY[key]
                self.assertEqual(definition.modifier_key.value, key)
                self.assertIsInstance(definition.sellable, bool)
                self.assertIn(definition.price_table_key, PRICE_TABLE)
                self.assertIn(definition.modifier_key, EQUIPMENT_EFFECT_RULES)

    @covers_requirement(
        "equipment-effects::equipment-membership-and-stocking-are-authored-data"
    )
    def test_stocking_is_authored_data_not_a_registration_consequence(self):
        # Offers are membership data over registered items, and registration
        # never implies an offer: a bound, budget-checked item no counter
        # carries is a valid shipped state that still loads its rule.
        registered = {
            definition.key
            for definition in ITEM_REGISTRY.values()
            if definition.equipment_slot is not None
        }
        offered = {
            item_key
            for shop in SHOP_REGISTRY.values()
            for item_key in shop.offered_item_keys
        }
        # An offer names a registered item; registration never implies one.
        self.assertTrue(offered <= set(ITEM_REGISTRY))
        unstocked = sorted(registered - offered)
        self.assertTrue(unstocked, "no unstocked equipment ships at all")
        for item_key in unstocked:
            with self.subTest(item=item_key):
                self.assertIn(
                    ITEM_REGISTRY[item_key].modifier_key, EQUIPMENT_EFFECT_RULES
                )

    @covers_requirement(
        "equipment-effects::registration-and-tradeability-are-independent"
    )
    def test_every_equipment_price_table_key_resolves(self):
        for key, definition in ITEM_REGISTRY.items():
            with self.subTest(item=key):
                self.assertIn(definition.price_table_key, PRICE_TABLE)


def _role_members(role: LiturgicalRole) -> tuple[str, ...]:
    """Discover one doctrine sub-set from item lore, never from a named list.

    Membership is the item's own immutable ``liturgical_role``, so authoring a
    new Church record with the role enters doctrine coverage automatically and
    no effect-table edit can move an item between the sub-sets.
    """
    return tuple(
        item_key
        for item_key, definition in sorted(ITEM_REGISTRY.items())
        if definition.liturgical_role is role
    )


def _percent_magnitude(value: str) -> int:
    return int(value[:-1])


def check_church_vestments_and_emblems(rules, keys=None) -> None:
    """Raise ValueError when one Church vestment or emblem breaks doctrine.

    Canon (坦露與歡愉為正向、光之治療與淨化): an explicit non-negative
    exposure bias and pleasure term, at least one of heal_gain or an
    immunity, no suppression values. Ordinary combat trade-offs remain
    permitted. This is the independent oracle: it never calls the production
    validator to learn the expected outcome.
    """
    if keys is None:
        keys = _role_members(LiturgicalRole.VESTMENT_OR_EMBLEM)
    for key in keys:
        rule = rules[EquipmentModifierKey(key)]
        if rule.exposure_bias < 0:
            raise ValueError(f"{key}: negative exposure_bias suppresses canon")
        pleasure = rule.adjustments.get("pleasure_gain")
        if pleasure is None:
            raise ValueError(f"{key}: absent pleasure_gain breaks canon")
        if _percent_magnitude(pleasure) < 0:
            raise ValueError(f"{key}: negative pleasure_gain suppresses canon")
        heal = rule.adjustments.get("heal_gain")
        if heal is not None and _percent_magnitude(heal) < 0:
            raise ValueError(f"{key}: negative heal_gain breaks healing canon")
        has_heal = heal is not None and _percent_magnitude(heal) > 0
        if not has_heal and not rule.immune:
            raise ValueError(
                f"{key}: neither heal_gain nor an immunity breaks healing canon"
            )


def check_church_sanctuary_devices(rules, keys=None) -> None:
    """Raise ValueError when one Church sanctuary device breaks doctrine.

    Sanctuary devices: non-negative exposure_bias, positive pleasure_gain,
    no suppression values. Healing-or-immunity is NOT required.
    """
    if keys is None:
        keys = _role_members(LiturgicalRole.SANCTUARY_DEVICE)
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
    """Raise ValueError when any item-lore role member breaks canon doctrine."""
    check_church_vestments_and_emblems(rules)
    check_church_sanctuary_devices(rules)


class ChurchDoctrineTests(unittest.TestCase):
    def _with_rule(self, key: str, rule: EquipmentEffectRule) -> dict:
        rules = dict(EQUIPMENT_EFFECT_RULES)
        rules[EquipmentModifierKey(key)] = rule
        return rules

    def _expect_load_rejection(self, mutate, reason: str | None = None) -> None:
        """Load one deviant canonical copy and optionally pin the reason."""
        document = _canonical_document()
        mutate(document)
        with self.assertRaises(EquipmentEffectsRulebookError) as caught:
            load_equipment_effect_rules(_write_rulebook(document))
        if reason is not None:
            self.assertIn(reason, str(caught.exception))

    @covers_requirement(
        "equipment-effects::church-of-light-equipment-obeys-its-canon-doctrine"
    )
    def test_every_role_bearing_church_item_satisfies_doctrine(self):
        vestments = _role_members(LiturgicalRole.VESTMENT_OR_EMBLEM)
        devices = _role_members(LiturgicalRole.SANCTUARY_DEVICE)
        self.assertTrue(vestments)
        self.assertTrue(devices)
        self.assertFalse(set(vestments) & set(devices))
        # Every roled item is covered, and every covered key is roled: the
        # sub-sets are a partition of the item-lore declarations, not a list.
        self.assertEqual(
            {
                item_key
                for item_key, definition in ITEM_REGISTRY.items()
                if definition.liturgical_role is not None
            },
            set(vestments) | set(devices),
        )
        for item_key in vestments + devices:
            self.assertIn(EquipmentModifierKey(item_key), EQUIPMENT_EFFECT_RULES)
        check_church_doctrine(EQUIPMENT_EFFECT_RULES)
        # The production load agrees with the independent oracle.
        validate_church_doctrine(
            {
                definition.key: definition
                for definition in ITEM_REGISTRY.values()
                if definition.equipment_slot is not None
            },
            EQUIPMENT_EFFECT_RULES,
        )

    @covers_requirement(
        "equipment-effects::church-of-light-equipment-obeys-its-canon-doctrine"
    )
    def test_sanctuary_devices_satisfy_doctrine_without_healing(self):
        check_church_sanctuary_devices(EQUIPMENT_EFFECT_RULES)
        for key in _role_members(LiturgicalRole.SANCTUARY_DEVICE):
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
        # The role lives on the item, so the deviant rule changes what the
        # item must satisfy -- never which sub-set the item belongs to.
        self.assertIs(
            ITEM_REGISTRY["sister_vestments"].liturgical_role,
            LiturgicalRole.VESTMENT_OR_EMBLEM,
        )
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
        church_items = set(_role_members(LiturgicalRole.VESTMENT_OR_EMBLEM)) | set(
            _role_members(LiturgicalRole.SANCTUARY_DEVICE)
        )
        for key in ("warmth_rune_egg", "tremor_crystal"):
            with self.subTest(item=key):
                self.assertIsNone(ITEM_REGISTRY[key].liturgical_role)
                self.assertNotIn(key, church_items)

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

    @covers_requirement(
        "equipment-effects::church-of-light-equipment-obeys-its-canon-doctrine"
    )
    def test_absent_pleasure_gain_is_not_an_exemption(self):
        # Dropping the key must not read as "no negative pleasure": absent is
        # its own violation, so a vestment cannot evade the canon by omission.
        self._expect_violation(
            "sister_vestments",
            lambda rule: {
                "adjustments": MappingProxyType(
                    {
                        field: value
                        for field, value in rule.adjustments.items()
                        if field != "pleasure_gain"
                    }
                )
            },
        )
        # The independent oracle holds the same reading as production.
        rule = EQUIPMENT_EFFECT_RULES[EquipmentModifierKey.SISTER_VESTMENTS]
        deviant = replace(
            rule,
            adjustments=MappingProxyType(
                {
                    field: value
                    for field, value in rule.adjustments.items()
                    if field != "pleasure_gain"
                }
            ),
        )
        with self.assertRaises(ValueError) as caught:
            check_church_vestments_and_emblems(
                self._with_rule("sister_vestments", deviant)
            )
        self.assertIn("absent pleasure_gain", str(caught.exception))

    @covers_requirement(
        "equipment-effects::church-of-light-equipment-obeys-its-canon-doctrine"
    )
    def test_an_effect_entry_cannot_declare_a_liturgical_role(self):
        # Reclassification from the effect side is impossible: the entry
        # schema is closed, so a role field is an unknown field naming itself.
        self._expect_load_rejection(
            lambda d: d["effects"]["sister_vestments"].update(
                {"liturgical_role": "sanctuary_device"}
            ),
            reason="unknown fields",
        )

    @covers_requirement(
        "equipment-effects::church-of-light-equipment-obeys-its-canon-doctrine"
    )
    def test_the_loader_rejects_a_vestment_that_drops_its_obligation(self):
        # A within-budget mutation that only breaks doctrine: the shipped
        # loader itself must refuse it, naming the item and the rule.
        def drop_healing(document):
            entry = document["effects"]["pilgrim_medallion"]
            entry["adjustments"].pop("heal_gain", None)
            entry["immune"] = []

        self._expect_load_rejection(drop_healing, reason="pilgrim_medallion")
        self._expect_load_rejection(drop_healing, reason="neither")

    @covers_requirement(
        "equipment-effects::church-of-light-equipment-obeys-its-canon-doctrine"
    )
    def test_a_role_bearing_item_joins_doctrine_coverage_automatically(self):
        # A newly authored Church record needs no list edit anywhere: its own
        # role puts it under the obligation the loader enforces.
        registry = {
            item_key: definition
            for item_key, definition in ITEM_REGISTRY.items()
            if definition.equipment_slot is not None
            and item_key != "sister_vestments"
        }
        registry["t_synth_vestment"] = replace(
            ITEM_REGISTRY["sister_vestments"],
            key="t_synth_vestment",
            liturgical_role=LiturgicalRole.VESTMENT_OR_EMBLEM,
        )
        # Covered with the shipped rule ...
        validate_church_doctrine(registry, EQUIPMENT_EFFECT_RULES)
        # ... and rejected the moment its own entry breaks the obligation.
        broken = dict(EQUIPMENT_EFFECT_RULES)
        broken[EquipmentModifierKey.SISTER_VESTMENTS] = replace(
            EQUIPMENT_EFFECT_RULES[EquipmentModifierKey.SISTER_VESTMENTS],
            adjustments=MappingProxyType({}),
            immune=(),
        )
        with self.assertRaises(EquipmentEffectsRulebookError) as caught:
            validate_church_doctrine(registry, broken)
        self.assertIn("t_synth_vestment", str(caught.exception))

    @covers_requirement(
        "equipment-effects::church-of-light-equipment-obeys-its-canon-doctrine"
    )
    def test_a_role_without_a_loaded_entry_is_refused(self):
        # Defence in depth: the loader's bijection already guarantees every
        # roled equipment item has an entry, so this branch is only reachable
        # by a direct call -- and it still fails closed by name.
        registry = {
            item_key: definition
            for item_key, definition in ITEM_REGISTRY.items()
            if definition.equipment_slot is not None
        }
        rules = {
            key: rule
            for key, rule in EQUIPMENT_EFFECT_RULES.items()
            if key is not EquipmentModifierKey.SISTER_VESTMENTS
        }
        with self.assertRaises(EquipmentEffectsRulebookError) as caught:
            validate_church_doctrine(registry, rules)
        message = str(caught.exception)
        self.assertIn("sister_vestments", message)
        self.assertIn("no loaded effect entry", message)


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


# The six shipped grade pairs, as identity only: bonuses, prices and stock
# come from the authored declarations (the historical section 5 numerical
# table is not duplicated in tests).
MILITARY_GRADES = ("e", "d", "c", "b", "a", "s")


class MilitaryAuthoringContractTests(unittest.TestCase):
    """The six shipped pairs stay shared registered declarations."""

    @covers_requirement(
        "military-equipment::six-military-pairs-use-shared-registered-effects-and-approved-integer-prices"
    )
    def test_shared_registered_pairs_use_authored_adjustments_and_finite_offers(self):
        from world.quests.catalog import register_catalog
        register_catalog()
        from world.lore.settlements.assortments import ASSORTMENT_REGISTRY
        from world.rules.guild_config import get_catalog
        from world.skills.equipment import EquipmentSlot

        catalog = get_catalog()
        for grade in MILITARY_GRADES:
            for shape, stat, slot, assortment in (
                ("sword", "atk_phys", EquipmentSlot.WEAPON_MAIN, "common_arms"),
                ("armor", "defense", EquipmentSlot.ARMOR, "common_outfits"),
            ):
                key = f"military_{grade}_{shape}"
                with self.subTest(item=key):
                    item = ITEM_REGISTRY[key]
                    self.assertEqual(item.equipment_slot, slot)
                    self.assertEqual(item.modifier_key.value, key)
                    self.assertIsInstance(item.presentation.rarity, ItemRarity)
                    self.assertTrue(item.sellable)
                    adjustments = dict(
                        EQUIPMENT_EFFECT_RULES[item.modifier_key].adjustments
                    )
                    self.assertIn(stat, adjustments)
                    self.assertTrue(
                        all(type(value) is int for value in adjustments.values())
                    )
                    self.assertIn(key, ASSORTMENT_REGISTRY[assortment].item_keys)
                    offers = [
                        offer for config in catalog.shop_configs.values()
                        for offer in config.offers if offer.item_key == key
                    ]
                    self.assertTrue(offers)
                    for offer in offers:
                        # Signed resale and finite stock are authored data:
                        # only their relations are asserted here.
                        self.assertIs(type(offer.buy_copper), int)
                        self.assertGreater(offer.buy_copper, 0)
                        self.assertEqual(offer.sell_copper, offer.buy_copper // 2)
                        self.assertGreaterEqual(offer.initial_stock, 0)
                        self.assertGreaterEqual(
                            offer.max_stock, offer.initial_stock
                        )
                        self.assertGreaterEqual(offer.restock_quantity, 0)
        # The bands these rows resolve to stay integral and ordered.
        for band_key in ("magic_armor", "armor", "magic_weapon"):
            band = PRICE_TABLE[band_key]
            self.assertIs(type(band.min_copper), int)
            self.assertTrue(
                band.max_copper is None or band.max_copper >= band.min_copper
            )

    def test_military_over_budget_rejected_without_budget_change(self):
        document = _canonical_document()
        before = {key: dict(value) for key, value in document["budgets"].items()}
        # One above the row's own rarity budget, derived from the authored
        # budget so a valid retune of either side stays consistent.
        rarity = ITEM_REGISTRY["military_s_sword"].presentation.rarity.value
        document["effects"]["military_s_sword"]["adjustments"]["atk_phys"] = (
            document["budgets"][rarity]["flat"] + 1
        )
        with self.assertRaises(EquipmentEffectsRulebookError):
            validate_equipment_effect_rules(document, ITEM_REGISTRY, BUFF_DEFINITIONS)
        self.assertEqual(document["budgets"], before)


from evennia.utils.test_resources import EvenniaTest


class MilitaryRuntimeSmokeTests(EvenniaTest):
    """Real registered gear on synthetic people through ordinary rule APIs."""

    @covers_requirement(
        "military-equipment::military-pairs-participate-in-ordinary-finite-commerce"
    )
    def test_purchase_equip_sell_restock_and_rollback(self):
        from unittest.mock import patch
        from world.quests.catalog import register_catalog
        register_catalog()
        from evennia.utils.create import create_object
        from typeclasses.characters import PlayerCharacter
        from typeclasses.components import Merchant
        from typeclasses.npcs import NPC
        from typeclasses.rooms import Room
        from world.rules.clock import WorldClock
        from world.rules.economy import buy, sell, parse_merchant_stock, TradeError, TradeReason
        from world.rules.guild_config import get_catalog
        from world.rules.equipment import toggle_equipment
        from world.rules.equipment_effects import equipment_adjustments
        from world.rules.caravan_arrivals import settle_caravan_arrivals

        catalog = get_catalog()
        room = create_object(Room, key="military smoke")
        player = create_object(PlayerCharacter, key="synthetic buyer", location=room)
        wearer = create_object(NPC, key="synthetic wearer", location=room)
        for entity in (player, wearer):
            entity.race = "human"
            entity.apply_race_baseline()
        for grade in MILITARY_GRADES:
            keys = (f"military_{grade}_sword", f"military_{grade}_armor")
            player.db.wallet = 2000000
            player.db.inventory = []
            wearer.db.inventory = list(keys)
            for entity in (player, wearer):
                entity.db.equipment = {"weapon_main": None, "weapon_off": None, "armor": None, "accessories": []}
            merchants = []
            for key in keys:
                config = next(config for config in catalog.shop_configs.values() if any(o.item_key == key for o in config.offers))
                offer = next(o for o in config.offers if o.item_key == key)
                price = offer.buy_copper
                host = create_object(NPC, key=f"synthetic {key} vendor", location=room)
                merchant = Merchant.create(host, service_id=key, shop_key=config.shop_key)
                host.components.add(merchant)
                merchant.merchant_stock = {o.item_key: o.initial_stock for o in config.offers}
                merchant.last_restock_day = 0
                merchants.append((host, merchant, offer))
                with patch("world.rules.economy.get_world_clock", return_value=WorldClock(12 * 3600)):
                    before = player.db.wallet
                    result = buy(player, host, key, 2)
                    self.assertEqual(result["total_copper"], price * 2)
                    self.assertEqual(player.db.wallet, before - price * 2)
                    snapshot = (player.db.wallet, list(player.db.inventory), len(player.contents), parse_merchant_stock(merchant))
                    with self.assertRaises(TradeError) as caught:
                        buy(player, host, key, 1)
                    self.assertEqual(caught.exception.args[0], TradeReason.INSUFFICIENT_STOCK)
                    self.assertEqual((player.db.wallet, list(player.db.inventory), len(player.contents), parse_merchant_stock(merchant)), snapshot)
                    sold = sell(player, host, key, 1)
                    self.assertEqual(sold["total_copper"], price // 2)
                    snapshot = (player.db.wallet, list(player.db.inventory), len(player.contents), parse_merchant_stock(merchant))
                    with patch("world.rules.affinity.apply_affinity_change", side_effect=RuntimeError("persistence fault")):
                        with self.assertRaises(RuntimeError):
                            buy(player, host, key, 1)
                    self.assertEqual((player.db.wallet, list(player.db.inventory), len(player.contents), parse_merchant_stock(merchant)), snapshot)
                # Two bought and one resold leaves the declared stock minus one.
                self.assertEqual(
                    parse_merchant_stock(merchant)[key], offer.initial_stock - 1
                )
            sword_rule = EQUIPMENT_EFFECT_RULES[ITEM_REGISTRY[keys[0]].modifier_key]
            armor_rule = EQUIPMENT_EFFECT_RULES[ITEM_REGISTRY[keys[1]].modifier_key]
            for entity in (player, wearer):
                entity.db.inventory = list(keys)
                for key in keys:
                    res = toggle_equipment(entity, key)
                    assert res.outcome == "success", f"toggle {key} on {entity} failed: {res.outcome} {res.reason}"
                # Declaration-to-consumer wiring: each worn row's own flat
                # axes and their sum land in the merged bundle consumers read.
                bonuses = equipment_adjustments(entity)
                self.assertEqual(
                    bonuses["atk_phys"], int(sword_rule.adjustments["atk_phys"])
                )
                self.assertEqual(
                    bonuses["defense"], int(armor_rule.adjustments["defense"])
                )
                self.assertEqual(
                    bonuses.get("agility_flat", 0),
                    int(sword_rule.adjustments.get("agility", 0))
                    + int(armor_rule.adjustments.get("agility", 0)),
                )
            end_tick = 86400 + 7 * 3600
            stock_before_restock = {
                key: parse_merchant_stock(merchant)[key]
                for key, (_, merchant, _) in zip(keys, merchants)
            }
            with patch("world.rules.clock.get_world_clock", return_value=WorldClock(end_tick)):
                settle_caravan_arrivals(12 * 3600, end_tick)
            for key, (host, merchant, offer) in zip(keys, merchants):
                settled = parse_merchant_stock(merchant)[key]
                self.assertGreaterEqual(settled, stock_before_restock[key])
                self.assertLessEqual(settled, offer.max_stock)
                self.assertEqual(merchant.last_restock_day, 1)
                host.delete()


class GuildRestrictionAuthoredKitTests(EvenniaTest):
    """Data-contract test: approved restriction rows produce real-kit references."""

    def _host(self, rank):
        from evennia.utils.create import create_object
        from typeclasses.npcs import NPC
        from world.rules.equipment import toggle_equipment
        from world.rules.guild_exam_restrictions import PROFILES
        from world.skills.registry import SKILL_REGISTRY, SkillKind

        host = create_object(NPC, key=f"authored kit {rank}", location=self.room1)
        host.race = "human"
        host.subrace = "human_plains"
        host.apply_race_baseline()
        bases = (
            (170, 120, 120, 17, 17, 16, 30)
            if rank == "A" else (200, 120, 120, 20, 20, 19, 35)
        )
        for key, value in zip(("hp", "mp", "sp", "atk_phys", "agility", "defense", "magic_power"), bases):
            host.traits.get(key).base = value
            if key in ("hp", "mp", "sp"):
                host.traits.get(key).rate = 0
                host.traits.get(key).current = value
        profile = PROFILES[rank]
        keys = (*profile.allowed_skills, "heal", "defense_instinct")
        host.db.skills = {
            "active": [key for key in keys if SKILL_REGISTRY[key].kind is SkillKind.ACTIVE],
            "passive": [key for key in keys if SKILL_REGISTRY[key].kind is SkillKind.PASSIVE],
        }
        host.db.skill_proficiency = {key: 1000.0 for key in keys}
        host.db.inventory = [profile.weapon, profile.armor]
        for key in host.db.inventory:
            self.assertEqual(toggle_equipment(host, key).outcome, "success")
        return host

    @covers_requirement("guild-exam-restrictions::a-and-s-examination-kits-retain-real-lineage-effects")
    def test_real_a_s_kits_seal_unrelated_effects_and_retain_domain(self):
        from unittest.mock import patch
        from world.rules.action import ActionRequest, ActionResolver
        from world.rules.combat import Battlefield, BattlefieldActionContext
        from world.rules.combat_modifiers import adjusted_agility, evaluate_combat_modifiers
        from world.rules.guild_exam_restrictions import activate_exam_restriction, remove_exam_restriction
        from world.skills.restrictions import skill_effect_allowed

        target = self._host("S")
        target.key = "authored domain target"
        target.traits.hp.base = 20000
        target.traits.hp.current = 20000
        for rank, expected in (("A", (30, 25, 29)), ("S", (36, 31, 35))):
            host = self._host(rank)
            bases = {key: host.traits.get(key).base for key in host.traits.all()}
            ownership = dict(host.db.skills)
            proficiency = dict(host.db.skill_proficiency)
            activate_exam_restriction(host, f"authored-{rank}", rank)
            modifiers = evaluate_combat_modifiers(host)
            self.assertEqual((
                host.skills.effective_value("atk_phys") + modifiers["atk_phys"],
                adjusted_agility(host),
                host.skills.effective_value("defense") + modifiers["defense"],
            ), expected)
            self.assertFalse(skill_effect_allowed(host, "defense_instinct"))
            self.assertFalse(skill_effect_allowed(host, "heal"))
            self.assertTrue(skill_effect_allowed(host, "body_enhancement_basic"))
            if rank == "S":
                battlefield = Battlefield(
                    {"one": frozenset({str(host.key)}), "two": frozenset({str(target.key)})},
                    {str(host.key): host, str(target.key): target},
                )
                context = BattlefieldActionContext(battlefield, event_context={"simulated": True}, nonlethal=True)
                with patch("world.rules.combat.damage.roll_d100", return_value=1):
                    result = ActionResolver.resolve(ActionRequest(host, "true_sword_saint", [target], context))
                self.assertEqual(result.outcome, "success")
                self.assertEqual(host.skills.effective_value("atk_phys") + evaluate_combat_modifiers(host)["atk_phys"], 48)
            remove_exam_restriction(host, f"authored-{rank}")
            self.assertEqual({key: host.traits.get(key).base for key in host.traits.all()}, bases)
            self.assertEqual(dict(host.db.skills), ownership)
            self.assertEqual(dict(host.db.skill_proficiency), proficiency)

    @covers_requirement("guild-exam-restrictions::reduced-neutral-baselines-precede-penalties-and-preserve-both-agility-consumers")
    @covers_requirement("guild-exam-restrictions::guild-accessories-persist-reversible-execution-and-effect-restrictions")
    def test_real_limit_accessories_lower_s_senior_and_keep_hamstring(self):
        from copy import deepcopy
        from world.rules.buffs import apply_buff, _remove_buff_keys
        from world.rules.combat_modifiers import adjusted_agility, evaluate_combat_modifiers
        from world.rules.equipment import toggle_equipment
        from world.rules.guild_exam_restrictions import PROFILES, activate_exam_restriction, remove_exam_restriction

        host = self._host("S")
        before = deepcopy((dict(host.db.skills), dict(host.db.skill_proficiency), {key: host.traits.get(key).base for key in host.traits.all()}))
        rows = (
            ("E", (100, 100, 100, 11, 8, 10, 10), 8),
            ("D", (110, 100, 100, 15, 12, 15, 12), 11),
            ("C", (130, 110, 110, 20, 16, 19, 20), 14),
            ("B", (145, 110, 110, 25, 20, 24, 25), 17),
        )
        for rank, expected, initiative in rows:
            profile = PROFILES[rank]
            host.db.inventory = [*host.db.inventory, profile.weapon, profile.armor]
            for key in (profile.weapon, profile.armor):
                self.assertEqual(toggle_equipment(host, key).outcome, "success")
            activate_exam_restriction(host, f"authored-{rank}", rank)
            self.assertIn(profile.accessory, host.db.equipment["accessories"])
            modifiers = evaluate_combat_modifiers(host)
            self.assertEqual((
                host.traits.hp.max, host.traits.mp.max, host.traits.sp.max,
                host.skills.effective_value("atk_phys") + modifiers["atk_phys"],
                adjusted_agility(host),
                host.skills.effective_value("defense") + modifiers["defense"],
                host.skills.effective_value("magic_power") + modifiers.get("magic_power", 0),
            ), expected)
            self.assertEqual(host.skills.effective_value("agility"), initiative)
            if rank == "D":
                apply_buff(host, "martial_hamstring")
                self.assertEqual(adjusted_agility(host), 7)
                _remove_buff_keys(host, ("martial_hamstring",))
            remove_exam_restriction(host, f"authored-{rank}")
            self.assertEqual((dict(host.db.skills), dict(host.db.skill_proficiency), {key: host.traits.get(key).base for key in host.traits.all()}), before)
            self.assertFalse(ITEM_REGISTRY[profile.accessory].sellable)
            self.assertTrue(ITEM_REGISTRY[profile.accessory].guild_property)
            self.assertTrue(all(profile.accessory not in shop.offered_item_keys for shop in SHOP_REGISTRY.values()))


if __name__ == "__main__":
    unittest.main()
