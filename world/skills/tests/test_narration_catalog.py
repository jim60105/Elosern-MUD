"""Pure tests for the authored narration catalog engine.

No database and no Evennia runtime. Engine cases use file-local synthetic rows
and bands, so the checks establish the engine's contract rather than echoing
registry data; the authored-family cases read the shipped data modules only to
establish row shape, distinctness and bound adherence, never key content.
"""

from __future__ import annotations

import itertools
import unittest

from tools.spec_traceability import covers_requirement

from world.skills.narration import (
    COMPACT_POOLS,
    DAMAGE_BAND_LINES,
    FALLBACK_TEMPLATES,
    FAMILY_ROWS,
    INTERNAL_KINDS,
    KIND_POOLS,
    NARRATION_CATALOG,
    NARRATION_KINDS,
    PENDING_FAMILIES,
    BandTable,
    NarrationCatalogError,
    NarrationRow,
    action_lines,
    base_family_key,
    composed_fits,
    entry_line,
    family_key,
    slot_count,
)
from world.skills.narration.data_divine_mystery import ROWS as DIVINE_MYSTERY_ROWS
from world.skills.narration.data_dark import ROWS as DARK_ROWS
from world.skills.narration.data_earth import ROWS as EARTH_ROWS
from world.skills.narration.data_enhancement import ROWS as ENHANCEMENT_ROWS
from world.skills.narration.data_fire import ROWS as FIRE_ROWS
from world.skills.narration.data_holy_rite import ROWS as HOLY_RITE_ROWS
from world.skills.narration.data_ice import ROWS as ICE_ROWS
from world.skills.narration.data_light import ROWS as LIGHT_ROWS
from world.skills.narration.data_lightning import ROWS as LIGHTNING_ROWS
from world.skills.narration.data_martial import ROWS as MARTIAL_ROWS
from world.skills.narration.data_water import ROWS as WATER_ROWS
from world.skills.narration.data_wind import ROWS as WIND_ROWS
from world.skills.narration.select import action_line, choose_line, narration_seed
from world.skills.narration.validation import build_catalog, validate_catalog
from world.skills.narration.vocab import contains_ascii_digit
from world.skills.registry import (
    SkillCategory,
    SkillDef,
    SkillKind,
    TargetSpec,
)
from world.lore.elements import Element

#: One authored module and the family label its element or category owns.
ELEMENTAL_MODULES = (
    (FIRE_ROWS, "elemental_magic:fire"),
    (WATER_ROWS, "elemental_magic:water"),
    (WIND_ROWS, "elemental_magic:wind"),
    (EARTH_ROWS, "elemental_magic:earth"),
    (LIGHTNING_ROWS, "elemental_magic:lightning"),
    (ICE_ROWS, "elemental_magic:ice"),
    (LIGHT_ROWS, "elemental_magic:light"),
    (DARK_ROWS, "elemental_magic:dark"),
)

#: One authored non-elemental module and the family key its rows resolve through.
AUTHORED_FAMILIES = (
    (MARTIAL_ROWS, "martial_arts"),
    (HOLY_RITE_ROWS, "holy_rite"),
    (DIVINE_MYSTERY_ROWS, "divine_mystery"),
    (ENHANCEMENT_ROWS, "enhancement"),
)

#: Every authored module, used by the whole-catalog distinctness checks.
AUTHORED_MODULES = (*ELEMENTAL_MODULES, *AUTHORED_FAMILIES)


def _skill(key: str, *, category: SkillCategory, element: Element | None = None,
           effects: tuple[str, ...] = ()) -> SkillDef:
    return SkillDef(
        key=key,
        label=key,
        description=key,
        kind=SkillKind.ACTIVE,
        target_spec=TargetSpec.SINGLE,
        cost={},
        usable_out_of_combat=True,
        element=element,
        effects=list(effects),
        category=category,
    )


def _row(key: str, *, action: tuple[str, ...] = (), kind: str = "damage",
         lines: tuple[str, ...] = ("{target} 吃了一記。",)) -> NarrationRow:
    return NarrationRow(key=key, action=action, kind_lines={kind: lines})


class BandTableTests(unittest.TestCase):
    def test_band_tables_are_finite_ascending_and_closed(self):
        table = BandTable("t", (("low", 0.5), ("high", 1.0)))
        self.assertEqual(table.bands[-1][1], 1.0)
        for invalid in (
            (),
            (("zero", 0.0), ("top", 1.0)),
            (("over", 1.5),),
            (("b", 0.5), ("a", 0.4), ("top", 1.0)),
            (("open", 0.5),),
        ):
            with self.subTest(bands=invalid):
                with self.assertRaises(NarrationCatalogError):
                    BandTable("bad", invalid)


class PoolInventoryTests(unittest.TestCase):
    @covers_requirement(
        "action-narration::mechanical-entries-narrate-qualitatively-instead-of-listing-state-changes"
    )
    def test_every_non_internal_kind_has_a_pool_and_a_compact_fallback(self):
        for kind in NARRATION_KINDS:
            if kind in INTERNAL_KINDS:
                self.assertEqual(FALLBACK_TEMPLATES[kind], "")
                continue
            with self.subTest(kind=kind):
                self.assertGreaterEqual(len(KIND_POOLS[kind]), 3)
                self.assertIn(kind, COMPACT_POOLS)
                self.assertFalse(any(ch.isdigit() for ch in COMPACT_POOLS[kind]))

class PendingFamilyDeclarationTests(unittest.TestCase):
    @covers_requirement(
        "action-narration::authored-narration-is-a-catalog-validated-against-the-shipped-registries",
        "action-narration::every-elemental-spell-has-its-own-action-narration",
    )
    def test_pending_families_is_the_frozen_declared_set(self):
        self.assertEqual(
            PENDING_FAMILIES,
            frozenset({"sexual_act"}),
        )


class LookupChainTests(unittest.TestCase):
    def test_exact_row_precedes_family_and_family_precedes_pool(self):
        exact = _row("t_exact", lines=("精確 {target}。",))
        family = NarrationRow(
            key="martial_arts", kind_lines={"damage": ("家族 {target}。",)}
        )
        line = entry_line(
            "damage",
            {},
            skill_key="t_exact",
            family="martial_arts",
            target_key="t",
            actor="a",
            target="t",
            catalog={"t_exact": exact},
            families={"martial_arts": family},
        )
        self.assertEqual(line, "精確 {target}。")

        line = entry_line(
            "damage",
            {},
            skill_key="t_missing",
            family="martial_arts",
            target_key="t",
            actor="a",
            target="t",
            catalog={},
            families={"martial_arts": family},
        )
        self.assertEqual(line, "家族 {target}。")

    @covers_requirement(
        "action-narration::narration-resolution-degrades-instead-of-rejecting-an-action"
    )
    def test_a_missing_family_and_row_degrades_to_the_kind_pool(self):
        line = entry_line(
            "damage",
            {},
            skill_key="t_missing",
            family="not_a_family",
            target_key="t",
            actor="a",
            target="t",
            catalog={},
            families={},
        )
        self.assertIn(line, DAMAGE_BAND_LINES["solid"])

    def test_a_resolved_named_row_keeps_a_short_name(self):
        row = _row("t_short", lines=("{target} 的傷勢浮現。",))
        line = entry_line(
            "damage",
            {},
            skill_key="t_short",
            target_key="t",
            actor="a",
            target="t",
            catalog={"t_short": row},
            families={},
        )
        self.assertEqual(line, "{target} 的傷勢浮現。")

    @covers_requirement(
        "action-narration::the-built-line-degrades-to-its-compact-fallback-when-names-do-not-fit"
    )
    def test_an_over_long_name_degrades_to_the_compact_fallback(self):
        long_name = "名" * 300
        row = _row("t_long", lines=("{target} 的傷勢浮現得很清楚。",))
        line = entry_line(
            "damage",
            {},
            skill_key="t_long",
            target_key=long_name,
            actor="a",
            target=long_name,
            catalog={"t_long": row},
            families={},
        )
        self.assertEqual(line, COMPACT_POOLS["damage"])

    @covers_requirement(
        "action-narration::narration-resolution-degrades-instead-of-rejecting-an-action"
    )
    def test_an_unknown_skill_still_renders_the_generic_action(self):
        lines = action_lines("t_only_synthetic", None, catalog={}, families={})
        self.assertTrue(lines)
        self.assertTrue(all(slot_count(line) <= 1 for line in lines))

    @covers_requirement(
        "action-narration::mechanical-entries-narrate-qualitatively-instead-of-listing-state-changes"
    )
    def test_a_row_kind_override_precedes_the_shared_pool(self):
        row = _row("t_override", lines=("這道傷被穩穩記下了。",))
        line = entry_line(
            "damage",
            {},
            skill_key="t_override",
            target_key="t",
            actor="a",
            target="t",
            catalog={"t_override": row},
            families={},
        )
        self.assertEqual(line, "這道傷被穩穩記下了。")


class FamilyKeyTests(unittest.TestCase):
    def test_elemental_skills_split_by_element_and_shape(self):
        fire = Element("fire", "fx", "x")
        assault = _skill(
            "t_fire_assault",
            category=SkillCategory.ELEMENTAL_MAGIC,
            element=fire,
            effects=("damage:fire:magic",),
        )
        succor = _skill(
            "t_fire_succor",
            category=SkillCategory.ELEMENTAL_MAGIC,
            element=fire,
        )
        self.assertEqual(family_key(assault), "elemental_magic:fire:assault")
        self.assertEqual(family_key(succor), "elemental_magic:fire:succor")
        self.assertIn(family_key(assault), FAMILY_ROWS)
        self.assertIn(family_key(succor), FAMILY_ROWS)
        self.assertEqual(
            base_family_key("elemental_magic:fire:assault"),
            "elemental_magic",
        )

    def test_a_sexual_act_resolves_through_its_line_tier(self):
        act = SkillDef(
            key="t_act",
            label="t_act",
            description="t_act",
            kind=SkillKind.ACTIVE,
            target_spec=TargetSpec.SINGLE,
            cost={},
            usable_out_of_combat=True,
            element=None,
            effects=[],
            category=SkillCategory.SEXUAL_ACT,
            group="關係",
        )
        self.assertEqual(family_key(act), "sexual_act:關係")
        self.assertIn(family_key(act), FAMILY_ROWS)


class AuthoredFamilyRowTests(unittest.TestCase):
    @covers_requirement(
        "action-narration::a-resolved-action-opens-with-its-own-skill-s-action-narration",
        "action-narration::every-non-elemental-active-skill-has-its-own-action-narration",
        "action-narration::every-elemental-spell-has-its-own-action-narration",
    )
    def test_two_skills_of_one_family_select_different_openings(self):
        for rows, family in AUTHORED_MODULES:
            for first, second in itertools.combinations(rows, 2):
                for scope in ("scope-one", "scope-two"):
                    with self.subTest(
                        family=family, first=first.key, second=second.key,
                        scope=scope,
                    ):
                        self.assertNotEqual(
                            action_line(
                                first.key,
                                family,
                                scope=scope,
                                target_key="t_target",
                                actor="A",
                                catalog=NARRATION_CATALOG,
                                families={},
                            ),
                            action_line(
                                second.key,
                                family,
                                scope=scope,
                                target_key="t_target",
                                actor="A",
                                catalog=NARRATION_CATALOG,
                                families={},
                            ),
                        )

    def test_no_two_rows_in_one_family_share_a_line(self):
        for rows, family in AUTHORED_MODULES:
            with self.subTest(family=family):
                lines = [line for row in rows for line in row.action]
                self.assertEqual(len(lines), len(set(lines)))

    def test_the_light_register_never_borrows_a_holy_rite_line(self):
        rite_lines = {line for row in HOLY_RITE_ROWS for line in row.action}
        light_lines = {line for row in LIGHT_ROWS for line in row.action}
        with self.subTest(element="light"):
            self.assertFalse(rite_lines & light_lines)

    @covers_requirement(
        "action-narration::authored-lines-carry-a-declared-participant-slot-budget"
    )
    def test_authored_rows_keep_the_shared_line_bounds(self):
        for row in NARRATION_CATALOG.values():
            self.assertTrue(row.action, row.key)
            self.assertLessEqual(len(row.action), 2, row.key)
            for line in row.action:
                with self.subTest(key=row.key, line=line):
                    self.assertEqual(slot_count(line), 1)
                    self.assertFalse(contains_ascii_digit(line))
                    self.assertTrue(
                        composed_fits(line, "{target} 吃了這一擊。")
                    )

    @covers_requirement(
        "action-narration::mechanical-entries-narrate-qualitatively-instead-of-listing-state-changes"
    )
    def test_a_kind_override_names_a_known_entry_kind(self):
        for row in NARRATION_CATALOG.values():
            for kind in row.kind_lines:
                with self.subTest(key=row.key, kind=kind):
                    self.assertIn(kind, NARRATION_KINDS)


class CatalogValidationTests(unittest.TestCase):
    def _validate(self, **kwargs):
        defaults = dict(
            catalog={},
            family_rows={},
            shipped={},
            acts={},
            pending=PENDING_FAMILIES,
        )
        defaults.update(kwargs)
        validate_catalog(**defaults)

    @covers_requirement(
        "action-narration::authored-narration-is-a-catalog-validated-against-the-shipped-registries"
    )
    def test_duplicate_key_is_rejected(self):
        row = _row("t_dup")
        with self.assertRaises(NarrationCatalogError):
            build_catalog([row, row])

    @covers_requirement(
        "action-narration::authored-narration-is-a-catalog-validated-against-the-shipped-registries"
    )
    def test_unknown_key_is_rejected(self):
        with self.assertRaises(NarrationCatalogError):
            self._validate(catalog={"t_unknown": _row("t_unknown")})

    @covers_requirement(
        "action-narration::authored-narration-is-a-catalog-validated-against-the-shipped-registries"
    )
    def test_missing_row_outside_pending_families_is_rejected(self):
        skill = _skill("t_needed", category=SkillCategory.MARTIAL_ARTS)
        with self.assertRaises(NarrationCatalogError):
            self._validate(
                catalog={},
                shipped={"t_needed": skill},
                pending=frozenset(),
            )

    def test_a_pending_family_may_omit_its_rows(self):
        skill = _skill("t_needed", category=SkillCategory.ELEMENTAL_MAGIC)
        self._validate(
            catalog={},
            shipped={"t_needed": skill},
            pending=frozenset({"elemental_magic"}),
        )

    @covers_requirement(
        "action-narration::authored-lines-carry-a-declared-participant-slot-budget"
    )
    def test_an_over_bound_row_is_rejected(self):
        with self.assertRaises(NarrationCatalogError):
            self._validate(
                family_rows={
                    "bad": NarrationRow(
                        key="bad",
                        action=("{actor}" + "字" * 200 + "{target}",),
                    )
                }
            )

    @covers_requirement(
        "action-narration::authored-lines-carry-a-declared-participant-slot-budget"
    )
    def test_a_slot_over_budget_row_is_rejected(self):
        with self.assertRaises(NarrationCatalogError):
            self._validate(
                family_rows={
                    "bad": NarrationRow(
                        key="bad",
                        action=("{actor}{target}{actor}",),
                    )
                }
            )

    def test_a_digit_bearing_row_is_rejected(self):
        with self.assertRaises(NarrationCatalogError):
            self._validate(
                family_rows={
                    "bad": NarrationRow(key="bad", action=("{actor} 施展第 7 式——",))
                }
            )

    @covers_requirement(
        "action-narration::authored-lines-carry-a-declared-participant-slot-budget"
    )
    def test_an_impossible_composed_pair_is_rejected(self):
        with self.assertRaises(NarrationCatalogError):
            self._validate(
                family_rows={
                    "bad": NarrationRow(
                        key="bad",
                        action=("{actor}{target}",),
                    )
                }
            )


class CompositionBudgetTests(unittest.TestCase):
    @covers_requirement(
        "action-narration::authored-lines-carry-a-declared-participant-slot-budget"
    )
    def test_named_lines_are_inside_the_authoring_bound(self):
        for row in FAMILY_ROWS.values():
            for line in row.action:
                self.assertLessEqual(slot_count(line), 2)
                self.assertTrue(
                    composed_fits(line, "{target} 吃了這一擊。"),
                    line,
                )

    def test_choose_line_is_stable_for_one_seed(self):
        seed = narration_seed("scope", "skill", "damage", 1, "target", "solid")
        first = choose_line(KIND_POOLS["damage"], seed, actor="a", target="t")
        second = choose_line(KIND_POOLS["damage"], seed, actor="a", target="t")
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
