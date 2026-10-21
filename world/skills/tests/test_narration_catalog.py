"""Pure tests for the authored narration catalog engine.

No database and no Evennia runtime. Engine cases use file-local synthetic rows
and bands, so the checks establish the engine's contract rather than echoing
registry data; the authored-family cases read the shipped data modules only to
establish row shape, distinctness and bound adherence, never key content.
"""

from __future__ import annotations

import itertools
import unittest
from types import SimpleNamespace

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
    SEXUAL_COUNTER_LINES,
    TRANSITION_LINES,
    BandTable,
    NarrationCatalogError,
    NarrationRow,
    RoleClause,
    action_lines,
    base_family_key,
    composed_fits,
    compose_first_line,
    entry_line,
    family_key,
    slot_count,
)
from world.skills.narration.data_sexual_combat import ROWS as SEXUAL_COMBAT_ROWS
from world.skills.narration.data_sexual_divine import ROWS as SEXUAL_DIVINE_ROWS
from world.skills.narration.data_sexual_interspecies import (
    ROWS as SEXUAL_INTERSPECIES_ROWS,
)
from world.skills.narration.data_sexual_partner import ROWS as SEXUAL_PARTNER_ROWS
from world.skills.narration.data_sexual_shame import ROWS as SEXUAL_SHAME_ROWS
from world.skills.narration.data_sexual_solo import ROWS as SEXUAL_SOLO_ROWS
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
from world.skills.narration.pools import (
    SEXUAL_COUNTER_SHARED_LINES,
    VERDICT_LINES,
)
from world.skills.narration.validation import (
    build_catalog,
    validate_catalog,
    validate_sexual_pools,
)
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
SEXUAL_MODULES = (
    (SEXUAL_SOLO_ROWS, "sexual_act:獨處"),
    (SEXUAL_SHAME_ROWS, "sexual_act:羞恥"),
    (SEXUAL_PARTNER_ROWS, "sexual_act:關係"),
    (SEXUAL_COMBAT_ROWS, "sexual_act:戰鬥"),
    (SEXUAL_INTERSPECIES_ROWS, "sexual_act:異種"),
    (SEXUAL_DIVINE_ROWS, "sexual_act:神之秘法"),
)

#: Every authored module, used by the whole-catalog distinctness checks.
AUTHORED_MODULES = (*ELEMENTAL_MODULES, *AUTHORED_FAMILIES, *SEXUAL_MODULES)


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
        self.assertEqual(PENDING_FAMILIES, frozenset())


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


def _act_stub(
    *,
    events: tuple[str, ...] = (),
    pair_events: tuple[tuple[tuple[str, str], str], ...] = (),
    actor_counters: tuple[str, ...] = (),
    participant_counters: tuple[str, ...] = (),
) -> SimpleNamespace:
    return SimpleNamespace(
        sexual_events=events,
        pair_events=pair_events,
        actor_counters=actor_counters,
        participant_counters=participant_counters,
    )


class SexualRowTests(unittest.TestCase):
    @covers_requirement(
        "action-narration::sexual-verdicts-and-participant-roles-drive-the-sexual-narration"
    )
    def test_every_verdict_keeps_the_act_clause_and_changes_only_the_verdict(
        self,
    ):
        row = NarrationRow("t_act", action=("{actor} 朝對方伸手——",))
        composed = []
        for payload in (
            {"resisted": True, "auto_comply": False, "roll": 90},
            {"resisted": False, "auto_comply": False, "roll": 20},
            {"resisted": False, "auto_comply": True, "roll": None},
        ):
            outcome = entry_line(
                "sexual_resist",
                payload,
                skill_key="t_act",
                target_key="t_target",
                actor="hero",
                target="t_target",
                catalog={"t_act": row},
                families={},
            )
            composed.append(
                compose_first_line(
                    "t_act",
                    None,
                    outcome,
                    scope="verdict",
                    target_key="t_target",
                    actor="hero",
                    target="t_target",
                    catalog={"t_act": row},
                    families={},
                )
            )
        for line in composed:
            self.assertTrue(line.startswith("{actor} 朝對方伸手——"), line)
        self.assertEqual(len(set(composed)), 3)

    @covers_requirement(
        "action-narration::sexual-verdicts-and-participant-roles-drive-the-sexual-narration"
    )
    def test_the_auto_complied_clause_is_not_the_ordinary_complied_clause(self):
        complied = entry_line(
            "sexual_resist",
            {"resisted": False, "auto_comply": False, "roll": 40},
            actor="hero",
            target="t_target",
        )
        auto = entry_line(
            "sexual_resist",
            {"resisted": False, "auto_comply": True, "roll": None},
            actor="hero",
            target="t_target",
        )
        self.assertNotEqual(complied, auto)
        self.assertIn("{target}", complied)
        self.assertIn("{target}", auto)

    @covers_requirement(
        "action-narration::sexual-verdicts-and-participant-roles-drive-the-sexual-narration"
    )
    def test_a_cast_without_a_resist_entry_opens_on_its_own_outcome(self):
        row = NarrationRow(
            "t_solo",
            action=("{actor} 朝自己伸手——",),
            performer_lines={"pleasure_gain": ("{actor} 的一刻。",)},
        )
        outcome = entry_line(
            "pleasure_gain",
            {"amount": 10},
            skill_key="t_solo",
            actor_key="hero",
            target_key="hero",
            actor="hero",
            target="hero",
            catalog={"t_solo": row},
            families={},
        )
        composed = compose_first_line(
            "t_solo",
            None,
            outcome,
            scope="solo",
            target_key="hero",
            actor="hero",
            target="hero",
            catalog={"t_solo": row},
            families={},
        )
        self.assertEqual(composed, "{actor} 朝自己伸手——" + outcome)
        for verdict_lines in VERDICT_LINES.values():
            for verdict_line in verdict_lines:
                self.assertNotIn(verdict_line, composed)

    @covers_requirement(
        "action-narration::sexual-verdicts-and-participant-roles-drive-the-sexual-narration"
    )
    def test_a_row_voices_the_performer_and_the_participant_separately(self):
        row = NarrationRow(
            "t_act",
            action=("{actor} 伸手——",),
            performer_lines={"pleasure_gain": ("{actor} 記下自己的一刻。",)},
            participant_lines={"pleasure_gain": ("{target} 記下被碰的一刻。",)},
        )
        caster = entry_line(
            "pleasure_gain",
            {"amount": 10},
            skill_key="t_act",
            actor_key="hero",
            target_key="hero",
            actor="hero",
            target="hero",
            catalog={"t_act": row},
            families={},
        )
        other = entry_line(
            "pleasure_gain",
            {"amount": 10},
            skill_key="t_act",
            actor_key="hero",
            target_key="partner",
            actor="hero",
            target="partner",
            catalog={"t_act": row},
            families={},
        )
        self.assertEqual(caster, "{actor} 記下自己的一刻。")
        self.assertEqual(other, "{target} 記下被碰的一刻。")

    @covers_requirement(
        "action-narration::sexual-verdicts-and-participant-roles-drive-the-sexual-narration"
    )
    def test_a_role_clause_precedes_a_plain_kind_override(self):
        row = NarrationRow(
            "t_act",
            action=("{actor} 伸手——",),
            kind_lines={"pleasure_gain": ("通用的一刻。",)},
            performer_lines={"pleasure_gain": ("{actor} 自己的一刻。",)},
        )
        caster = entry_line(
            "pleasure_gain",
            {"amount": 10},
            skill_key="t_act",
            actor_key="hero",
            target_key="hero",
            actor="hero",
            target="hero",
            catalog={"t_act": row},
            families={},
        )
        other = entry_line(
            "pleasure_gain",
            {"amount": 10},
            skill_key="t_act",
            actor_key="hero",
            target_key="partner",
            actor="hero",
            target="partner",
            catalog={"t_act": row},
            families={},
        )
        self.assertEqual(caster, "{actor} 自己的一刻。")
        self.assertEqual(other, "通用的一刻。")

    @covers_requirement(
        "action-narration::authored-narration-is-a-catalog-validated-against-the-shipped-registries"
    )
    def test_a_role_clause_over_the_shared_bound_is_rejected(self):
        with self.assertRaises(NarrationCatalogError):
            validate_catalog(
                catalog={},
                family_rows={
                    "t_bad": NarrationRow(
                        "t_bad",
                        performer_lines={
                            "pleasure_gain": ("{actor}" + "字" * 200,)
                        },
                    )
                },
                shipped={},
                acts={},
            )


class SexualPoolSelectionTests(unittest.TestCase):
    @covers_requirement(
        "action-narration::sexual-verdicts-and-participant-roles-drive-the-sexual-narration"
    )
    def test_a_pooled_counter_voices_the_entries_own_participant(self):
        pool = {
            "t_counter": RoleClause(
                performer=("{actor} 記下自己做的事。",),
                participant=("{target} 記下被做的事。",),
            )
        }
        shared_act = _act_stub(participant_counters=("t_counter",))
        caster = entry_line(
            "sexual_counter",
            {"counter": "t_counter"},
            act=shared_act,
            actor_key="hero",
            target_key="hero",
            actor="hero",
            target="hero",
            counters=pool,
        )
        other = entry_line(
            "sexual_counter",
            {"counter": "t_counter"},
            act=shared_act,
            actor_key="hero",
            target_key="partner",
            actor="hero",
            target="partner",
            counters=pool,
        )
        self.assertEqual(caster, "{actor} 記下自己做的事。")
        self.assertEqual(other, "{target} 記下被做的事。")

    @covers_requirement(
        "action-narration::sexual-verdicts-and-participant-roles-drive-the-sexual-narration"
    )
    def test_a_performer_only_counter_never_renders_the_participant_clause(self):
        pool = {
            "t_counter": RoleClause(
                performer=("{actor} 記下自己做的事。",),
                participant=("{target} 記下被做的事。",),
            )
        }
        solo_act = _act_stub(
            actor_counters=("t_counter",), participant_counters=()
        )
        line = entry_line(
            "sexual_counter",
            {"counter": "t_counter"},
            act=solo_act,
            actor_key="hero",
            target_key="partner",
            actor="hero",
            target="partner",
            counters=pool,
        )
        self.assertEqual(line, "{actor} 記下自己做的事。")

    @covers_requirement(
        "action-narration::narration-resolution-degrades-instead-of-rejecting-an-action"
    )
    def test_an_unpooled_counter_degrades_to_the_role_fallback(self):
        line = entry_line(
            "sexual_counter",
            {"counter": "t_unpooled"},
            actor_key="hero",
            target_key="partner",
            actor="hero",
            target="partner",
            counters={},
        )
        self.assertIn(line, SEXUAL_COUNTER_SHARED_LINES)

    @covers_requirement(
        "action-narration::mechanical-entries-narrate-qualitatively-instead-of-listing-state-changes"
    )
    def test_a_transition_selects_by_event_name_and_degrades_when_unknown(self):
        pool = {"t_event": ("{target} 越過了一道界線。",)}
        known = entry_line(
            "sexual_transition",
            {"event": "t_event"},
            actor="hero",
            target="t_target",
            transitions=pool,
        )
        unknown = entry_line(
            "sexual_transition",
            {"event": "t_unknown"},
            actor="hero",
            target="t_target",
            transitions=pool,
        )
        self.assertEqual(known, "{target} 越過了一道界線。")
        self.assertIn(unknown, KIND_POOLS["sexual_transition"])

class SexualPoolCoverageTests(unittest.TestCase):
    @covers_requirement(
        "action-narration::authored-narration-is-a-catalog-validated-against-the-shipped-registries"
    )
    def test_the_pools_accept_exactly_the_declared_names(self):
        act = _act_stub(
            events=("t_event",),
            pair_events=((("female", "male"), "t_pair_event"),),
            actor_counters=("t_counter",),
            participant_counters=("t_counter",),
        )
        validate_sexual_pools(
            {"t_act": act},
            transitions={"t_event": ("一。",), "t_pair_event": ("二。",)},
            counters={
                "t_counter": RoleClause(
                    performer=("{actor} 一。",), participant=("{target} 二。",)
                )
            },
        )

    @covers_requirement(
        "action-narration::authored-narration-is-a-catalog-validated-against-the-shipped-registries"
    )
    def test_an_event_without_a_clause_fails_validation_naming_it(self):
        act = _act_stub(events=("t_missing_event",))
        with self.assertRaises(NarrationCatalogError) as caught:
            validate_sexual_pools({"t_act": act}, transitions={}, counters={})
        self.assertIn("t_missing_event", str(caught.exception))

    @covers_requirement(
        "action-narration::authored-narration-is-a-catalog-validated-against-the-shipped-registries"
    )
    def test_a_counter_without_clauses_fails_validation_naming_it(self):
        act = _act_stub(actor_counters=("t_missing_counter",))
        with self.assertRaises(NarrationCatalogError) as caught:
            validate_sexual_pools({"t_act": act}, transitions={}, counters={})
        self.assertIn("t_missing_counter", str(caught.exception))

    @covers_requirement(
        "action-narration::authored-narration-is-a-catalog-validated-against-the-shipped-registries"
    )
    def test_an_unemitted_pool_entry_fails_validation_naming_it(self):
        with self.assertRaises(NarrationCatalogError) as caught:
            validate_sexual_pools(
                {},
                transitions={"t_orphan_event": ("一。",)},
                counters={},
            )
        self.assertIn("t_orphan_event", str(caught.exception))

    def test_a_role_clause_requires_both_roles(self):
        for keyword in (
            {"performer": (), "participant": ("{target} 二。",)},
            {"performer": ("{actor} 一。",), "participant": ()},
        ):
            with self.subTest(**keyword):
                with self.assertRaises(NarrationCatalogError):
                    RoleClause(**keyword)


if __name__ == "__main__":
    unittest.main()
