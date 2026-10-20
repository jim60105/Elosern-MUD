"""Fixed-fixture reader tests: player characters (task 2.1 / 6.1).

Establishes the delta requirement "Complete curated entity summaries" for the
player-character kind, including the two hard invariants: stored truth and
``disguised_stats`` are emitted side by side (the disguise labelled 僅顯示用 and
never merged into a true trait), and currency stays integer copper with a
derived display. Its ``gm-runtime-state`` requirement annotation was attached
when the delta spec synced into the main spec at archive.
"""

from __future__ import annotations

from contextlib import ExitStack
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from django.test import Client
from evennia.utils import create
from evennia.utils.test_resources import EvenniaTest
from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from world.lore.items import EquipmentModifierKey, EquipmentSlot
from world.rules.affinity_config import AffinityConfig, AffinityStage
from world.rules.buffs import apply_buff
from world.rules.equipment_effects import EquipmentEffectRule
from world.rules.rulebook.schema import Rule
from world.rules.status_display import ConditionDisplay
from world.rules.status_query import (
    StatBreakdownRow,
    StatLayer,
    StatusQueryError,
    build_character_read_model,
)
from world.rules.traits import restore_gauges_to_full
from world.skills.handler import ConferredSkillGrant
from world.skills.registry import SkillCategory, SkillKind
from world.tests.synthetic_data import (
    SYNTH_BUFFS,
    SYNTH_RACES,
    make_item,
    make_skill,
    synthetic_registries,
)

from tools.spec_traceability import covers_requirement
from web.gm.readers import characters
from web.gm.readers._entities import (
    attribute_rows,
    read_attr,
    stored_attribute_keys,
)
from web.gm.tests._state_support import (
    column_values,
    failed_sections,
    field_value,
    link_kinds,
    open_synthetic_scope,
    row_by_key,
    row_value,
    section_keys,
    section_of,
)
from web.gm.tests._support import GmTestCase

SYNTH_RACE = "t_duskmari"

EXPECTED_SECTIONS = [
    "identity",
    "resources",
    "conditions",
    "traits",
    "disguise",
    "breakdown",
    "skills",
    "lineage",
    "equipment",
    "inventory",
    "wallet",
    "guild",
    "titles",
    "affinity",
    "party",
    "possession",
    "sexual",
    "links",
]

def _open_character_scope(case) -> None:
    open_synthetic_scope(case, "races", "static_tiers", "subraces")


class CharacterReaderTests(EvenniaTest):
    character_typeclass = PlayerCharacter

    def setUp(self):
        _open_character_scope(self)
        super().setUp()
        self.player = create.create_object(
            PlayerCharacter, key="t_reader_player", location=self.room1
        )
        self.player.race = SYNTH_RACE
        self.player.apply_race_baseline()
        restore_gauges_to_full(self.player)
        self.player.sex = "female"
        self.player.age = 24
        self.player.apparent_age = 19
        self.player.db.wallet = 12_345
        self.player.db.inventory = ["t_ember_spray", "t_ember_spray", "t_iron_fang"]
        self.player.db.equipment = {
            "weapon_main": "t_iron_fang",
            "accessories": ["t_wayfarer_pass"],
        }
        self.player.guild_rank = "t_bronze"

    @covers_requirement("gm-runtime-state::complete-curated-entity-summaries")
    def test_detail_exposes_every_curated_character_section(self):
        detail = characters.character_detail(self.player)
        self.assertEqual(detail["kind"], "characters")
        self.assertEqual(detail["dbref"], self.player.pk)
        self.assertEqual(section_keys(detail), EXPECTED_SECTIONS)
        self.assertEqual(failed_sections(detail), {})

    def test_identity_reports_stored_identity_fields(self):
        detail = characters.character_detail(self.player)
        identity = section_of(detail, "identity")
        self.assertEqual(row_value(identity, "年齡"), 24)
        self.assertEqual(row_value(identity, "外觀年齡"), 19)
        self.assertEqual(row_value(identity, "性別"), "female")
        self.assertEqual(row_value(identity, "種族"), SYNTH_RACES[SYNTH_RACE].display_name_zh)
        self.assertEqual(row_value(identity, "當前房間"), f"#{self.room1.pk}")

    @covers_requirement("gm-runtime-state::complete-curated-entity-summaries")
    def test_disguise_is_emitted_separately_and_never_replaces_true_traits(self):
        true_attack = int(self.player.traits.atk_phys.value)
        self.player.db.disguised_stats = {"atk_phys": true_attack - 5}
        detail = characters.character_detail(self.player)
        traits = section_of(detail, "traits")
        self.assertEqual(row_by_key(traits, "atk_phys")["value"], true_attack)
        disguise = section_of(detail, "disguise")
        self.assertIn("僅顯示用", disguise["note"])
        self.assertEqual(row_by_key(disguise, "atk_phys")["value"], true_attack - 5)

    def test_breakdown_decomposes_each_trait_from_base_to_effective(self):
        detail = characters.character_detail(self.player)
        breakdown = section_of(detail, "breakdown")
        hp = next(group for group in breakdown["groups"] if group["key"] == "hp")
        self.assertEqual(hp["rows"][0]["label"], "基礎")
        self.assertTrue(hp["note"].startswith("有效值 "))

    @covers_requirement("gm-runtime-state::complete-curated-entity-summaries")
    def test_wallet_stays_integer_copper_with_a_derived_display(self):
        detail = characters.character_detail(self.player)
        wallet = section_of(detail, "wallet")
        self.assertEqual(row_value(wallet, "銅幣（整數）"), 12_345)
        self.assertEqual(row_value(wallet, "換算"), characters.money_display(12_345))
        self.assertIsInstance(row_value(wallet, "銅幣（整數）"), int)

    def test_inventory_counts_and_equipment_slots_are_projected(self):
        detail = characters.character_detail(self.player)
        inventory = section_of(detail, "inventory")
        self.assertEqual(column_values(inventory, "key"), ["t_ember_spray", "t_iron_fang"])
        self.assertEqual(column_values(inventory, "quantity"), [2, 1])
        equipment = section_of(detail, "equipment")
        self.assertEqual(column_values(equipment, "slot"), ["weapon_main", "accessory"])
        self.assertEqual(column_values(equipment, "key"), ["t_iron_fang", "t_wayfarer_pass"])

    @covers_requirement(
        "skill-lineage-panel::the-lineage-read-model-is-pure-derived-and-side-effect-free"
    )
    def test_synthetic_commander_lineage_section_is_available_and_unchanged(self):
        """A commander under the installed synthetic catalog reads its lineage.

        The read model caches the reverse-edge index at validation time, so a
        scoped synthetic skill catalog must rebuild it before the GM detail
        reader (a separate consumer from the text command and the party panel)
        renders the section. The section stays the bounded view's own graphs,
        and repeated reads write nothing.
        """
        from world.rules.lineage_query import build_lineage_view
        from web.webclient.presentation.lineage import bounded_lineage_view

        self.player.db.skills = {"active": ["t_ember_burst"], "passive": []}
        self.player.db.skill_proficiency = {"t_ember_burst": 30.0}
        before = (
            deepcopy(dict(self.player.db.skills)),
            deepcopy(dict(self.player.db.skill_proficiency)),
            stored_attribute_keys(self.player),
        )

        with synthetic_registries("skills"):
            first = characters.character_detail(self.player)
            self.assertNotIn("lineage", failed_sections(first))
            lineage = section_of(first, "lineage")
            self.assertEqual(lineage["note"], "完成 0 / 1")

            graph = next(
                group for group in lineage["groups"] if group["key"] == "t_ember_burst"
            )
            view = bounded_lineage_view(build_lineage_view(self.player))
            nodes = next(
                item for item in view.graphs if item.graph_id == "t_ember_burst"
            ).nodes
            self.assertEqual(
                [row["key"] for row in graph["rows"]],
                [node.skill_key for node in nodes],
            )
            self.assertEqual(
                [row["label"] for row in graph["rows"]],
                [node.display_name_zh for node in nodes],
            )
            self.assertEqual(
                [row["value"] for row in graph["rows"]],
                [
                    f"Lv.{node.level}" + ("（已滿）" if node.capped else "")
                    for node in nodes
                ],
            )

            # The same read again is byte-identical.
            self.assertEqual(
                section_of(characters.character_detail(self.player), "lineage"),
                lineage,
            )

        after = (
            deepcopy(dict(self.player.db.skills)),
            deepcopy(dict(self.player.db.skill_proficiency)),
            stored_attribute_keys(self.player),
        )
        self.assertEqual(after, before)

    def test_every_relationship_identifier_is_a_link(self):
        detail = characters.character_detail(self.player)
        links = section_of(detail, "links")
        kinds = link_kinds(links)
        self.assertLessEqual({"rooms", "quests", "memories", "dialogue"}, kinds)

    @covers_requirement("gm-runtime-state::complete-curated-entity-summaries")
    def test_affinity_stages_render_as_names_in_the_detail_api_without_writes(self):
        npc = create.create_object(NPC, key="t_reader_affinity_npc")
        config = AffinityConfig(
            invite_threshold=10,
            daily_interaction_cap=5,
            quest_completion_gain=2,
            friendly_fire_penalty_per_hit=1,
            sexual_forced_penalty=3,
            cap_breaks=(),
            stages=(
                AffinityStage("t_distant", 0, "合成疏遠階段", "合成描述"),
                AffinityStage("t_close", 10, "合成親近階段", "合成描述"),
            ),
        )
        client = Client()
        client.force_login(self.account)
        with patch("world.rules.affinity.get_config", return_value=config):
            for value, expected_name in (
                (9, "合成疏遠階段"),
                (10, "合成親近階段"),
                (25, "合成親近階段"),
            ):
                with self.subTest(value=value):
                    npc.db.relations_data = {
                        str(self.player.pk): {
                            "value": value,
                            "cap": 120,
                            "daily_gain": 2,
                            "daily_tick": 1,
                        }
                    }
                    before = deepcopy(dict(npc.db.relations_data))
                    response = client.get(f"/gm/api/state/characters/{self.player.pk}")
                    self.assertEqual(response.status_code, 200)
                    body = response.json()
                    self.assertIs(body["ok"], True)
                    affinity = section_of(body["data"], "affinity")
                    cells = next(
                        entry["cells"]
                        for entry in affinity["rows"]
                        if entry["key"] == str(npc.pk)
                    )
                    self.assertEqual(cells["stage"]["value"], expected_name)
                    self.assertEqual(cells["value"]["value"], value)
                    self.assertEqual(cells["cap"]["value"], 120)
                    self.assertEqual(dict(npc.db.relations_data), before)

    def test_links_expose_the_current_room_and_quests(self):
        detail = characters.character_detail(self.player)
        links = section_of(detail, "links")
        ids = {chip["label"]: chip["link"]["kind"] for chip in links["chips"]}
        self.assertEqual(ids[self.room1.key], "rooms")
        self.assertEqual(ids["任務紀錄"], "quests")

    def test_list_item_is_summary_only(self):
        item = characters.character_list_item(self.player)
        self.assertEqual(item["kind"], "characters")
        self.assertEqual(item["id"], str(self.player.pk))
        self.assertEqual(set(field_value(item, label) is not None for label in (
            "待完成建立",
            "種族",
            "所在位置",
        )), {True})


class MissingStoredDefaultTests(EvenniaTest):
    """A missing stored Attribute is reported, never materialized (design §2)."""

    character_typeclass = PlayerCharacter

    def setUp(self):
        _open_character_scope(self)
        super().setUp()
        self.player = create.create_object(
            PlayerCharacter, key="t_reader_pending", location=self.room1
        )
        self.player.race = SYNTH_RACE
        self.player.apply_race_baseline()
        restore_gauges_to_full(self.player)
        # The wallet Attribute is deliberately absent from a freshly created
        # shell; a product read must not fill it in.
        self.player.attributes.remove("wallet")

    @covers_requirement("gm-runtime-state::protected-read-only-inspection-boundary")
    def test_missing_wallet_reports_a_section_error_without_creating_it(self):
        before = stored_attribute_keys(self.player)
        self.assertIsNone(read_attr(self.player, "wallet", default=None))
        detail = characters.character_detail(self.player)
        failures = failed_sections(detail)
        self.assertIn("wallet", failures)
        self.assertEqual(failures["wallet"], "source_unavailable")
        # Everything that does not depend on the wallet still renders.
        self.assertNotIn("identity", failures)
        self.assertNotIn("resources", failures)
        self.assertIsNone(read_attr(self.player, "wallet", default=None))
        self.assertEqual(stored_attribute_keys(self.player), before)


# ---------------------------------------------------------------------------
# Fractional percentage controls. Each invented buff activates exactly one
# invented rule, so the real read model composes one named layer per authored
# control; the multiplier comes from one invented passive skill. No shipped
# catalog literal appears here.
# ---------------------------------------------------------------------------

#: ``(buff key, authored percentage, display label)`` — two fractions and two
#: integral controls, positives and negatives.
_PCT_CONTROLS = (
    ("t_gm_frac_up", "+12.5%", "合成上揚"),
    ("t_gm_frac_down", "-2.5%", "合成下調"),
    ("t_gm_int_up", "+10%", "合成整數上揚"),
    ("t_gm_int_down", "-10%", "合成整數下調"),
)
_FLAT_BUFF = "t_gm_frac_flat_source"
_FLAT_RULE_ID = "t_gm_frac_flat_rule"
_FLAT_LABEL = "合成小數固定值"
_FLAT_AMOUNT = 2.5
_MULT_SKILL = make_skill(
    "t_gm_frac_mult",
    label="合成倍率",
    kind=SkillKind.PASSIVE,
    effects=["stat_multiply:atk_phys:1.5"],
    category=SkillCategory.ENHANCEMENT,
)
_MULT_FACTOR = 1.5
#: A conferred grant keeps the multiplier out of ``db.skills``, so the
#: unrelated lineage section still reads its ordinary (empty) owning set.
_MULT_GRANT = ConferredSkillGrant("t_gm_frac_source", _MULT_SKILL.key, 1.0)
_MULT_LAYER_NAME = f"{_MULT_SKILL.label}（1）"
_AGILITY_BASE = 40
_ATTACK_BASE = 20
#: One invented accessory contributes a flat defense layer, so the regression
#: covers all three layer sources, not only ``skill`` and ``condition``.
_GEAR_KEY = "t_gm_frac_gear"
_GEAR_LABEL = "合成護符"
_GEAR_MODIFIER = tuple(EquipmentModifierKey)[1]
_GEAR_FLAT = 3
_GEAR = make_item(
    _GEAR_KEY,
    display_name_zh=_GEAR_LABEL,
    equipment_slot=EquipmentSlot.ACCESSORY,
    modifier_key=_GEAR_MODIFIER,
)
_GEAR_RULE = EquipmentEffectRule(
    adjustments={"defense": _GEAR_FLAT},
    gauge_caps={},
    immune=(),
    attached_buffs=(),
    exposure_bias=0,
)
#: 40 × (+12.5 − 2.5 + 10 − 10 → +10%) and round(20 × 1.5) + 2.5.
_AGILITY_EFFECTIVE = 44.0
_ATTACK_EFFECTIVE = 32.5
_BUFF_KEYS = (*[key for key, _, _ in _PCT_CONTROLS], _FLAT_BUFF)

_FRACTIONAL_RULES = [
    Rule(f"{key}_rule", {"buff_active": key}, {"agility": pct})
    for key, pct, _ in _PCT_CONTROLS
] + [Rule(_FLAT_RULE_ID, {"buff_active": _FLAT_BUFF}, {"atk_phys": _FLAT_AMOUNT})]

_FRACTIONAL_DISPLAY = {
    entry.code: entry
    for entry in (
        *[
            ConditionDisplay(
                f"{key}_rule",
                label,
                "beneficial" if pct.startswith("+") else "harmful",
            )
            for key, pct, label in _PCT_CONTROLS
        ],
        ConditionDisplay(_FLAT_RULE_ID, _FLAT_LABEL, "beneficial"),
        *[ConditionDisplay(key, label, "informational") for key, _, label in _PCT_CONTROLS],
        ConditionDisplay(_FLAT_BUFF, "合成固定值來源", "informational"),
    )
}


def _open_fractional_scope(case) -> None:
    """Open the synthetic catalogs plus the invented rule and display tables."""
    open_synthetic_scope(
        case,
        "races",
        "static_tiers",
        "subraces",
        "buffs",
        "items",
        extra={
            "buffs": {
                key: replace(SYNTH_BUFFS["t_moss_veil"], key=key) for key in _BUFF_KEYS
            },
            "items": {_GEAR.key: _GEAR},
        },
    )
    stack = ExitStack()
    # The kit's prerequisite graph cycles when the whole synthetic skill
    # catalog replaces the registry, which would fail the unrelated lineage
    # section; the multiplier row only needs this one definition.
    stack.enter_context(
        patch(
            "world.rules.status_query.breakdown.SKILL_REGISTRY",
            {_MULT_SKILL.key: _MULT_SKILL},
        )
    )
    stack.enter_context(
        patch("world.rules.combat_modifiers._RULES", new=list(_FRACTIONAL_RULES))
    )
    stack.enter_context(
        patch(
            "world.rules.equipment_effects.EQUIPMENT_EFFECT_RULES",
            {_GEAR_MODIFIER: _GEAR_RULE},
        )
    )
    stack.enter_context(
        patch.dict("world.rules.status_display.STATUS_DISPLAY", _FRACTIONAL_DISPLAY)
    )
    case.addCleanup(stack.close)


def _fractional_player(case) -> PlayerCharacter:
    """A player whose authoritative read model carries every authored control."""
    player = create.create_object(
        PlayerCharacter, key="t_reader_fractional", location=case.room1
    )
    player.race = SYNTH_RACE
    player.apply_race_baseline()
    restore_gauges_to_full(player)
    player.traits.agility.base = _AGILITY_BASE
    player.traits.atk_phys.base = _ATTACK_BASE
    player.db.wallet = 0
    player.db.inventory = []
    player.db.equipment = {
        "weapon_main": None,
        "weapon_off": None,
        "armor": None,
        "accessories": [_GEAR.key],
    }
    player.db.skill_grants = [_MULT_GRANT]
    for key in _BUFF_KEYS:
        apply_buff(player, key)
    return player


def _assert_fractional_breakdown(case, detail, player) -> None:
    """Every control reads with its true value, provenance and effective total."""
    case.assertNotIn("breakdown", failed_sections(detail))
    breakdown = section_of(detail, "breakdown")
    case.assertEqual(breakdown["type"], "groups")
    groups = {entry["key"]: entry for entry in breakdown["groups"]}

    agility = groups["agility"]
    for key, pct, label in _PCT_CONTROLS:
        entry = row_by_key(agility, f"agility:condition:{label}")
        case.assertEqual(entry["label"], f"{label}（condition）")
        case.assertEqual(entry["value"], pct)
        case.assertTrue(entry["mono"])
    case.assertEqual(agility["rows"][0]["label"], "基礎")
    case.assertEqual(agility["rows"][0]["value"], _AGILITY_BASE)
    case.assertEqual(agility["note"], f"有效值 {_AGILITY_EFFECTIVE}")

    attack = groups["atk_phys"]
    multiplier = row_by_key(attack, f"atk_phys:skill:{_MULT_LAYER_NAME}")
    case.assertEqual(multiplier["label"], f"{_MULT_LAYER_NAME}（skill）")
    case.assertEqual(multiplier["value"], f"×{_MULT_FACTOR}")
    flat = row_by_key(attack, f"atk_phys:condition:{_FLAT_LABEL}")
    case.assertEqual(flat["label"], f"{_FLAT_LABEL}（condition）")
    case.assertEqual(flat["value"], f"+{_FLAT_AMOUNT}")
    case.assertEqual(attack["rows"][0]["value"], _ATTACK_BASE)
    case.assertEqual(attack["note"], f"有效值 {_ATTACK_EFFECTIVE}")

    defense = groups["defense"]
    gear = row_by_key(defense, f"defense:equipment:{_GEAR_LABEL}")
    case.assertEqual(gear["label"], f"{_GEAR_LABEL}（equipment）")
    case.assertEqual(gear["value"], f"+{_GEAR_FLAT}")

    # Every rendered layer, in order, matches the authoritative read model,
    # and the rendered totals agree with it.
    authoritative = {row.key: row for row in build_character_read_model(player).breakdown}
    for key in ("agility", "atk_phys", "defense"):
        rendered = groups[key]["rows"][1:]
        layers = authoritative[key].layers
        case.assertEqual(
            [entry["key"] for entry in rendered],
            [f"{key}:{layer.source}:{layer.name}" for layer in layers],
        )
        case.assertEqual(
            [entry["label"] for entry in rendered],
            [f"{layer.name}（{layer.source}）" for layer in layers],
        )
    case.assertEqual(authoritative["agility"].effective, _AGILITY_EFFECTIVE)
    case.assertEqual(authoritative["atk_phys"].effective, _ATTACK_EFFECTIVE)
    case.assertEqual(agility["note"], f"有效值 {authoritative['agility'].effective}")
    case.assertEqual(attack["note"], f"有效值 {authoritative['atk_phys'].effective}")


class FractionalBreakdownTests(EvenniaTest):
    """Fractional and integral layer amounts through the real character reader."""

    character_typeclass = PlayerCharacter

    def setUp(self):
        _open_fractional_scope(self)
        super().setUp()
        self.player = _fractional_player(self)

    @covers_requirement("gm-runtime-state::complete-curated-entity-summaries")
    def test_fractional_percentage_flat_and_multiplier_layers_are_readable(self):
        detail = characters.character_detail(self.player)
        _assert_fractional_breakdown(self, detail, self.player)


class FormattingPrecisionTests(TestCase):
    """The layer formatter keeps every authored fraction, not six digits."""

    def test_percentage_keeps_precision_beyond_six_significant_digits(self):
        row_fixture = StatBreakdownRow(
            key="agility",
            base=_AGILITY_BASE,
            current=0.0,
            effective=0.0,
            layers=(StatLayer("condition", "合成精度", "pct", 12.3456789),),
        )
        model = SimpleNamespace(breakdown=(row_fixture,))
        with patch(
            "world.rules.status_query.build_character_read_model", return_value=model
        ):
            breakdown = characters.breakdown_section(object())
        entry = row_by_key(breakdown["groups"][0], "agility:condition:合成精度")
        self.assertEqual(entry["value"], "+12.3456789%")


class FractionalBreakdownApiTests(GmTestCase):
    """The protected character-detail endpoint serves and isolates the breakdown."""

    character_typeclass = PlayerCharacter

    def setUp(self):
        _open_fractional_scope(self)
        super().setUp()
        self.player = _fractional_player(self)
        self.url = f"/gm/api/state/characters/{self.player.pk}"

    @covers_requirement("gm-runtime-state::complete-curated-entity-summaries")
    def test_detail_api_serves_fractional_layers_without_mutating_state(self):
        before = attribute_rows(self.player)
        detail = self.assert_ok_envelope(self.client_for("developer").get(self.url))
        _assert_fractional_breakdown(self, detail, self.player)
        self.assertEqual(attribute_rows(self.player), before)

    @covers_requirement("gm-runtime-state::protected-read-only-inspection-boundary")
    def test_detail_api_keeps_the_protected_boundary(self):
        self.assert_error_envelope(
            self.client_for("anonymous").get(self.url), 401, "unauthenticated"
        )
        self.assert_error_envelope(
            self.client_for("player").get(self.url), 403, "forbidden"
        )

    @covers_requirement("gm-runtime-state::complete-curated-entity-summaries")
    def test_invalid_status_source_isolates_only_the_sections_that_use_it(self):
        before = attribute_rows(self.player)
        with patch(
            "world.rules.status_query.build_character_read_model",
            side_effect=StatusQueryError("synthetic invalid source"),
        ):
            detail = self.assert_ok_envelope(self.client_for("developer").get(self.url))
        expected = {
            "traits",
            "disguise",
            "breakdown",
            "skills",
            "equipment",
            "wallet",
            "guild",
        }
        failures = failed_sections(detail)
        self.assertEqual(set(failures), expected)
        self.assertEqual(set(failures.values()), {"source_unavailable"})
        # The status source's failure never takes down an independent section.
        for key in ("identity", "resources", "conditions", "lineage", "links"):
            self.assertNotIn(key, failures)
        self.assertEqual(attribute_rows(self.player), before)
