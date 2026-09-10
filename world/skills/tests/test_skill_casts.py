"""Cast-resolution tests built on the synthetic skill kit.

The shipped-registry content claims these tests used to carry (dual-blade
sibling, light-sword damage declaration, full-earth spell round-trip) live
in the registered data-contract files (test_skill_registry.py,
test_spell_catalogs.py). What remains here is cast-resolution *behavior*
exercised through synthetic rows: damage dispatch and cost deduction, self
buffs committing to the caster only, target-spec rejection, and the
usable-out-of-combat flag gate against the damaging-action gate.
"""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.rules.action import ActionRequest, ActionResolver, RejectReason
from world.rules.combat import Battlefield, BattlefieldActionContext
from world.rules.targeting import RoomActionContext
from world.skills.registry import SkillKind, TargetSpec
from world.tests.synthetic_data import (
    SYNTH_SKILLS,
    make_skill,
    synthetic_registries,
)

# Synthetic cast fixtures. The damage element is borrowed from the kit's
# own spell row, so the closed element enum never needs a synthetic name.
_ELEMENT = SYNTH_SKILLS["t_ember_burst"].element
_T_CLEAVE = make_skill(
    "t_iron_cleave",
    effects=[f"damage:{_ELEMENT}:physical"],
    cost={"sp": 30},
    usable_out_of_combat=False,
)
_T_HOLLOW_STANCE = make_skill(
    "t_hollow_stance",
    effects=["stat_multiply:agility:1.1"],
    kind=SkillKind.PASSIVE,
    target_spec=TargetSpec.SELF,
)
_T_BLAZE_JAB = make_skill(
    "t_blaze_jab",
    effects=[f"damage:{_ELEMENT}:magic"],
    cost={"mp": 12},
    usable_out_of_combat=True,
)
_T_MOSS_VEIL = SYNTH_SKILLS["t_moss_veil"]

_SCOPE = synthetic_registries(
    "skills",
    "buffs",
    "races",
    "subraces",
    "static_tiers",
    "elements",
    "items",
    "sexual_acts",
    extra={
        "skills": {
            skill.key: skill for skill in (_T_CLEAVE, _T_HOLLOW_STANCE, _T_BLAZE_JAB)
        }
    },
)


# Lifecycle note: the kit's class decorator wraps collected ``test*`` methods,
# not ``setUp`` — so every synthetic-scoped entity construction happens in a
# helper invoked from the test body, guaranteeing the patched registries are
# installed when ``apply_race_baseline`` reads the race catalog.
@_SCOPE
class SyntheticDamageCastTests(EvenniaTestCase):
    def _build(self):
        self.actor = create_object(PlayerCharacter, key="synth cleave actor")
        self.target = create_object(PlayerCharacter, key="synth cleave target")
        for entity in (self.actor, self.target):
            entity.race = "t_duskmari"
            entity.subrace = "t_duskmari_evensong"
            entity.apply_race_baseline()
        self.actor.db.skills = {"active": [_T_CLEAVE.key], "passive": []}
        self.target.db.skills = {"active": [], "passive": []}
        battlefield = Battlefield(
            {
                "party": frozenset({"synth cleave actor"}),
                "foes": frozenset({"synth cleave target"}),
            },
            {"synth cleave actor": self.actor, "synth cleave target": self.target},
        )
        self.request = ActionRequest(
            self.actor,
            _T_CLEAVE.key,
            [self.target],
            BattlefieldActionContext(battlefield),
        )

    def test_cast_resolves_via_damage_handler_and_deducts_the_declared_cost(self):
        self._build()
        before = self.target.traits.hp.value
        sp_before = self.actor.traits.sp.value
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = ActionResolver.resolve(self.request)
        self.assertEqual(result.outcome, "success")
        self.assertLess(self.target.traits.hp.value, before)
        self.assertEqual(
            [entry.kind for entry in result.event_log.entries[:2]],
            ["roll", "damage"],
        )
        self.assertEqual(
            self.actor.traits.sp.value, sp_before - _T_CLEAVE.cost["sp"]
        )

    def test_unrelated_passive_ownership_has_no_bearing_on_cost(self):
        self._build()
        self.actor.db.skills = {
            "active": [_T_CLEAVE.key],
            "passive": [_T_HOLLOW_STANCE.key],
        }
        self.assertIn(_T_HOLLOW_STANCE.key, self.actor.skills.owned_keys())
        sp_before = self.actor.traits.sp.value
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = ActionResolver.resolve(self.request)
        self.assertEqual(result.outcome, "success")
        self.assertEqual(
            self.actor.traits.sp.value, sp_before - _T_CLEAVE.cost["sp"]
        )


@_SCOPE
class SelfBuffCastTests(EvenniaTestCase):
    def _build(self):
        self.actor = create_object(PlayerCharacter, key="synth veil actor")
        self.other = create_object(PlayerCharacter, key="synth veil other")
        for entity in (self.actor, self.other):
            entity.race = "t_duskmari"
            entity.subrace = "t_duskmari_evensong"
            entity.apply_race_baseline()
        self.actor.db.skills = {"active": [_T_MOSS_VEIL.key], "passive": []}
        self.other.db.skills = {"active": [], "passive": []}
        battlefield = Battlefield(
            {
                "party": frozenset({"synth veil actor"}),
                "foes": frozenset({"synth veil other"}),
            },
            {"synth veil actor": self.actor, "synth veil other": self.other},
        )
        self.context = BattlefieldActionContext(battlefield)

    def test_self_cast_applies_the_buff_to_the_caster(self):
        self._build()
        request = ActionRequest(self.actor, _T_MOSS_VEIL.key, [], self.context)
        result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "success")
        buff_key = _T_MOSS_VEIL.parsed_effects[0].buff_key
        self.assertIn(buff_key, self.actor.buffs.all)
        self.assertNotIn(buff_key, self.other.buffs.all)

    def test_cast_at_an_explicit_other_target_is_rejected(self):
        self._build()
        request = ActionRequest(
            self.actor, _T_MOSS_VEIL.key, [self.other], self.context
        )
        result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "rejected")
        self.assertEqual(result.reason, RejectReason.TARGET_SPEC_MISMATCH)


@_SCOPE
class FieldDamageSelectionTests(EvenniaTestCase):
    """``usable_out_of_combat`` governs selection; the damaging-action gate
    governs resolution (skill-field-availability, design D-7)."""

    def _build(self):
        from typeclasses.rooms import Room

        self.room = create_object(Room, key="field room")
        self.actor = create_object(PlayerCharacter, key="field selector")
        self.actor.race = "t_duskmari"
        self.actor.subrace = "t_duskmari_evensong"
        self.actor.apply_race_baseline()
        self.actor.location = self.room
        self.actor.db.skills = {"active": [_T_BLAZE_JAB.key], "passive": []}

    @covers_requirement(
        "action-resolution-pipeline::the-out-of-combat-gates-fire-in-a-fixed-specified-order"
    )
    def test_newly_permitted_damage_spell_is_selectable_but_never_resolves(self):
        self._build()
        self.assertTrue(_T_BLAZE_JAB.usable_out_of_combat)
        mp_before = self.actor.traits.mp.value
        result = ActionResolver.resolve(
            ActionRequest(
                self.actor, _T_BLAZE_JAB.key, [self.actor], RoomActionContext(self.room)
            )
        )
        # The flag gate lets the cast through to the damaging-action gate,
        # which rejects before any MP is deducted or effect is staged.
        self.assertEqual(result.outcome, "rejected")
        self.assertIs(result.reason, RejectReason.DAMAGE_REQUIRES_MONSTER_TARGET)
        self.assertEqual(self.actor.traits.mp.value, mp_before)

    @covers_requirement(
        "action-resolution-pipeline::the-out-of-combat-gates-fire-in-a-fixed-specified-order"
    )
    def test_skill_declaring_false_is_rejected_at_the_flag_gate(self):
        self._build()
        # The out-of-combat-permitted fixture is a second synthetic row; the
        # damage fixture deliberately declares False, so the flag gate — not
        # the damaging-action gate — rejects its field selection.
        self.assertFalse(_T_CLEAVE.usable_out_of_combat)
        self.actor.db.skills = {
            "active": [_T_CLEAVE.key],
            "passive": [],
        }
        result = ActionResolver.resolve(
            ActionRequest(
                self.actor, _T_CLEAVE.key, [self.actor], RoomActionContext(self.room)
            )
        )
        self.assertEqual(result.outcome, "rejected")
        self.assertIs(result.reason, RejectReason.SKILL_NOT_USABLE_OUT_OF_COMBAT)
