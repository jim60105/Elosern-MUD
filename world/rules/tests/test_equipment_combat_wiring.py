"""Worn-equipment combat wiring tests (P2).

Data-independent (migrate-rules-equipment-item-tests-off-real-data): every
folded number is COMPUTED from rulebook rows resolved at import by shape
probe (`first_matching_rule`) — the gear is synthetic kit items bound to
those rows, and a same-shape replacement row (renamed keys, different
values) keeps every assertion honest instead of pinning shipped data.
"""

from tools.spec_traceability import covers_requirement

import ast
import math
import unittest
from pathlib import Path
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.rooms import Room
from world.rules import combat
from world.rules.action import ActionRequest, ActionResolver
from world.rules.action_preview import preview_skill
from world.rules.combat import (
    Battlefield,
    BattlefieldActionContext,
    _heal_magnitude,
    _to_hit,
)
from world.rules.combat_modifiers import (
    adjusted_agility,
    evaluate_combat_modifiers,
    evaluate_combat_modifiers_no_create,
)
from world.rules.combat_session import engage, read_session, reconstruct_battlefield
from world.rules.disengage import _adjusted_agility as flee_agility
from world.rules.equipment import toggle_equipment
from world.rules.equipment_effects import (
    equipment_adjustments,
    equipment_gauge_caps,
)
from world.rules.items import (
    ITEM_EFFECT_RULES,
    ItemUseRequest,
    preflight_item_use,
)
from world.rules.overwhelm import _required_roll
from world.rules.sexual_resist import _blended_score
from world.lore.items import EquipmentSlot, ItemEffectKey, ItemUseMechanics
from world.rules.tests.combat_fixtures import (
    BattlefieldIsolation,
    FakeEntity,
    grant_lineage,
)
from world.quests.catalog import register_catalog
from world.skills.registry import TargetSpec
from world.tests.synthetic_data import SYNTH_SKILLS, make_item, make_skill

from ._combat_session_helpers import open_synthetic_scope
from ._equipment_rulebook_probes import first_matching_rule

_ROOT = Path(__file__).resolve().parents[3]

# The loader module is the only production surface allowed to reference the
# loaded rulebook data; its accessors are the capability surface, and every
# other consumer goes through the accessor functions.
_RULEBOOK_ALLOWLIST = frozenset({Path("world/rules/equipment_effects.py")})


def _percent(value):
    """Numeric percent-string value: "-8%" -> -0.08."""
    return int(str(value).rstrip("%")) / 100


# --- rulebook shape probes (fail-fast, computed-from-live-values) ----------
_ATK_KEY, _ATK_ROW = first_matching_rule(
    "flat-attack weapon",
    lambda r: set(r.adjustments) == {"atk_phys"}
    and isinstance(r.adjustments["atk_phys"], int)
    and r.adjustments["atk_phys"] > 0,
)
_ATK = _ATK_ROW.adjustments["atk_phys"]

_PLATE_KEY, _PLATE_ROW = first_matching_rule(
    "punishing heavy armor",
    lambda r: set(r.adjustments) == {"atk_phys", "defense", "agility"}
    and r.adjustments["atk_phys"] < 0
    and r.adjustments["defense"] > 0
    and isinstance(r.adjustments["agility"], str),
)
_PLATE_ATK = _PLATE_ROW.adjustments["atk_phys"]
_PLATE_DEF = _PLATE_ROW.adjustments["defense"]
_PLATE_AGILITY = _PLATE_ROW.adjustments["agility"]

_RING_KEY, _RING_ROW = first_matching_rule(
    "gauge-capping ring",
    lambda r: set(r.adjustments) == {"defense"}
    and r.adjustments["defense"] > 0
    and "hp" in r.gauge_caps,
)
_RING_DEF = _RING_ROW.adjustments["defense"]
_PLATE_CAP = _PLATE_ROW.gauge_caps["hp"]
_RING_CAP = _RING_ROW.gauge_caps["hp"]

_BLADE_KEY, _BLADE_ROW = first_matching_rule(
    "flat attack plus flat agility weapon",
    lambda r: set(r.adjustments) == {"atk_phys", "agility"}
    and isinstance(r.adjustments["atk_phys"], int)
    and r.adjustments["atk_phys"] > 0
    and isinstance(r.adjustments["agility"], int)
    and r.adjustments["agility"] > 0,
)
_BLADE_ATK = _BLADE_ROW.adjustments["atk_phys"]
_BLADE_AGILITY = _BLADE_ROW.adjustments["agility"]

_MAIL_KEY, _MAIL_ROW = first_matching_rule(
    "flat defense plus percent agility armor",
    lambda r: set(r.adjustments) == {"defense", "agility"}
    and r.adjustments["defense"] > 0
    and isinstance(r.adjustments["agility"], str),
)
_MAIL_ATK = _MAIL_ROW.adjustments.get("atk_phys", 0)
_MAIL_DEF = _MAIL_ROW.adjustments["defense"]
_MAIL_AGILITY = _MAIL_ROW.adjustments["agility"]

_ROBE_KEY, _ROBE_ROW = first_matching_rule(
    "mp-cost-cutting mage gear",
    lambda r: "mp_cost" in r.adjustments
    and isinstance(r.adjustments["mp_cost"], str)
    and _percent(r.adjustments["mp_cost"]) < 0,
)
_ROBE_MP_PCT = _percent(_ROBE_ROW.adjustments["mp_cost"])
_ROBE_MAGIC = _ROBE_ROW.adjustments.get("magic_power", 0)

_SEAL_KEY, _SEAL_ROW = first_matching_rule(
    "sp-cost-cutting seal",
    lambda r: "sp_cost" in r.adjustments
    and isinstance(r.adjustments["sp_cost"], str)
    and _percent(r.adjustments["sp_cost"]) < 0,
)
_SEAL_SP_PCT = _percent(_SEAL_ROW.adjustments["sp_cost"])

_ECHO_KEY, _ECHO_ROW = first_matching_rule(
    "flat agility penalty weapon",
    lambda r: set(r.adjustments) == {"atk_phys", "agility"}
    and r.adjustments["atk_phys"] > 0
    and isinstance(r.adjustments["agility"], int)
    and r.adjustments["agility"] <= -2,
)
_ECHO_ATK = _ECHO_ROW.adjustments["atk_phys"]
_ECHO_AGILITY_FLAT = _ECHO_ROW.adjustments["agility"]

_EMBLEM_KEY, _EMBLEM_ROW = first_matching_rule(
    "heal-gain emblem",
    lambda r: "heal_gain" in r.adjustments
    and _percent(r.adjustments["heal_gain"]) >= 0.2
    and 3 * (1 + _percent(r.adjustments["heal_gain"])) % 1 >= 0.5,
)
_HEAL_GAIN_PCT = _percent(_EMBLEM_ROW.adjustments["heal_gain"])

assert _PLATE_CAP != _RING_CAP, "the two cap rows must be distinct values"
assert _PLATE_AGILITY != _MAIL_AGILITY, "the two percent-agility rows must differ"

# --- synthetic cast rows (declared costs chosen by this test) --------------
_T_ELEMENT = SYNTH_SKILLS["t_ember_burst"].element.key

_MP_SKILL = make_skill(
    "t_arc_burst",
    effects=[f"damage:{_T_ELEMENT}:magic"],
    target_spec=TargetSpec.SINGLE,
    cost={"mp": 20},
)
_SP_SKILL = make_skill(
    "t_rune_cleave",
    effects=[f"damage:{_T_ELEMENT}:physical"],
    target_spec=TargetSpec.SINGLE,
    cost={"sp": 20},
)

# --- synthetic consumable bound to the shipped self-heal effect row --------
_TONIC = make_item(
    "t_wiring_tonic",
    display_name_zh="合成苔汁",
    use_mechanics=ItemUseMechanics(
        effect_key=ItemEffectKey.SELF_HEAL, consumable=True, combat_allowed=True
    ),
)
_HEAL_AMOUNT = ITEM_EFFECT_RULES[ItemEffectKey.SELF_HEAL].amount

# --- synthetic gear bound to the probed rows -------------------------------
_SABER = make_item(
    "t_fold_saber",
    display_name_zh="合成折刀",
    equipment_slot=EquipmentSlot.WEAPON_MAIN,
    modifier_key=_ATK_KEY,
)
_PLATE = make_item(
    "t_fold_plate",
    display_name_zh="合成折甲",
    equipment_slot=EquipmentSlot.ARMOR,
    modifier_key=_PLATE_KEY,
)
_RING = make_item(
    "t_fold_ring",
    display_name_zh="合成折戒",
    equipment_slot=EquipmentSlot.ACCESSORY,
    modifier_key=_RING_KEY,
)
_BLADE = make_item(
    "t_fold_blade",
    display_name_zh="合成影刃",
    equipment_slot=EquipmentSlot.WEAPON_MAIN,
    modifier_key=_BLADE_KEY,
)
_MAIL = make_item(
    "t_fold_mail",
    display_name_zh="合成鏈甲",
    equipment_slot=EquipmentSlot.ARMOR,
    modifier_key=_MAIL_KEY,
)
_ROBE = make_item(
    "t_fold_robe",
    display_name_zh="合成法袍",
    equipment_slot=EquipmentSlot.ARMOR,
    modifier_key=_ROBE_KEY,
)
_SEAL = make_item(
    "t_fold_seal",
    display_name_zh="合成印章戒",
    equipment_slot=EquipmentSlot.ACCESSORY,
    modifier_key=_SEAL_KEY,
)
_ECHO = make_item(
    "t_fold_echo",
    display_name_zh="合成回聲刃",
    equipment_slot=EquipmentSlot.WEAPON_OFF,
    modifier_key=_ECHO_KEY,
)
_EMBLEM = make_item(
    "t_fold_emblem",
    display_name_zh="合成聖徽",
    equipment_slot=EquipmentSlot.ACCESSORY,
    modifier_key=_EMBLEM_KEY,
)
_SCOPE_ITEMS = {d.key: d for d in (_SABER, _PLATE, _RING, _BLADE, _MAIL, _ROBE, _SEAL, _ECHO, _EMBLEM, _TONIC)}


def _worn(entity, *, weapon=None, off=None, armor=None, accessories=()) -> None:
    """Write raw equipment storage directly onto a fixture entity."""
    entity.db.equipment = {
        "weapon_main": weapon,
        "weapon_off": off,
        "armor": armor,
        "accessories": list(accessories),
    }


def _player(key: str):
    player = create_object(PlayerCharacter, key=key)
    player.race = "human"
    player.apply_race_baseline()
    player.traits.hp.rate = 0
    player.traits.magic_power.base = 30
    player.db.equipment = None
    player.db.inventory = []
    return player


def _monster(key: str, location):
    monster = create_object(Monster, key=key)
    monster.threat_tier = "low"
    monster.apply_monster_tier("floor")
    monster.traits.hp.base = 500
    monster.traits.hp.current = 500
    monster.location = location
    return monster


class _WearerCase(EvenniaTestCase):
    """Evennia-backed base with a wear helper and the synthetic scope."""

    def setUp(self):
        super().setUp()
        open_synthetic_scope(
            self,
            "skills",
            "elements",
            "items",
            extra={
                "items": _SCOPE_ITEMS,
                "skills": {_MP_SKILL.key: _MP_SKILL, _SP_SKILL.key: _SP_SKILL},
            },
        )

    def wear(self, entity, *item_keys: str):
        entity.db.inventory = list(item_keys)
        for item_key in item_keys:
            result = toggle_equipment(entity, item_key)
            assert result.outcome == "success", (item_key, result.reason)
        return entity


class AccessorFoldTests(_WearerCase):
    @covers_requirement(
        "equipment-effects::equipment-adjustments-reach-every-consumer-through-one-accessor"
    )
    def test_worn_items_stack_additively(self):
        entity = self.wear(
            _player("fold stacker"), _SABER.key, _PLATE.key, _RING.key
        )
        self.assertEqual(
            dict(equipment_adjustments(entity)),
            # Weapon flat attack plus the armor's negative attack; the two
            # defense flats sum; the armor percent keeps its signed shape.
            {
                "atk_phys": _ATK + _PLATE_ATK,
                "defense": _PLATE_DEF + _RING_DEF,
                "agility": _PLATE_AGILITY,
            },
        )
        self.assertEqual(
            dict(equipment_gauge_caps(entity)), {"hp": _PLATE_CAP + _RING_CAP}
        )

    def test_flat_and_percent_agility_split_across_keys(self):
        entity = self.wear(_player("fold splitter"), _BLADE.key, _MAIL.key)
        bundle = dict(equipment_adjustments(entity))
        self.assertEqual(bundle["atk_phys"], _BLADE_ATK + _MAIL_ATK)
        self.assertEqual(bundle["agility_flat"], _BLADE_AGILITY)
        self.assertEqual(bundle["agility"], _MAIL_AGILITY)

    def test_percent_fields_sum_and_rerender_as_signed_strings(self):
        entity = self.wear(_player("fold percent"), _ROBE.key, _SEAL.key)
        bundle = dict(equipment_adjustments(entity))
        self.assertEqual(bundle["mp_cost"], f"{int(_ROBE_MP_PCT * 100)}%")
        self.assertEqual(bundle["sp_cost"], f"{int(_SEAL_SP_PCT * 100)}%")
        self.assertEqual(bundle["magic_power"], _ROBE_MAGIC)

    def test_accessor_is_a_pure_read(self):
        entity = self.wear(_player("fold purity"), _SABER.key)

        def storage():
            return (
                repr(entity.db.equipment),
                repr(entity.db.inventory),
                repr(dict(entity.traits.trait_data)),
            )

        before = storage()
        dict(equipment_adjustments(entity))
        dict(equipment_gauge_caps(entity))
        evaluate_combat_modifiers_no_create(entity)
        self.assertEqual(storage(), before)

    @covers_requirement(
        "equipment-effects::equipment-adjustments-reach-every-consumer-through-one-accessor"
    )
    def test_malformed_storage_reads_as_empty_bundle(self):
        entity = _player("fold malformed")
        entity.db.equipment = "not-a-mapping"
        self.assertEqual(dict(equipment_adjustments(entity)), {})
        self.assertEqual(dict(equipment_gauge_caps(entity)), {})

    @covers_requirement(
        "combat-modifier-table::worn-equipment-merges-into-the-merged-bundle-of-both-evaluation-paths"
    )
    def test_both_evaluation_paths_merge_the_equipment_layer(self):
        entity = self.wear(_player("merge both paths"), _SABER.key)
        with patch(
            "world.rules.combat_modifiers.matched_combat_modifiers",
            return_value=(("rule", {"atk_phys": 2}),),
        ):
            self.assertEqual(
                evaluate_combat_modifiers(entity)["atk_phys"], 2 + _ATK
            )
            self.assertEqual(
                evaluate_combat_modifiers_no_create(entity)["atk_phys"], 2 + _ATK
            )

    @covers_requirement(
        "combat-modifier-table::worn-equipment-merges-into-the-merged-bundle-of-both-evaluation-paths"
    )
    def test_malformed_storage_keeps_the_rule_bundle_intact(self):
        entity = self.wear(_player("merge malformed"), _SABER.key)
        entity.db.equipment = "corrupted"
        with patch(
            "world.rules.combat_modifiers.matched_combat_modifiers",
            return_value=(("rule", {"atk_phys": 2}),),
        ):
            self.assertEqual(evaluate_combat_modifiers(entity), {"atk_phys": 2})
            self.assertEqual(
                evaluate_combat_modifiers_no_create(entity), {"atk_phys": 2}
            )


class SingleSourceStructureTests(unittest.TestCase):
    @covers_requirement(
        "equipment-effects::equipment-adjustments-reach-every-consumer-through-one-accessor"
    )
    def test_no_other_production_module_reads_the_rulebook_data(self):
        """Structural single-source guard (delta scenario).

        Production modules outside the loader itself must not reference the
        loaded rulebook symbol or its entry fields; consumers go through the
        accessor functions only.
        """
        offenders: list[str] = []
        for root in ("commands", "server", "typeclasses", "web", "world"):
            for path in (_ROOT / root).rglob("*.py"):
                relative = path.relative_to(_ROOT)
                if "tests" in relative.parts or relative in _RULEBOOK_ALLOWLIST:
                    continue
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if (
                        isinstance(node, ast.Attribute)
                        and node.attr
                        in {"EQUIPMENT_EFFECT_RULES", "adjustments", "gauge_caps"}
                    ) or (
                        isinstance(node, ast.Name)
                        and node.id == "EQUIPMENT_EFFECT_RULES"
                    ):
                        offenders.append(f"{relative}:{node.lineno}")
        self.assertEqual(offenders, [])



class CostParityTests(BattlefieldIsolation, _WearerCase):
    def _context(self, player, monster):
        engage(player, monster)
        return BattlefieldActionContext(
            reconstruct_battlefield(player, read_session(player))
        )

    @covers_requirement(
        "combat-modifier-table::worn-equipment-merges-into-the-merged-bundle-of-both-evaluation-paths"
    )
    def test_preview_and_resolve_agree_on_equipment_adjusted_mp_cost(self):
        player = self.wear(_player("mp parity"), _ROBE.key)
        grant_lineage(player, [_MP_SKILL.key])
        room = create_object(Room, key="mp parity arena")
        player.location = room
        monster = _monster("mp parity goblin", room)
        context = self._context(player, monster)

        # The probed percent lands on the synthetic skill's declared cost:
        # floor(20 * (1 + pct)).
        declared = _MP_SKILL.cost["mp"]
        adjusted = math.floor(declared * (1 + _ROBE_MP_PCT))
        self.assertEqual(
            evaluate_combat_modifiers_no_create(player)["mp_cost"],
            f"{int(_ROBE_MP_PCT * 100)}%",
        )
        player.traits.mp.base = adjusted
        player.traits.mp.current = adjusted
        preview = preview_skill(player, _MP_SKILL.key, context, [monster])
        self.assertTrue(preview.enabled)
        preflight = ActionResolver.preflight(
            ActionRequest(player, _MP_SKILL.key, [monster], context)
        )
        self.assertEqual(preflight.outcome, "success")

        player.traits.mp.current = adjusted - 1
        preview = preview_skill(player, _MP_SKILL.key, context, [monster])
        self.assertFalse(preview.enabled)
        preflight = ActionResolver.preflight(
            ActionRequest(player, _MP_SKILL.key, [monster], context)
        )
        self.assertEqual(preflight.outcome, "rejected")

        # A successful cast spends exactly the equipment-adjusted cost.
        player.traits.mp.current = adjusted
        with patch("world.rules.combat.roll_d100", return_value=50):
            result = ActionResolver.resolve(
                ActionRequest(player, _MP_SKILL.key, [monster], context)
            )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(player.traits.mp.current, 0)

    @covers_requirement(
        "combat-modifier-table::worn-equipment-merges-into-the-merged-bundle-of-both-evaluation-paths"
    )
    def test_preview_gates_on_equipment_adjusted_sp_cost(self):
        player = self.wear(_player("sp parity"), _SEAL.key)
        player.db.skills = {"active": [_SP_SKILL.key], "passive": []}
        room = create_object(Room, key="sp parity arena")
        player.location = room
        monster = _monster("sp parity goblin", room)
        context = self._context(player, monster)

        # Declared 20 SP, seal percent: floor(20 * (1 + pct)).
        declared = _SP_SKILL.cost["sp"]
        adjusted = math.floor(declared * (1 + _SEAL_SP_PCT))
        player.traits.sp.current = adjusted
        self.assertTrue(
            preview_skill(player, _SP_SKILL.key, context, [monster]).enabled
        )
        player.traits.sp.current = adjusted - 1
        self.assertFalse(
            preview_skill(player, _SP_SKILL.key, context, [monster]).enabled
        )

        # Without the seal the same adjusted SP cannot afford the skill.
        self.assertEqual(
            toggle_equipment(player, _SEAL.key).outcome, "success"
        )
        player.traits.sp.current = adjusted
        self.assertFalse(
            preview_skill(player, _SP_SKILL.key, context, [monster]).enabled
        )
        player.traits.sp.current = declared
        self.assertTrue(
            preview_skill(player, _SP_SKILL.key, context, [monster]).enabled
        )
class _FixtureFieldCase(_WearerCase):
    def _staged_damage(self, actor, target):
        with patch("world.rules.combat.roll_d100", return_value=100):
            pending = combat._handle_damage(
                actor, [target], f"damage:{_T_ELEMENT}:physical", {}, 1.0
            )[0]
        return int(pending.description.rsplit("|", 1)[1])


class DamageWiringTests(_FixtureFieldCase):
    @covers_requirement(
        "combat-modifier-table::worn-equipment-merges-into-the-merged-bundle-of-both-evaluation-paths"
    )
    def test_worn_weapon_raises_staged_physical_damage(self):
        attacker = FakeEntity("wiring attacker", atk_phys=20, agility=10)
        defender = FakeEntity("wiring defender", hp=1000, agility=10, defense=5)
        baseline = self._staged_damage(attacker, defender)
        _worn(attacker, weapon=_SABER.key)
        worn = self._staged_damage(attacker, defender)
        # Crit roll 100 doubles the weapon's flat attack before defense.
        self.assertEqual(worn - baseline, 2 * _ATK)

    @covers_requirement(
        "combat-modifier-table::worn-equipment-merges-into-the-merged-bundle-of-both-evaluation-paths"
    )
    def test_worn_armor_moves_the_defender_required_roll(self):
        attacker = FakeEntity("roll attacker", agility=10)
        defender = FakeEntity("roll defender", agility=30, defense=5)
        self.assertEqual(_required_roll(attacker, defender), 51 + 30 - 10)
        _worn(defender, armor=_MAIL.key)
        # The armor's percent agility scales the effective agility.
        scaled = 30 * (1 + _percent(_MAIL_AGILITY))
        self.assertAlmostEqual(_required_roll(attacker, defender), 51 + scaled - 10)
        hit, margin = _to_hit(attacker, defender, math.ceil(51 + scaled - 10))
        self.assertTrue(hit)
        missed, _ = _to_hit(attacker, defender, math.ceil(51 + scaled - 10) - 1)
        self.assertFalse(missed)


class AdjustedAgilityTests(_FixtureFieldCase):
    @covers_requirement(
        "combat-modifier-table::adjusted-agility-never-resolves-negative"
    )
    def test_flat_penalty_floors_agility_at_zero_everywhere(self):
        floored = FakeEntity("floored agility", agility=2)
        zero = FakeEntity("zero agility", agility=0)
        attacker = FakeEntity("steady attacker", agility=10)
        # The probed penalty row floors the 2-agility fixture at zero.
        _worn(floored, off=_ECHO.key)

        self.assertEqual(
            adjusted_agility(floored, {"agility_flat": _ECHO_AGILITY_FLAT}), 0.0
        )
        self.assertEqual(flee_agility(floored), flee_agility(zero))
        self.assertEqual(
            _required_roll(attacker, floored), _required_roll(attacker, zero)
        )
        # The floored defender behaves exactly like the zero-agility one in
        # live to-hit math.
        hit_a, margin_a = _to_hit(attacker, floored, 51)
        hit_b, margin_b = _to_hit(attacker, zero, 51)
        self.assertEqual(hit_a, hit_b)
        self.assertAlmostEqual(margin_a, margin_b)

    @covers_requirement(
        "combat-modifier-table::adjusted-agility-never-resolves-negative"
    )
    def test_resist_blend_shares_the_shared_floor(self):
        register_catalog()
        entity = _player("floored resist blend")
        entity.db.inventory = [_ECHO.key]
        self.assertEqual(
            toggle_equipment(entity, _ECHO.key).outcome, "success"
        )
        entity.traits.agility.base = 2
        entity.traits.agility.current = 2
        blended = _blended_score(entity)
        # The probed penalty floors agility to 0; the probed flat attack is the
        # addend the blend's atk component reads.
        expected = 0.6 * 0.0 + 0.4 * (
            float(entity.skills.effective_value("atk_phys")) + _ECHO_ATK
        )
        self.assertAlmostEqual(blended, expected)

    @covers_requirement(
        "combat-modifier-table::adjusted-agility-never-resolves-negative"
    )
    def test_percent_scales_then_flat_adds_then_floor(self):
        entity = FakeEntity("composed agility", agility=10)
        # -50% scales to 5, +3 lands on top of the scaled value.
        self.assertEqual(
            adjusted_agility(entity, {"agility": "-50%", "agility_flat": 3}),
            8.0,
        )
        # The floor lands after both components: a beyond--100% percent
        # still cannot leave the flat addend as a negative escape hatch.
        self.assertEqual(
            adjusted_agility(entity, {"agility": "-200%", "agility_flat": 3}),
            0.0,
        )
        self.assertEqual(adjusted_agility(entity, {"agility": "-200%"}), 0.0)

    @covers_requirement(
        "combat-modifier-table::adjusted-agility-never-resolves-negative"
    )
    def test_initiative_keeps_its_raw_agility_exception(self):
        boosted = FakeEntity("cloak carrier", agility=10)
        plain = FakeEntity("plain runner", agility=10 + _BLADE_AGILITY + 1)
        # The blade's flat agility would let the adjusted bundle invert the
        # order — an initiative that consulted the bundle would flip it.
        _worn(boosted, weapon=_BLADE.key)
        field = Battlefield(
            {
                "first": frozenset({"cloak carrier"}),
                "second": frozenset({"plain runner"}),
            },
            {"cloak carrier": boosted, "plain runner": plain},
        )
        with patch("world.rules.combat.roll_d100", side_effect=[1, 1]):
            order = combat.roll_initiative(field)
        # Raw effective agility decides: the plain runner outranks the
        # gear-boosted carrier despite the higher adjusted value.
        self.assertEqual(order, ["plain runner", "cloak carrier"])
class HealWiringTests(_WearerCase):
    def setUp(self):
        super().setUp()
        self.caster = _player("wiring caster")
        self.caster.traits.magic_power.base = 40

    @covers_requirement(
        "combat-resolution::skill-heal-magnitude-scales-by-the-merged-heal-gain-percent"
    )
    def test_holy_gear_amplifies_skill_heal_magnitude(self):
        self.assertEqual(_heal_magnitude(self.caster), 40)
        self.wear(self.caster, _EMBLEM.key)
        # The probed heal_gain percent lands on the caster-stat base.
        self.assertEqual(
            _heal_magnitude(self.caster), math.floor(40 * (1 + _HEAL_GAIN_PCT))
        )

    @covers_requirement(
        "combat-resolution::skill-heal-magnitude-scales-by-the-merged-heal-gain-percent"
    )
    def test_gear_scaling_floors_instead_of_banker_rounding(self):
        self.caster.traits.magic_power.base = 3
        self.wear(self.caster, _EMBLEM.key)
        raw = 3 * (1 + _HEAL_GAIN_PCT)
        self.assertEqual(_heal_magnitude(self.caster), math.floor(raw))
        # The probed row keeps the fractional part observable, so flooring
        # is distinguishable from rounding here.
        self.assertNotEqual(_heal_magnitude(self.caster), round(raw))

    @covers_requirement(
        "combat-resolution::skill-heal-magnitude-scales-by-the-merged-heal-gain-percent"
    )
    def test_magic_gear_lifts_the_heal_base(self):
        self.wear(self.caster, _ROBE.key)
        # The bound row's magic_power flat raises the caster-stat base.
        self.assertEqual(_heal_magnitude(self.caster), 40 + _ROBE_MAGIC)

    @covers_requirement(
        "combat-resolution::skill-heal-magnitude-scales-by-the-merged-heal-gain-percent"
    )
    def test_potion_heal_stays_flat_under_heal_gear(self):
        self.wear(self.caster, _EMBLEM.key)
        self.caster.db.inventory = [_TONIC.key]
        self.caster.traits.hp.base = 100
        self.caster.traits.hp.current = 10
        preflight = preflight_item_use(
            ItemUseRequest(actor=self.caster, item_key=_TONIC.key),
            in_combat=False,
        )
        self.assertTrue(preflight.allowed)
        # Potion heals stay the flat effect-row amount; heal-gear percent
        # never scales them, and the restore plan equals current + amount.
        self.assertEqual(preflight.plan.amount, _HEAL_AMOUNT)
        self.assertEqual(preflight.plan.gauge_restored, 10 + _HEAL_AMOUNT)

    def test_fractional_heal_gain_percent_is_tolerated(self):
        with patch(
            "world.rules.combat.evaluate_combat_modifiers",
            return_value={"heal_gain": "+2.5%"},
        ):
            self.assertEqual(_heal_magnitude(self.caster), 41)  # floor(40*1.025)


class SyntheticCastRowShapeTests(unittest.TestCase):
    """The declared costs the parity tests compute against are owned by this
    file (synthetic rows), so their shape is asserted here — the shipped
    declared costs remain registry content owned by the registered
    skill-registry data-contract files."""

    def test_declared_costs_under_test(self):
        self.assertEqual(_MP_SKILL.cost, {"mp": 20})
        self.assertEqual(_SP_SKILL.cost, {"sp": 20})
        self.assertGreater(_ROBE_MP_PCT, -0.5)
        self.assertGreater(_SEAL_SP_PCT, -0.5)
