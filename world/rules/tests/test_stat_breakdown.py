"""Stat-breakdown read model tests (expose-stat-breakdown-read-model tasks 1.1–1.4).

Every composition test pins the builder to the shipped authoritative
operations: the ``SkillHandler.effective_value`` fold (banker's rounding,
single final ``round``), ``combat._adjusted_attack``/``_adjusted_defense``
flat sums, ``combat_modifiers.adjusted_agility`` (percent-then-flat, floored
at zero), and the gauge-ceiling reader. Fail-closed fixtures force each
unattributable-source branch, including the per-stat layer bound via a
synthetic 17-item accessory stack.
"""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.lore.items import ITEM_REGISTRY
from world.rules import combat
from world.rules.buffs import _add_buff
from world.rules.combat_modifiers import adjusted_agility, evaluate_combat_modifiers
from world.rules.equipment import toggle_equipment
from world.rules.status_query import (
    MAX_LAYERS_PER_STAT,
    GaugeValue,
    StatBreakdownRow,
    StatLayer,
    StatusQueryError,
    _Assembly,
    build_character_read_model,
    build_stat_breakdown,
    build_status_read_model,
    display_for,
)
from world.rules.status_display import MissingDisplayMetadataError
from world.skills.effects import StatMultiplyEffect
from world.skills.handler import ConferredSkillGrant


def _player(key: str):
    player = create_object(PlayerCharacter, key=key)
    player.race = "human"
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
    gauges = {key: GaugeValue(current=100, maximum=100) for key in ("hp", "mp", "sp")}
    trait_values = {
        key: (traits_data[key].get("current", traits_data[key].get("base")))
        for key in ("atk_phys", "agility", "defense", "magic_power", "guild_merit")
    }
    return _Assembly(
        entity=entity,
        traits_data=traits_data,
        gauges=gauges,
        gauge_records={key: (0, 1) for key in ("hp", "mp", "sp")},
        trait_values=trait_values,
        buff_entries=(),
        matches=tuple(matches),
        equipment=tuple(equipment),
        combat=None,
    )


class BreakdownShapeTests(EvenniaTestCase):
    """Closed vocabulary, row order, empty-source rows, current semantics."""

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
        self.assertEqual(row.effective, 100)
        model = build_status_read_model(player)
        self.assertEqual(row.effective, model.resources["hp"].maximum)

    @covers_requirement("character-breakdown-view::breakdown-read-model-decomposes-each-panel-stat-by-source")
    def test_character_read_model_projects_the_breakdown(self):
        player = _player("breakdown model")
        _wear(player, "knight_platemail")
        first = build_character_read_model(player)
        second = build_character_read_model(player)
        self.assertEqual(
            [row.key for row in first.breakdown],
            ["hp", "mp", "sp", "atk_phys", "agility", "defense", "magic_power", "guild_merit"],
        )
        self.assertEqual(first.breakdown, second.breakdown)
        hp = next(row for row in first.breakdown if row.key == "hp")
        self.assertEqual(hp.effective, 115)  # base 100 + worn plate cap 15
        self.assertEqual(
            hp.layers,
            (
                StatLayer(
                    "equipment", ITEM_REGISTRY["knight_platemail"].display_name_zh, "flat", 15
                ),
            ),
        )

    @covers_requirement("character-breakdown-view::breakdown-read-model-decomposes-each-panel-stat-by-source")
    def test_layer_alphabets_are_closed(self):
        player = _player("breakdown alphabet")
        _add_buff(player, "poisoned")
        _wear(player, "knight_platemail", "ashen_scimitar")
        player.db.skills = {"active": ["body_enhancement_basic"], "passive": []}
        for row in build_stat_breakdown(player):
            for layer in row.layers:
                self.assertIn(layer.source, ("skill", "condition", "equipment"))
                self.assertIn(layer.kind, ("mult", "flat", "pct"))
                self.assertNotEqual(layer.amount, 0)


class SkillFoldParityTests(EvenniaTestCase):
    """Tasks 1.1/1.3: the shipped effective_value fold, replayed as layers."""

    @covers_requirement("character-breakdown-view::each-displayed-stat-matches-its-named-authoritative-computation")
    def test_bankers_rounding_replays_the_shipped_round(self):
        player = _player("breakdown tie")
        # 45 x 2.5 = 112.5 is an exact banker's-rounding tie: the replay must
        # land on the shipped fold's half-even neighbour (112), never away.
        player.traits.atk_phys.base = 45
        player.db.skills = {"active": ["tie_skill"], "passive": []}
        skill = type(
            "Skill",
            (),
            {
                "key": "tie_skill",
                "label": "測試強化",
                "parsed_effects": [StatMultiplyEffect(trait="atk_phys", multiplier=2.5)],
            },
        )()
        with patch("world.rules.status_query.SKILL_REGISTRY", {"tie_skill": skill}), patch(
            "world.skills.handler.SKILL_REGISTRY", {"tie_skill": skill}
        ):
            row = _rows(player)["atk_phys"]
            self.assertEqual(row.effective, player.skills.effective_value("atk_phys"))
        self.assertEqual(row.base, 45)
        self.assertEqual(row.effective, 112)
        self.assertEqual(row.current, 112)

    @covers_requirement("character-breakdown-view::each-displayed-stat-matches-its-named-authoritative-computation")
    def test_skill_grant_fold_carries_scaled_layer(self):
        player = _player("breakdown grant fold")
        player.db.skills = {"active": ["body_enhancement_basic"], "passive": []}
        player.db.skill_grants = [
            ConferredSkillGrant(source_key="patron", skill_key="body_enhancement_basic", scale=0.5)
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
            "active": ["body_enhancement_basic", "body_enhancement"],
            "passive": [],
        }
        player_b.db.skills = {
            "active": ["body_enhancement", "body_enhancement_basic"],
            "passive": [],
        }
        rows_a = _rows(player_a)["atk_phys"]
        rows_b = _rows(player_b)["atk_phys"]
        self.assertEqual(rows_a.effective, rows_b.effective)
        self.assertEqual(rows_a.layers, rows_b.layers)
        self.assertEqual([layer.amount for layer in rows_a.layers], [100, 1.2])

    @covers_requirement("character-breakdown-view::breakdown-read-model-decomposes-each-panel-stat-by-source")
    def test_duplicate_multiplier_fails_closed(self):
        player = _player("breakdown dup")
        player.db.skills = {"active": ["dup_skill"], "passive": []}
        skill = type(
            "Skill",
            (),
            {
                "key": "dup_skill",
                "label": "重複",
                "parsed_effects": [
                    StatMultiplyEffect(trait="atk_phys", multiplier=1.5),
                    StatMultiplyEffect(trait="atk_phys", multiplier=2.0),
                ],
            },
        )()
        with patch("world.rules.status_query.SKILL_REGISTRY", {"dup_skill": skill}):
            with self.assertRaises(StatusQueryError):
                build_stat_breakdown(player)


class ConditionLayerTests(EvenniaTestCase):
    """Task 1.2: per-rule condition layers, buff classification, parity."""

    @covers_requirement("character-breakdown-view::breakdown-read-model-decomposes-each-panel-stat-by-source")
    def test_poison_agility_layer_is_named_and_signed(self):
        player = _player("breakdown poison")
        _add_buff(player, "poisoned")
        base = _stored_trait(player, "agility")
        row = _rows(player)["agility"]
        self.assertEqual(
            row.layers,
            (StatLayer("condition", display_for("poison_agility_penalty").label, "pct", -10),),
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
        _add_buff(player, "poisoned")
        row = _rows(player)["agility"]
        self.assertEqual(row.effective, 0.9)
        self.assertEqual(row.current, 0.9)
        self.assertEqual(row.current, row.effective)
        self.assertEqual(row.current, adjusted_agility(player))

    @covers_requirement("character-breakdown-view::each-displayed-stat-matches-its-named-authoritative-computation")
    def test_skill_owned_rule_flows_through_the_facade(self):
        player = _player("breakdown skill owned")
        player.db.skills = {"active": ["retainer_martial_training"], "passive": []}
        base = _stored_trait(player, "atk_phys")
        row = _rows(player)["atk_phys"]
        self.assertEqual(
            row.layers,
            (
                StatLayer(
                    "condition",
                    display_for("retainer_martial_training_atk_phys_bonus").label,
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
            ConferredSkillGrant(source_key="patron", skill_key="defense_instinct", scale=0.5)
        ]
        base = _stored_trait(player, "defense")
        row = _rows(player)["defense"]
        self.assertEqual(
            row.layers,
            (
                StatLayer(
                    "condition",
                    display_for("defense_instinct_defense_bonus").label,
                    "flat",
                    2.5,
                ),
            ),
        )
        self.assertEqual(row.effective, float(base) + 2.5)

    @covers_requirement("character-breakdown-view::breakdown-read-model-decomposes-each-panel-stat-by-source")
    def test_buff_rule_sorts_before_plain_rule(self):
        player = _player("breakdown buff order")
        _add_buff(player, "poisoned")
        player.db.skills = {"active": ["retainer_martial_training"], "passive": []}
        rows = _rows(player)
        # The poison row exists and carries the buff-classified condition
        # layer; the retainer row is the plain-rule counterpart.
        poison = rows["agility"].layers[0]
        self.assertEqual(poison.source, "condition")
        retainer = rows["atk_phys"].layers[0]
        self.assertEqual(retainer.source, "condition")
        self.assertEqual(retainer.kind, "flat")

    @covers_requirement("character-breakdown-view::breakdown-read-model-decomposes-each-panel-stat-by-source")
    def test_unresolvable_label_fails_closed(self):
        player = _player("breakdown no label")
        assembly = _synthetic_assembly(
            player, matches=[("poison_agility_penalty", {"agility": "-10%"})]
        )
        real = display_for

        def fake(code: str):
            if code == "poison_agility_penalty":
                raise MissingDisplayMetadataError(code)
            return real(code)

        with patch("world.rules.status_query.display_for", side_effect=fake):
            with self.assertRaises(StatusQueryError):
                build_stat_breakdown(player, assembly)

    @covers_requirement("character-breakdown-view::each-displayed-stat-matches-its-named-authoritative-computation")
    def test_panel_agility_matches_live_consumers(self):
        player = _player("breakdown live parity")
        _add_buff(player, "poisoned")
        _wear(player, "knight_platemail", "ashen_scimitar")
        player.db.skills = {"active": ["body_enhancement_basic"], "passive": []}
        bundle = evaluate_combat_modifiers(player)
        self.assertEqual(bundle["agility"], "-20%")  # poison -10 merged with gear -10
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
                ("equipment", "flat", 2),
                ("equipment", "pct", -10),
            ],
        )


class EquipmentLayerTests(EvenniaTestCase):
    """Task 1.4: per-item gear layers, slot order, gauge decomposition."""

    @covers_requirement("character-breakdown-view::each-displayed-stat-matches-its-named-authoritative-computation")
    def test_flat_stat_parity_with_combat_consumers(self):
        player = _player("breakdown flat parity")
        _wear(player, "knight_platemail", "ashen_scimitar")
        player.db.skills = {"active": ["retainer_martial_training"], "passive": []}
        rows = _rows(player)
        self.assertEqual(rows["atk_phys"].effective, combat._adjusted_attack(player, "atk_phys"))
        self.assertEqual(rows["defense"].effective, combat._adjusted_defense(player))
        self.assertEqual(
            rows["magic_power"].effective, combat._adjusted_attack(player, "magic_power")
        )

    @covers_requirement("character-breakdown-view::breakdown-read-model-decomposes-each-panel-stat-by-source")
    def test_gear_layers_follow_slot_order(self):
        player = _player("breakdown slot order")
        _wear(player, "knight_platemail", "ashen_scimitar")
        row = _rows(player)["atk_phys"]
        plate = next(layer for layer in row.layers if layer.amount == -2)
        scimitar = next(layer for layer in row.layers if layer.amount == 4)
        self.assertLess(row.layers.index(scimitar), row.layers.index(plate))

    @covers_requirement("character-breakdown-view::each-displayed-stat-matches-its-named-authoritative-computation")
    def test_gauge_mod_is_explained_by_worn_caps(self):
        player = _player("breakdown gauge gear")
        _wear(player, "knight_platemail")  # gauge_caps hp +15
        row = _rows(player)["hp"]
        self.assertEqual(row.base, 100)
        self.assertEqual(row.effective, 115)
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
            "weapon_main": "not_a_real_item",
            "weapon_off": None,
            "armor": None,
            "accessories": [],
        }
        rows = _rows(player)
        self.assertEqual(rows["defense"].layers, ())
        self.assertEqual(rows["defense"].effective, _stored_trait(player, "defense"))
        self.assertEqual(rows["hp"].layers, ())
        self.assertEqual(rows["hp"].effective, 100)


class FailClosedTests(EvenniaTestCase):
    """Unattributable storage, bounds, and malformed bundles fail the read."""

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
        from world.rules.status_query import CharacterEquipmentView

        player = _player("breakdown bound")
        assembly = _synthetic_assembly(
            player,
            equipment=[
                CharacterEquipmentView("accessory", "chainmail")
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
        from world.rules.status_query import _validated_row

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
        assembly = _synthetic_assembly(player, matches=[("bad_rule", {"agility": -10})])
        with self.assertRaises(StatusQueryError):
            build_stat_breakdown(player, assembly)

    @covers_requirement("character-breakdown-view::each-displayed-stat-matches-its-named-authoritative-computation")
    def test_agility_floors_at_zero(self):
        player = _player("breakdown floor")
        assembly = _synthetic_assembly(
            player, matches=[("poison_agility_penalty", {"agility": "-120%"})]
        )
        row = next(row for row in build_stat_breakdown(player, assembly) if row.key == "agility")
        self.assertEqual(row.effective, 0.0)
        self.assertEqual(row.current, 0.0)
        self.assertEqual(row.layers[0].kind, "pct")
        self.assertEqual(row.layers[0].amount, -120.0)


class PurityTests(EvenniaTestCase):
    """Task 1.3: the reads never materialize entity.skills."""

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
            "active": ["retainer_martial_training", "guardian_instinct"],
            "passive": [],
        }
        _wear(player, "knight_platemail")
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
