"""Stat-breakdown read model tests (expose-stat-breakdown-read-model tasks 1.1–1.4).

Every composition test pins the builder to the shipped authoritative
operations: the ``SkillHandler.effective_value`` fold (banker's rounding,
single final ``round``), ``combat._adjusted_attack``/``_adjusted_defense``
flat sums, ``combat_modifiers.adjusted_agility`` (percent-then-flat, floored
at zero), and the gauge-ceiling reader. Fail-closed fixtures force each
unattributable-source branch, including the per-stat layer bound via a
synthetic 17-item accessory stack.

All fixtures run inside the synthetic-data scope (test-data-independence):
kit race/skill/buff/item rows, an invented combat-modifier rule table, an
invented equipment-effect table, and display metadata registered in-test —
the shipped catalogs never appear as literals or symbol references.
"""

from contextlib import ExitStack, contextmanager
from dataclasses import replace
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from world.skills.equipment import EquipmentSlot
from world.lore.items import EquipmentModifierKey
from world.rules import combat
from world.rules.buffs import _add_buff
from world.rules.combat_modifiers import adjusted_agility, evaluate_combat_modifiers
from world.rules.equipment import toggle_equipment
from world.rules.equipment_effects import (
    EquipmentEffectRule,
    equipment_modifier_layers,
)
from world.rules.rulebook.schema import Rule
from world.rules.status_display import (
    ConditionDisplay,
    MissingDisplayMetadataError,
    display_for,
)
from world.rules.status_query import (
    MAX_LAYERS_PER_STAT,
    CharacterEquipmentView,
    GaugeValue,
    StatBreakdownRow,
    StatLayer,
    StatusQueryError,
    _Assembly,
    _validated_row,
    build_character_read_model,
    build_stat_breakdown,
    build_status_read_model,
)
from world.skills.effects import StatMultiplyEffect
from world.skills.handler import ConferredSkillGrant
from world.skills.registry import SkillCategory, SkillKind, TargetSpec
from world.tests.synthetic_data import (
    SYNTH_BUFFS,
    make_item,
    make_skill,
    synthetic_registries,
)

# ---------------------------------------------------------------------------
# Synthetic fixtures. Registry rows are kit templates; the rule tables and
# display metadata have no registry target, so they are invented here and
# swapped in through the patch context below. Display labels are invented
# prose disjoint from the shipped token universe.
# ---------------------------------------------------------------------------

# Skill rows: an owned x1.2 enhancement, a 100x partner for display-sort,
# two rule-table passives (owned and conferred), and a same-trait duplicate
# for the fail-closed fold.
_BODY_PULSE = make_skill(
    "t_body_pulse",
    label="體魄躍動",
    kind=SkillKind.PASSIVE,
    effects=[f"stat_multiply:{trait}:1.2" for trait in ("atk_phys", "agility", "defense")],
    category=SkillCategory.ENHANCEMENT,
)
_HIGH_PULSE = make_skill(
    "t_high_pulse",
    label="巨力澎湃",
    kind=SkillKind.PASSIVE,
    effects=["stat_multiply:atk_phys:100"],
    category=SkillCategory.ENHANCEMENT,
)
_WARD_TRAINING = make_skill(
    "t_ward_training",
    label="守御鍛練",
    kind=SkillKind.PASSIVE,
    effects=["passive_buff:t_ward_stance"],
    category=SkillCategory.ENHANCEMENT,
)
_RAMPART_INSTINCT = make_skill(
    "t_rampart_instinct",
    label="垣壁本能",
    kind=SkillKind.PASSIVE,
    effects=["passive_buff:t_rampart_guard"],
    category=SkillCategory.ENHANCEMENT,
)
_DUP_PULSE = make_skill(
    "t_dup_pulse",
    label="重影",
    kind=SkillKind.PASSIVE,
    effects=["stat_multiply:atk_phys:1.5", "stat_multiply:atk_phys:2.0"],
    category=SkillCategory.ENHANCEMENT,
)
_TIE_PULSE = make_skill(
    "t_tie_pulse",
    label="測試強化",
    kind=SkillKind.PASSIVE,
    effects=["stat_multiply:atk_phys:2.5"],
    category=SkillCategory.ENHANCEMENT,
)

# Buff + combat-modifier rule table (replaces the shipped rulebook wholesale
# while the context is open; the rule shape mirrors combat_modifiers.yaml).
# Refresh-stacking template: an in-test grant needs no source key.
_THORN_FEVER = replace(SYNTH_BUFFS["t_moss_veil"], key="t_thorn_fever")
_FEVER_RULE_ID = "t_thorn_fever_agility_penalty"
_WARD_RULE_ID = "t_ward_training_atk_phys_bonus"
_RAMPART_RULE_ID = "t_rampart_instinct_defense_bonus"
_COMBAT_RULES = [
    Rule(_FEVER_RULE_ID, {"buff_active": _THORN_FEVER.key}, {"agility": "-10%"}),
    Rule(_WARD_RULE_ID, {"skill_owned": _WARD_TRAINING.key}, {"atk_phys": 5}),
    Rule(_RAMPART_RULE_ID, {"skill_owned": _RAMPART_INSTINCT.key}, {"defense": 5}),
]
_DISPLAY_ROWS = {
    row.code: row
    for row in (
        ConditionDisplay(_THORN_FEVER.key, "荊棘熱", "harmful"),
        ConditionDisplay(_FEVER_RULE_ID, "荊棘熱靈巧 penalty", "harmful"),
        ConditionDisplay(_WARD_RULE_ID, "守御鍛練攻擊提升", "beneficial"),
        ConditionDisplay(_RAMPART_RULE_ID, "垣壁本能防禦提升", "beneficial"),
    )
}

# Gear rows. The closed shipped modifier enum cannot gain members, so the
# kit items borrow members positionally at runtime (never named as literals
# or attributes); the invented effect table below is the only source their
# rows resolve through while the context is open. Index 0 is the kit item's
# own borrowed member, so gear rows take the next five.
_BORROWED_KEYS = tuple(EquipmentModifierKey)[1:6]
_BULWARK_KEY, _HUSK_KEY, _GLINT_KEY, _BEADS_KEY, _FANG_KEY = _BORROWED_KEYS
_BULWARK_SHIELD = make_item(
    "t_bulwark_shell",
    display_name_zh="合成城殼鎧",
    equipment_slot=EquipmentSlot.ARMOR,
    modifier_key=_BULWARK_KEY,
)
_HUSK_VEST = make_item(
    "t_husk_vest",
    display_name_zh="合成殼甲衣",
    equipment_slot=EquipmentSlot.ARMOR,
    modifier_key=_HUSK_KEY,
)
_GLINT_FOCUS = make_item(
    "t_glint_focus",
    display_name_zh="合成微光飾符",
    equipment_slot=EquipmentSlot.ACCESSORY,
    modifier_key=_GLINT_KEY,
)
_BEAD_WARD = make_item(
    "t_warbeads_ward",
    display_name_zh="合成戰珠護符",
    equipment_slot=EquipmentSlot.ACCESSORY,
    modifier_key=_BEADS_KEY,
)
_FANG_BLADE = make_item(
    "t_fang_blade",
    display_name_zh="合成毒牙短刃",
    equipment_slot=EquipmentSlot.WEAPON_MAIN,
    modifier_key=_FANG_KEY,
)
_BULWARK_RULE = EquipmentEffectRule(
    adjustments={"atk_phys": -2, "agility": "-10%", "magic_power": 3},
    gauge_caps={"hp": 15},
    immune=(),
    attached_buffs=(),
    exposure_bias=0,
)
_HUSK_RULE = EquipmentEffectRule(
    adjustments={"defense": 8}, gauge_caps={}, immune=(), attached_buffs=(), exposure_bias=0
)
_GLINT_RULE = EquipmentEffectRule(
    # Flat agility rides the authored ``agility`` int field (the bundle
    # accessor relays it to ``agility_flat``).
    adjustments={"agility": 2}, gauge_caps={}, immune=(), attached_buffs=(), exposure_bias=0
)
_BEADS_RULE = EquipmentEffectRule(
    adjustments={"atk_phys": 1, "defense": 1},
    gauge_caps={},
    immune=(),
    attached_buffs=(),
    exposure_bias=0,
)
_FANG_RULE = EquipmentEffectRule(
    adjustments={"atk_phys": 4}, gauge_caps={}, immune=(), attached_buffs=(), exposure_bias=0
)
_EQUIPMENT_RULES = {
    _BULWARK_KEY: _BULWARK_RULE,
    _HUSK_KEY: _HUSK_RULE,
    _GLINT_KEY: _GLINT_RULE,
    _BEADS_KEY: _BEADS_RULE,
    _FANG_KEY: _FANG_RULE,
}


@contextmanager
def _synthetic_tables():
    """Swap the non-registry tables (rules, gear effects, display) synthetically."""
    with ExitStack() as stack:
        stack.enter_context(
            patch("world.rules.combat_modifiers._RULES", new=list(_COMBAT_RULES))
        )
        stack.enter_context(
            patch(
                "world.rules.equipment_effects.EQUIPMENT_EFFECT_RULES",
                new=dict(_EQUIPMENT_RULES),
            )
        )
        stack.enter_context(
            patch.dict("world.rules.status_display.STATUS_DISPLAY", _DISPLAY_ROWS)
        )
        yield


def _open_scope(case):
    """One kit scope covering the whole test, plus the synthetic table swaps."""
    scope = synthetic_registries(
        "races",
        "skills",
        "items",
        "buffs",
        extra={
            "skills": {
                _BODY_PULSE.key: _BODY_PULSE,
                _HIGH_PULSE.key: _HIGH_PULSE,
                _WARD_TRAINING.key: _WARD_TRAINING,
                _RAMPART_INSTINCT.key: _RAMPART_INSTINCT,
                _DUP_PULSE.key: _DUP_PULSE,
                _TIE_PULSE.key: _TIE_PULSE,
            },
            "items": {
                _BULWARK_SHIELD.key: _BULWARK_SHIELD,
                _HUSK_VEST.key: _HUSK_VEST,
                _GLINT_FOCUS.key: _GLINT_FOCUS,
                _BEAD_WARD.key: _BEAD_WARD,
                _FANG_BLADE.key: _FANG_BLADE,
            },
            "buffs": {_THORN_FEVER.key: _THORN_FEVER},
        },
    )
    stack = ExitStack()
    stack.enter_context(scope)
    stack.enter_context(_synthetic_tables())
    case.addCleanup(stack.close)


def _player(key: str):
    player = create_object(PlayerCharacter, key=key)
    player.race = "t_duskmari"
    player.apply_race_baseline()
    player.traits.hp.rate = 0
    player.db.equipment = None
    player.db.inventory = []
    return player


def _traits_data(entity) -> dict:
    return dict(entity.attributes.get("traits", default=None, category="traits"))


def _stored_trait(entity, key: str) -> int:
    raw = _traits_data(entity)[key]
    return raw.get("current", raw.get("base"))


def _wear(entity, *item_keys: str):
    entity.db.inventory = list(item_keys)
    for item_key in item_keys:
        result = toggle_equipment(entity, item_key)
        assert result.outcome == "success", (item_key, result.reason)
    return entity


def _rows(entity) -> dict[str, StatBreakdownRow]:
    return {row.key: row for row in build_stat_breakdown(entity)}


def _synthetic_assembly(entity, *, matches=(), equipment=()) -> _Assembly:
    """An assembly with forced storage views for fail-closed fixtures."""
    traits_data = _traits_data(entity)
    gauges = {}
    gauge_records = {}
    for key in ("hp", "mp", "sp"):
        raw = traits_data[key]
        base = raw.get("base", 0)
        mod = raw.get("mod", 0)
        gauge_records[key] = (mod, raw.get("mult", 1))
        gauges[key] = GaugeValue(
            current=raw.get("current", base + mod), maximum=base + mod
        )
    trait_values = {
        key: (traits_data[key].get("current", traits_data[key].get("base")))
        for key in ("atk_phys", "agility", "defense", "magic_power", "guild_merit")
    }
    return _Assembly(
        entity=entity,
        traits_data=traits_data,
        gauges=gauges,
        gauge_records=gauge_records,
        trait_values=trait_values,
        buff_entries=(),
        matches=tuple(matches),
        equipment=tuple(equipment),
        combat=None,
    )


class BreakdownShapeTests(EvenniaTestCase):
    """Closed vocabulary, row order, empty-source rows, current semantics."""

    def setUp(self):
        _open_scope(self)

    @covers_requirement("character-breakdown-view::breakdown-read-model-decomposes-each-panel-stat-by-source")
    def test_rows_have_closed_order_and_empty_layers(self):
        player = _player("breakdown shape")
        rows = build_stat_breakdown(player)
        self.assertEqual(
            [row.key for row in rows],
            ["hp", "mp", "sp", "atk_phys", "agility", "defense", "magic_power", "guild_merit"],
        )
        for row in rows:
            self.assertEqual(row.layers, ())
        traits = _traits_data(player)
        for key in ("atk_phys", "agility", "defense", "magic_power", "guild_merit"):
            row = next(r for r in rows if r.key == key)
            base = traits[key].get("current", traits[key].get("base"))
            self.assertEqual(row.base, traits[key]["base"])
            self.assertEqual(row.effective, base)
            self.assertEqual(row.current, base)

    @covers_requirement("character-breakdown-view::breakdown-read-model-decomposes-each-panel-stat-by-source")
    def test_gauge_rows_split_current_from_effective_maximum(self):
        player = _player("breakdown gauges")
        player.traits.hp.current = 40
        row = _rows(player)["hp"]
        self.assertEqual(row.current, 40)
        self.assertEqual(row.effective, _traits_data(player)["hp"]["base"])
        model = build_status_read_model(player)
        self.assertEqual(row.effective, model.resources["hp"].maximum)

    @covers_requirement("character-breakdown-view::breakdown-read-model-decomposes-each-panel-stat-by-source")
    def test_character_read_model_projects_the_breakdown(self):
        player = _player("breakdown model")
        _wear(player, _BULWARK_SHIELD.key)
        first = build_character_read_model(player)
        second = build_character_read_model(player)
        self.assertEqual(
            [row.key for row in first.breakdown],
            ["hp", "mp", "sp", "atk_phys", "agility", "defense", "magic_power", "guild_merit"],
        )
        self.assertEqual(first.breakdown, second.breakdown)
        hp = next(row for row in first.breakdown if row.key == "hp")
        cap = _BULWARK_RULE.gauge_caps["hp"]
        self.assertEqual(hp.effective, _stored_trait(player, "hp") + cap)
        self.assertEqual(
            hp.layers,
            (
                StatLayer(
                    "equipment", _BULWARK_SHIELD.display_name_zh, "flat", cap
                ),
            ),
        )

    @covers_requirement("character-breakdown-view::breakdown-read-model-decomposes-each-panel-stat-by-source")
    def test_layer_alphabets_are_closed(self):
        player = _player("breakdown alphabet")
        _add_buff(player, _THORN_FEVER.key)
        _wear(player, _BULWARK_SHIELD.key, _FANG_BLADE.key)
        player.db.skills = {"active": [_BODY_PULSE.key], "passive": []}
        for row in build_stat_breakdown(player):
            for layer in row.layers:
                self.assertIn(layer.source, ("skill", "condition", "equipment"))
                self.assertIn(layer.kind, ("mult", "flat", "pct"))
                self.assertNotEqual(layer.amount, 0)


class SkillFoldParityTests(EvenniaTestCase):
    """Tasks 1.1/1.3: the shipped effective_value fold, replayed as layers."""

    def setUp(self):
        _open_scope(self)

    @covers_requirement("character-breakdown-view::each-displayed-stat-matches-its-named-authoritative-computation")
    def test_bankers_rounding_replays_the_shipped_round(self):
        player = _player("breakdown tie")
        # 45 x 2.5 = 112.5 is an exact banker's-rounding tie: the replay must
        # land on the shipped fold's half-even neighbour (112), never away.
        player.traits.atk_phys.base = 45
        player.db.skills = {"active": [_TIE_PULSE.key], "passive": []}
        row = _rows(player)["atk_phys"]
        self.assertEqual(row.effective, player.skills.effective_value("atk_phys"))
        self.assertEqual(row.base, 45)
        self.assertEqual(row.effective, 112)
        self.assertEqual(row.current, 112)

    @covers_requirement("character-breakdown-view::each-displayed-stat-matches-its-named-authoritative-computation")
    def test_skill_grant_fold_carries_scaled_layer(self):
        player = _player("breakdown grant fold")
        player.db.skills = {"active": [_BODY_PULSE.key], "passive": []}
        player.db.skill_grants = [
            ConferredSkillGrant(source_key="t_patron", skill_key=_BODY_PULSE.key, scale=0.5)
        ]
        base = _stored_trait(player, "defense")
        row = _rows(player)["defense"]
        # Shipped fold: 1.2 (owned) x (1.2 x 0.5) (grant) = 0.72, single round.
        self.assertEqual(row.effective, round(base * (1.2 * 0.6)))
        self.assertEqual(row.effective, player.skills.effective_value("defense"))
        self.assertEqual(
            [layer.kind for layer in row.layers], ["mult", "mult"]
        )
        self.assertEqual(row.layers[0].amount, 1.2)
        self.assertEqual(row.layers[1].amount, 0.6)
        self.assertIn("0.5", row.layers[1].name)

    @covers_requirement("character-breakdown-view::breakdown-read-model-decomposes-each-panel-stat-by-source")
    def test_skill_permutation_invariance_and_display_sort(self):
        player_a = _player("breakdown perm a")
        player_b = _player("breakdown perm b")
        player_a.db.skills = {
            "active": [_BODY_PULSE.key, _HIGH_PULSE.key],
            "passive": [],
        }
        player_b.db.skills = {
            "active": [_HIGH_PULSE.key, _BODY_PULSE.key],
            "passive": [],
        }
        rows_a = _rows(player_a)["atk_phys"]
        rows_b = _rows(player_b)["atk_phys"]
        self.assertEqual(rows_a.effective, rows_b.effective)
        self.assertEqual(rows_a.layers, rows_b.layers)
        # Display order is (skill_key, source_key): the x1.2 row sorts first.
        self.assertEqual([layer.amount for layer in rows_a.layers], [1.2, 100.0])

    @covers_requirement("character-breakdown-view::breakdown-read-model-decomposes-each-panel-stat-by-source")
    def test_duplicate_multiplier_fails_closed(self):
        player = _player("breakdown dup")
        player.db.skills = {"active": [_DUP_PULSE.key], "passive": []}
        with self.assertRaises(StatusQueryError):
            build_stat_breakdown(player)


class ConditionLayerTests(EvenniaTestCase):
    """Task 1.2: per-rule condition layers, buff classification, parity."""

    def setUp(self):
        _open_scope(self)

    @covers_requirement("character-breakdown-view::breakdown-read-model-decomposes-each-panel-stat-by-source")
    def test_poison_agility_layer_is_named_and_signed(self):
        player = _player("breakdown poison")
        player.traits.agility.base = 100
        _add_buff(player, _THORN_FEVER.key)
        base = _stored_trait(player, "agility")
        row = _rows(player)["agility"]
        self.assertEqual(
            row.layers,
            (StatLayer("condition", display_for(_FEVER_RULE_ID).label, "pct", -10),),
        )
        self.assertEqual(row.effective, base * 0.9)
        self.assertEqual(row.effective, adjusted_agility(player))

    @covers_requirement("character-breakdown-view::each-displayed-stat-matches-its-named-authoritative-computation")
    def test_fractional_agility_current_equals_effective(self):
        # A percent-scaled static agility stays fractional: the shipped
        # adjusted_agility returns a float and the v5 wire rejects any static
        # row whose total-display current diverges from effective (rounding
        # it here made the whole character panel unavailable).
        player = _player("breakdown fraction")
        player.traits.agility.base = 1
        _add_buff(player, _THORN_FEVER.key)
        row = _rows(player)["agility"]
        self.assertEqual(row.effective, 0.9)
        self.assertEqual(row.current, 0.9)
        self.assertEqual(row.current, row.effective)
        self.assertEqual(row.current, adjusted_agility(player))

    @covers_requirement("character-breakdown-view::each-displayed-stat-matches-its-named-authoritative-computation")
    def test_skill_owned_rule_flows_through_the_facade(self):
        player = _player("breakdown skill owned")
        player.db.skills = {"active": [_WARD_TRAINING.key], "passive": []}
        base = _stored_trait(player, "atk_phys")
        row = _rows(player)["atk_phys"]
        self.assertEqual(
            row.layers,
            (
                StatLayer(
                    "condition",
                    display_for(_WARD_RULE_ID).label,
                    "flat",
                    5,
                ),
            ),
        )
        self.assertEqual(row.effective, float(base) + 5)
        # Purity (task 1.3): the read never mounts the skills handler.
        self.assertNotIn("skills", vars(player))

    @covers_requirement("character-breakdown-view::breakdown-read-model-decomposes-each-panel-stat-by-source")
    def test_conferred_rule_scale_produces_fractional_layer(self):
        player = _player("breakdown conferred rule")
        player.db.skill_grants = [
            ConferredSkillGrant(source_key="t_patron", skill_key=_RAMPART_INSTINCT.key, scale=0.5)
        ]
        base = _stored_trait(player, "defense")
        row = _rows(player)["defense"]
        self.assertEqual(
            row.layers,
            (
                StatLayer(
                    "condition",
                    display_for(_RAMPART_RULE_ID).label,
                    "flat",
                    2.5,
                ),
            ),
        )
        self.assertEqual(row.effective, float(base) + 2.5)

    @covers_requirement("character-breakdown-view::breakdown-read-model-decomposes-each-panel-stat-by-source")
    def test_buff_rule_sorts_before_plain_rule(self):
        player = _player("breakdown buff order")
        _add_buff(player, _THORN_FEVER.key)
        player.db.skills = {"active": [_WARD_TRAINING.key], "passive": []}
        rows = _rows(player)
        # The fever row exists and carries the buff-classified condition
        # layer; the ward row is the plain-rule counterpart.
        fever = rows["agility"].layers[0]
        self.assertEqual(fever.source, "condition")
        ward = rows["atk_phys"].layers[0]
        self.assertEqual(ward.source, "condition")
        self.assertEqual(ward.kind, "flat")

    @covers_requirement("character-breakdown-view::breakdown-read-model-decomposes-each-panel-stat-by-source")
    def test_unresolvable_label_fails_closed(self):
        player = _player("breakdown no label")
        assembly = _synthetic_assembly(
            player, matches=[(_FEVER_RULE_ID, {"agility": "-10%"})]
        )
        real = display_for

        def fake(code: str):
            if code == _FEVER_RULE_ID:
                raise MissingDisplayMetadataError(code)
            return real(code)

        with patch("world.rules.status_query.display_for", side_effect=fake):
            with self.assertRaises(StatusQueryError):
                build_stat_breakdown(player, assembly)

    @covers_requirement("character-breakdown-view::each-displayed-stat-matches-its-named-authoritative-computation")
    def test_panel_agility_matches_live_consumers(self):
        player = _player("breakdown live parity")
        _add_buff(player, _THORN_FEVER.key)
        _wear(player, _BULWARK_SHIELD.key, _GLINT_FOCUS.key)
        player.db.skills = {"active": [_BODY_PULSE.key], "passive": []}
        bundle = evaluate_combat_modifiers(player)
        self.assertEqual(bundle["agility"], "-20%")  # fever -10 merged with gear -10
        self.assertEqual(bundle["agility_flat"], 2)
        row = _rows(player)["agility"]
        self.assertEqual(row.effective, adjusted_agility(player))
        self.assertEqual(
            [
                (layer.source, layer.kind, layer.amount)
                for layer in row.layers
            ],
            [
                ("skill", "mult", 1.2),
                ("condition", "pct", -10),
                # Slot order: the armor's percent layer precedes the
                # accessory's flat layer.
                ("equipment", "pct", -10),
                ("equipment", "flat", 2),
            ],
        )


class EquipmentLayerTests(EvenniaTestCase):
    """Task 1.4: per-item gear layers, slot order, gauge decomposition."""

    def setUp(self):
        _open_scope(self)

    @covers_requirement("character-breakdown-view::each-displayed-stat-matches-its-named-authoritative-computation")
    def test_flat_stat_parity_with_combat_consumers(self):
        player = _player("breakdown flat parity")
        _wear(player, _BULWARK_SHIELD.key, _FANG_BLADE.key)
        player.db.skills = {"active": [_WARD_TRAINING.key], "passive": []}
        rows = _rows(player)
        self.assertEqual(rows["atk_phys"].effective, combat._adjusted_attack(player, "atk_phys"))
        self.assertEqual(rows["defense"].effective, combat._adjusted_defense(player))
        self.assertEqual(
            rows["magic_power"].effective, combat._adjusted_attack(player, "magic_power")
        )

    @covers_requirement("character-breakdown-view::breakdown-read-model-decomposes-each-panel-stat-by-source")
    def test_gear_layers_follow_slot_order(self):
        player = _player("breakdown slot order")
        _wear(player, _BULWARK_SHIELD.key, _FANG_BLADE.key)
        row = _rows(player)["atk_phys"]
        plate = next(layer for layer in row.layers if layer.amount == -2)
        blade = next(layer for layer in row.layers if layer.amount == 4)
        self.assertLess(row.layers.index(blade), row.layers.index(plate))

    @covers_requirement("character-breakdown-view::each-displayed-stat-matches-its-named-authoritative-computation")
    def test_gauge_mod_is_explained_by_worn_caps(self):
        player = _player("breakdown gauge gear")
        _wear(player, _BULWARK_SHIELD.key)  # gauge_caps hp +15
        row = _rows(player)["hp"]
        base = _stored_trait(player, "hp")
        self.assertEqual(row.base, base)
        self.assertEqual(row.effective, base + _BULWARK_RULE.gauge_caps["hp"])
        self.assertEqual(row.layers[0].source, "equipment")
        # The heal-clamp ceiling agrees with the composed maximum.
        self.assertEqual(float(row.effective), combat._max_hp(player))

    @covers_requirement("character-breakdown-view::each-displayed-stat-matches-its-named-authoritative-computation")
    def test_malformed_equipment_contributes_no_layers_and_no_effective(self):
        # Parity pin: the shipped combat fold reads malformed equipment as
        # "nothing worn" (``normalized_equipment`` → None), so the panel
        # must take the identical zero — never layers the bundle lacks.
        player = _player("breakdown unknown gear")
        player.db.equipment = {
            "weapon_main": "t_not_a_real_item",
            "weapon_off": None,
            "armor": None,
            "accessories": [],
        }
        rows = _rows(player)
        self.assertEqual(rows["defense"].layers, ())
        self.assertEqual(rows["defense"].effective, _stored_trait(player, "defense"))
        self.assertEqual(rows["hp"].layers, ())
        self.assertEqual(rows["hp"].effective, _stored_trait(player, "hp"))


class FailClosedTests(EvenniaTestCase):
    """Unattributable storage, bounds, and malformed bundles fail the read."""

    def setUp(self):
        _open_scope(self)

    @covers_requirement("character-breakdown-view::breakdown-read-model-decomposes-each-panel-stat-by-source")
    def test_static_nonzero_mod_fails_closed(self):
        player = _player("breakdown drift mod")
        traits = _traits_data(player)
        traits["atk_phys"] = {"base": 50, "mod": 3, "mult": 1}
        player.attributes.add("traits", traits, category="traits")
        with self.assertRaises(StatusQueryError):
            build_stat_breakdown(player)

    @covers_requirement("character-breakdown-view::breakdown-read-model-decomposes-each-panel-stat-by-source")
    def test_gauge_multiplier_fails_closed(self):
        player = _player("breakdown gauge mult")
        traits = _traits_data(player)
        traits["hp"] = {"base": 100, "mod": 0, "mult": 1.5, "current": 150}
        player.attributes.add("traits", traits, category="traits")
        with self.assertRaises(StatusQueryError):
            build_stat_breakdown(player)

    @covers_requirement("character-breakdown-view::breakdown-read-model-decomposes-each-panel-stat-by-source")
    def test_gauge_mod_mismatch_fails_closed(self):
        player = _player("breakdown gauge mismatch")
        traits = _traits_data(player)
        traits["hp"] = {"base": 100, "mod": 7, "mult": 1, "current": 107}
        player.attributes.add("traits", traits, category="traits")
        with self.assertRaises(StatusQueryError):
            build_stat_breakdown(player)

    @covers_requirement("character-breakdown-view::breakdown-read-model-decomposes-each-panel-stat-by-source")
    def test_unvalidated_equipment_stack_yields_no_layers(self):
        # The shipped normalization caps accessory stacks, so a >16-layer
        # stat is unreachable through validated storage: the bound is
        # enforced by the wire validators (documented deviation). Malformed
        # gear reads as "nothing worn" — the same zero the combat bundle
        # takes — instead of failing the whole panel.
        player = _player("breakdown bound")
        assembly = _synthetic_assembly(
            player,
            equipment=[
                CharacterEquipmentView("accessory", _BEAD_WARD.key)
                for _ in range(MAX_LAYERS_PER_STAT + 1)
            ],
        )
        rows = build_stat_breakdown(player, assembly)
        for row in rows:
            self.assertEqual(row.layers, ())

    @covers_requirement("character-breakdown-view::breakdown-read-model-decomposes-each-panel-stat-by-source")
    def test_layer_bound_rejects_instead_of_truncating(self):
        # The builder-side bound itself: a 17-layer row fails the read
        # closed through _validated_row, never a silent truncation.
        row = StatBreakdownRow(
            "defense",
            4,
            4,
            4,
            tuple(
                StatLayer("equipment", f"測試戒指 {index}", "flat", 1)
                for index in range(MAX_LAYERS_PER_STAT + 1)
            ),
        )
        with self.assertRaises(StatusQueryError):
            _validated_row(row)

    @covers_requirement("character-breakdown-view::breakdown-read-model-decomposes-each-panel-stat-by-source")
    def test_malformed_agility_bundle_fails_closed(self):
        player = _player("breakdown bad percent")
        assembly = _synthetic_assembly(player, matches=[("t_bad_rule", {"agility": -10})])
        with self.assertRaises(StatusQueryError):
            build_stat_breakdown(player, assembly)

    @covers_requirement("character-breakdown-view::each-displayed-stat-matches-its-named-authoritative-computation")
    def test_agility_floors_at_zero(self):
        player = _player("breakdown floor")
        assembly = _synthetic_assembly(
            player, matches=[(_FEVER_RULE_ID, {"agility": "-120%"})]
        )
        row = next(row for row in build_stat_breakdown(player, assembly) if row.key == "agility")
        self.assertEqual(row.effective, 0.0)
        self.assertEqual(row.current, 0.0)
        self.assertEqual(row.layers[0].kind, "pct")
        self.assertEqual(row.layers[0].amount, -120.0)


class EquipmentEffectTableTests(EvenniaTestCase):
    """The synthetic gear rows decompose through the loaded table accessor."""

    def test_accessor_decomposes_invented_rules(self):
        with _synthetic_tables():
            self.assertEqual(
                equipment_modifier_layers(_GLINT_KEY), {"agility": ("flat", 2)}
            )
            layers = equipment_modifier_layers(_BULWARK_KEY)
            self.assertEqual(
                {key: layers[key] for key in ("atk_phys", "agility", "hp")},
                {
                    "atk_phys": ("flat", -2),
                    "agility": ("pct", -10),
                    "hp": ("flat", 15),
                },
            )

    @covers_requirement("character-breakdown-view::breakdown-read-model-decomposes-each-panel-stat-by-source")
    def test_unbound_modifier_key_resolves_none(self):
        # A closed-enum member with no row in the (invented) table stays the
        # sanctioned "no rulebook entry" answer, never a KeyError.
        unbound = next(
            member
            for member in EquipmentModifierKey
            if member not in _EQUIPMENT_RULES
        )
        with _synthetic_tables():
            self.assertIsNone(equipment_modifier_layers(unbound))


class PurityTests(EvenniaTestCase):
    """Task 1.3: the reads never materialize entity.skills."""

    def setUp(self):
        _open_scope(self)

    @staticmethod
    def _attribute_snapshot(entity) -> dict:
        """Byte-comparable snapshot of every attribute the reads may touch."""
        return {
            "buffs": dict(entity.attributes.get("buffs") or {}),
            "sexual_traits": dict(
                entity.attributes.get("sexual_traits", category="traits") or {}
            ),
            "traits": dict(entity.attributes.get("traits", category="traits") or {}),
            "active_combat": entity.db.active_combat,
            "disguised_stats": entity.db.disguised_stats,
            "equipment": entity.db.equipment,
            "inventory": entity.db.inventory,
            "skills": entity.db.skills,
            "skill_grants": entity.db.skill_grants,
        }

    @covers_requirement("character-breakdown-view::breakdown-read-model-decomposes-each-panel-stat-by-source")
    def test_builds_never_materialize_skills(self):
        player = _player("breakdown purity")
        player.db.skills = {
            "active": [_WARD_TRAINING.key, _RAMPART_INSTINCT.key],
            "passive": [],
        }
        _wear(player, _BULWARK_SHIELD.key)
        before = self._attribute_snapshot(player)
        before_vars = sorted(vars(player).keys())
        self.assertIsNone(player.attributes.get("sexual_traits", category="traits"))
        build_status_read_model(player)
        model = build_character_read_model(player)
        self.assertEqual(len(model.breakdown), 8)
        self.assertNotIn("skills", vars(player))
        self.assertNotIn("sexual", vars(player))
        self.assertEqual(before, self._attribute_snapshot(player))
        self.assertEqual(before_vars, sorted(vars(player).keys()))
        self.assertIsNone(
            player.attributes.get("sexual_traits", category="traits"),
            "the breakdown reads must not materialize the sexual handler",
        )
