"""Lamb-seal target-preference narrowing (church design §5.7).

``rite_lamb_mark`` mounts the ``lamb_seal`` buff (the charge-on-climax seal);
``monster_behaviour_policy`` narrows single-target candidates to seal-bearers
BEFORE target-strategy evaluation, in canonical order (player first, then
ascending pk). The seal is preference, not threat: AREA paths and the
positional-marker exclusion are untouched, and with no seal anywhere every
decision is byte-identical. Security-relevant baseline: the shipped
``lamb_seal`` buff key is the one literal this module shares with the rules
module that owns the seal; every other number is authored here.

Synthetic monsters (file-local skill rows via the shared kit) face REAL
seal-bearing party entities so the PlayerCharacter-vs-NPC canonical order is
exercised through the shipped buff surface.
"""

from unittest.mock import patch

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from world.rules.buffs import apply_buff
from world.rules.monster_behaviour import monster_behaviour_policy
from world.rules.sexual_state import _apply_climax_phase_set

from ._combat_session_helpers import open_synthetic_scope
from .test_monster_behaviour_policy import (
    _T_AREA,
    _T_CLAW,
    _T_SPELL,
    FakeMonster,
    _field,
)

_SCOPE_EXTRA = {
    "skills": {row.key: row for row in (_T_SPELL, _T_AREA, _T_CLAW)}
}

def _party_member(key: str, *, hp: int = 100, npc: bool = False):
    cls = NPC if npc else PlayerCharacter
    entity = create_object(cls, key=key)
    entity.race = "human"
    entity.apply_race_baseline()
    entity.traits.hp.base = hp
    entity.traits.hp.current = hp
    return entity


def _seal(entity) -> None:
    apply_buff(entity, "lamb_seal")


class MonsterSealNarrowTests(EvenniaTestCase):
    """The policy-level narrowing contract (design §5.7 scenarios)."""

    def setUp(self):
        super().setUp()
        open_synthetic_scope(self, "skills", "elements", extra=_SCOPE_EXTRA)

    @covers_requirement("lamb-mark-narrows-monster-target-preference-with-a-charging-buff")
    def test_seal_redirects_over_lowest_hp_strategy(self):
        """A lowest_hp monster picks the seal-bearer over a cheaper target."""
        monster = FakeMonster(
            "seal actor", behaviour_tree="instinctive", owned=[_T_SPELL.key]
        )
        sealed = _party_member("sealed sister", hp=90)
        _seal(sealed)
        cheap = _party_member("cheap normal", hp=10)
        request = monster_behaviour_policy(monster, _field(monster, [sealed, cheap]))
        self.assertEqual([target.key for target in request.targets], [sealed.key])

    @covers_requirement("lamb-mark-narrows-monster-target-preference-with-a-charging-buff")
    def test_seal_redirects_over_highest_effective_power_strategy(self):
        """A highest_effective_power monster still picks the seal-bearer."""
        monster = FakeMonster(
            "seal brute", behaviour_tree="brute", owned=[_T_SPELL.key]
        )
        sealed = _party_member("weak sealed", hp=1)
        _seal(sealed)
        strong = _party_member("strong normal", hp=100)
        request = monster_behaviour_policy(monster, _field(monster, [sealed, strong]))
        self.assertEqual([target.key for target in request.targets], [sealed.key])

    @covers_requirement("lamb-mark-narrows-monster-target-preference-with-a-charging-buff")
    def test_multi_seal_canonical_order_player_first_then_ascending_pk(self):
        """Two seal-bearers resolve player-first, then ascending pk."""
        monster = FakeMonster(
            "seal order", behaviour_tree="instinctive", owned=[_T_SPELL.key]
        )
        player = _party_member("sealed player", hp=50)
        _seal(player)
        npc_low = _party_member("sealed npc low", hp=60, npc=True)
        _seal(npc_low)
        npc_high = _party_member("sealed npc high", hp=70, npc=True)
        _seal(npc_high)
        field = _field(monster, [player, npc_high, npc_low])
        # The player-bearer is preferred regardless of position in the list.
        request = monster_behaviour_policy(monster, field)
        self.assertEqual([target.key for target in request.targets], [player.key])
        # Without the player, ascending pk among the NPC bearers wins.
        field = _field(monster, [npc_high, npc_low])
        request = monster_behaviour_policy(monster, field)
        expected = sorted((npc_low, npc_high), key=lambda entity: int(entity.pk))[0]
        self.assertEqual([target.key for target in request.targets], [expected.key])

    @covers_requirement("lamb-mark-narrows-monster-target-preference-with-a-charging-buff")
    def test_no_seal_decisions_are_byte_identical(self):
        """Zero seals: the metric path runs exactly as before, dice included."""
        monster = FakeMonster(
            "seal free actor", behaviour_tree="instinctive", owned=[_T_SPELL.key]
        )
        low = _party_member("low target", hp=30)
        high = _party_member("high target", hp=70)
        with patch(
            "world.rules.monster_behaviour.dice.roll_d100"
        ) as roller:
            request = monster_behaviour_policy(monster, _field(monster, [low, high]))
        roller.assert_not_called()
        self.assertEqual([target.key for target in request.targets], [low.key])
        # A metric tie still consumes the tie-break dice, unchanged.
        twin_a = _party_member("twin a", hp=50)
        twin_b = _party_member("twin b", hp=50)
        with patch(
            "world.rules.monster_behaviour.dice.roll_d100", return_value=1
        ) as roller:
            request = monster_behaviour_policy(
                monster, _field(monster, [twin_a, twin_b])
            )
        roller.assert_called_once()

    @covers_requirement("lamb-mark-narrows-monster-target-preference-with-a-charging-buff")
    def test_area_path_is_untouched_by_seals(self):
        """An AREA decision neither narrows nor substitutes with seals present."""
        monster = FakeMonster(
            "seal area", behaviour_tree="pack_hunter", owned=[_T_AREA.key, _T_SPELL.key]
        )
        sealed_a = _party_member("sealed a", hp=90)
        _seal(sealed_a)
        sealed_b = _party_member("sealed b", hp=90)
        _seal(sealed_b)
        request = monster_behaviour_policy(
            monster, _field(monster, [sealed_a, sealed_b])
        )
        self.assertEqual(request.skill_key, _T_AREA.key)
        self.assertEqual(request.targets, "all-enemies")

    @covers_requirement("lamb-mark-narrows-monster-target-preference-with-a-charging-buff")
    def test_positional_exclusion_is_never_substituted_by_the_seal(self):
        """A strike-only kit still refuses a displaced seal-bearer."""
        monster = FakeMonster(
            "seal strike", behaviour_tree="instinctive", owned=[_T_CLAW.key]
        )
        displaced_sealed = _party_member("displaced sealed", hp=80)
        _seal(displaced_sealed)
        apply_buff(displaced_sealed, "displaced")
        self.assertIsNone(
            monster_behaviour_policy(monster, _field(monster, [displaced_sealed]))
        )
        # A magic kit reaches the displaced seal-bearer: the seal narrows the
        # base, while the positional hygiene stays an orthogonal exclusion.
        caster = FakeMonster(
            "seal caster", behaviour_tree="instinctive", owned=[_T_SPELL.key]
        )
        request = monster_behaviour_policy(caster, _field(caster, [displaced_sealed]))
        self.assertEqual(
            [target.key for target in request.targets], [displaced_sealed.key]
        )
        self.assertEqual(request.skill_key, _T_SPELL.key)

    @covers_requirement("lamb-mark-narrows-monster-target-preference-with-a-charging-buff")
    def test_two_climaxes_lift_the_seal_and_subsequent_fights_show_none(self):
        """Two 進行中 transitions consume the charges; the seal then vanishes
        without a fresh cast, so the policy returns to its metric path."""
        monster = FakeMonster(
            "seal lift", behaviour_tree="instinctive", owned=[_T_SPELL.key]
        )
        sealed = _party_member("lifting sister", hp=90)
        _seal(sealed)
        cheap = _party_member("cheap backup", hp=10)
        _apply_climax_phase_set(sealed, "接近")
        _apply_climax_phase_set(sealed, "進行中")
        # First consumption leaves the seal live: the redirect still holds.
        request = monster_behaviour_policy(monster, _field(monster, [sealed, cheap]))
        self.assertEqual([target.key for target in request.targets], [sealed.key])
        _apply_climax_phase_set(sealed, "餘韻")
        _apply_climax_phase_set(sealed, "接近")
        _apply_climax_phase_set(sealed, "進行中")
        # Second consumption removes the buff: no seal anywhere → the normal
        # lowest-hp decision (cheap backup), byte-identical baseline.
        request = monster_behaviour_policy(monster, _field(monster, [sealed, cheap]))
        self.assertEqual([target.key for target in request.targets], [cheap.key])