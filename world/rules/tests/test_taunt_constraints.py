"""Initiative-priority Taunt and legal enemy decision constraints.

Pure ``unittest.TestCase`` covers the round's Taunt winner resolution and the
round execution context; ``EvenniaTestCase`` covers the deterministic enemy
policy paths (the delegated non-``Monster`` policy, the Monster legacy body,
and a real persistent session) on synthetic entities. No shipped skill,
element, tier or archetype key is named by a resolvable literal: the archetype
used for the area case is resolved from the live rulebook by predicate.

The tests establish this slice's contracts: the winner per enemy is the first
taunter in the round's own initiative sequence (entry order and confirmation
order have no influence, no extra dice are drawn, and a losing declaration is
never promoted); a declaration costs no resource and consumes its actor's
action; the active winner is revalidated before each enemy decision and drops
out permanently for the round when it can no longer act; and an active winner
narrows an enemy single-target hostile action to itself only when it is
ordinarily legal, leaving AREA, support and flee freedom intact.

Traceability ordering (``docs/development/spec-test-traceability.md``):
``tools.spec_traceability`` resolves ids against the main specs under
``openspec/specs/`` only, so the two requirement ids this change ADDS do not
exist until ``openspec archive`` syncs the delta and cannot be annotated now;
they are annotated at archive time (the ``party-combat-defend-dodge``
precedent).
"""

import contextlib
import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.npcs import NPC
from typeclasses.rooms import Room

from world.rules.combat import (
    Battlefield,
    BattlefieldActionContext,
    RoundTactical,
    default_attack_policy,
    run_round,
)
from world.rules.combat.rounds import _resolve_taunt_winners
from world.rules.combat_session import (
    confirm_actor_command,
    engage,
    read_session,
)
from world.rules.disengage import FLEE_SKILL_KEY
from world.rules.monster_behaviour import (
    BEHAVIOUR_PROFILES,
    DecisionMode,
    monster_behaviour_policy,
)
from world.rules.party import join_party
from world.skills.registry import TargetSpec

from ._combat_session_helpers import (
    SYNTH_GLOW_ELEMENT,
    _monster,
    _player,
    complete_party_draft,
    open_synthetic_scope,
    synth_damage_skill,
    synth_innate_overlay,
)
from .combat_fixtures import FakeEntity

#: A legacy archetype that prefers an AREA action against several enemies,
#: resolved from the live rulebook by predicate (never a shipped literal).
AREA_ARCHETYPE = next(
    key
    for key, profile in BEHAVIOUR_PROFILES.items()
    if profile.prefer_area_when_multiple_enemies
    and profile.decision_mode is DecisionMode.LEGACY
)

#: A registered AREA damage skill for the area-freedom case.
AREA_SKILL = synth_damage_skill(
    "t_taunt_area",
    "挑釁範圍術",
    effects=[f"damage:{SYNTH_GLOW_ELEMENT}:magic"],
    cost={},
    target_spec=TargetSpec.AREA,
)


def _round_patches(roll=90):
    """The patches a pure ``run_round`` test needs to stay deterministic."""
    return [
        patch("world.rules.combat.rounds.roll_d100", return_value=roll),
        patch("world.rules.combat.rounds.tick_buffs", return_value=()),
        patch("world.rules.combat.rounds.decay_tick"),
        patch("world.rules.combat.rounds.climax_settlement_action", return_value=None),
    ]


@contextlib.contextmanager
def _round_environment(roll=90):
    """One deterministic, non-throwing round environment."""
    with contextlib.ExitStack() as stack:
        for patcher in _round_patches(roll):
            stack.enter_context(patcher)
        stack.enter_context(
            patch("world.rules.combat.battlefield.roll_d100", return_value=90)
        )
        yield


class TauntWinnerResolutionTests(unittest.TestCase):
    """The round's winner per enemy is the first taunter in initiative order."""

    def _field(self, *entity_keys):
        roster = {key: FakeEntity(key) for key in entity_keys}
        return Battlefield(
            {
                "party": frozenset({"slower", "faster"}),
                "foes": frozenset({"boss"}),
            },
            roster,
        )

    def test_the_first_taunter_in_initiative_wins_regardless_of_entry_order(self):
        battlefield = self._field("slower", "faster", "boss")
        order = ["faster", "slower", "boss"]
        declared_first = {"slower": "boss", "faster": "boss"}
        declared_last = {"faster": "boss", "slower": "boss"}
        self.assertEqual(
            _resolve_taunt_winners(declared_first, order, battlefield),
            {"boss": "faster"},
        )
        self.assertEqual(
            _resolve_taunt_winners(declared_last, order, battlefield),
            {"boss": "faster"},
        )

    def test_only_one_winner_is_kept_per_enemy(self):
        battlefield = self._field("slower", "faster", "boss")
        winners = _resolve_taunt_winners(
            {"slower": "boss", "faster": "boss"}, ["faster", "slower", "boss"], battlefield
        )
        self.assertEqual(list(winners), ["boss"])

    def test_an_unknown_taunter_enemy_or_absent_taunter_is_ignored(self):
        battlefield = self._field("slower", "faster", "boss")
        order = ["faster", "slower", "boss"]
        self.assertEqual(
            _resolve_taunt_winners({"ghost": "boss"}, order, battlefield), {}
        )
        self.assertEqual(
            _resolve_taunt_winners({"faster": "ghost"}, order, battlefield), {}
        )
        # A taunter already absent from the initiative sequence cannot act.
        self.assertEqual(
            _resolve_taunt_winners({"faster": "boss"}, ["slower", "boss"], battlefield),
            {},
        )


class TauntRoundContextTests(unittest.TestCase):
    """The winner rides the round context and is revalidated live."""

    def _field(self):
        return Battlefield(
            {
                "party": frozenset({"winner"}),
                "foes": frozenset({"boss"}),
            },
            {"winner": FakeEntity("winner"), "boss": FakeEntity("boss")},
        )

    def test_the_winner_is_revalidated_on_every_read(self):
        battlefield = self._field()
        winner = battlefield.roster["winner"]
        self.assertIsNone(battlefield.taunt_winner("boss"))
        battlefield.tactical = RoundTactical({}, {"boss": "winner"})
        self.assertIs(battlefield.taunt_winner("boss"), winner)
        winner.traits.hp.current = 0
        self.assertIsNone(battlefield.taunt_winner("boss"))
        winner.traits.hp.current = 100
        battlefield.knocked_out.add("winner")
        self.assertIsNone(battlefield.taunt_winner("boss"))
        battlefield.knocked_out.discard("winner")
        battlefield.fled.add("winner")
        self.assertIsNone(battlefield.taunt_winner("boss"))

    def test_run_round_activates_the_winner_for_the_round_then_expires(self):
        slow = FakeEntity("slow", hp=100, agility=1)
        boss = FakeEntity("boss", hp=100, agility=99)
        battlefield = Battlefield(
            {"party": frozenset({"slow"}), "foes": frozenset({"boss"})},
            {"slow": slow, "boss": boss},
        )
        seen: list[object] = []

        def provider(entity, field):
            seen.append(field.taunt_winner("boss"))
            return None

        with _round_environment():
            run_round(battlefield, provider, taunt_declarations={"slow": "boss"})
        # The winner was active before the enemy's own initiative position.
        self.assertTrue(seen)
        self.assertTrue(all(winner is slow for winner in seen))
        # Round ended: the transient context expired and cannot stack.
        self.assertIsNone(battlefield.tactical)

        seen.clear()
        with _round_environment():
            run_round(battlefield, provider)
        self.assertTrue(seen)
        self.assertTrue(all(winner is None for winner in seen))
        self.assertIsNone(battlefield.tactical)

    def test_taunt_ranking_draws_no_extra_initiative_roll(self):
        slow = FakeEntity("slow", hp=100, agility=1)
        boss = FakeEntity("boss", hp=100, agility=99)
        battlefield = Battlefield(
            {"party": frozenset({"slow"}), "foes": frozenset({"boss"})},
            {"slow": slow, "boss": boss},
        )
        draws: list[int] = []

        def roll():
            draws.append(1)
            return 50

        with contextlib.ExitStack() as stack:
            for patcher in _round_patches():
                stack.enter_context(patcher)
            stack.enter_context(
                patch("world.rules.combat.battlefield.roll_d100", side_effect=roll)
            )
            run_round(battlefield, lambda entity, field: None, taunt_declarations={"slow": "boss"})
        # One draw per eligible participant: Taunt ranking adds none, so a
        # second declaration can never reroll initiative.
        self.assertEqual(len(draws), 2)


class TauntedEnemyPolicyTests(EvenniaTestCase):
    """The deterministic enemy policy paths honour the active winner."""

    def setUp(self):
        extra = synth_innate_overlay()
        extra["skills"][AREA_SKILL.key] = AREA_SKILL
        open_synthetic_scope(
            self, "monster_tiers", "races", "skills", "elements", extra=extra
        )
        super().setUp()
        self.room = create_object(Room, key="taunt arena")
        self.monster = _monster("taunt goblin", hp=100)
        self.monster.location = self.room
        self.taunter = _player("taunt knight")
        self.taunter.location = self.room
        self.other = _player("taunt squire")
        self.other.location = self.room

    def _field(self):
        return Battlefield(
            {
                "foes": frozenset({str(self.monster.key)}),
                "party": frozenset({str(self.taunter.key), str(self.other.key)}),
            },
            {
                str(self.monster.key): self.monster,
                str(self.taunter.key): self.taunter,
                str(self.other.key): self.other,
            },
        )

    def _taunted(self, field):
        field.tactical = RoundTactical(
            {}, {str(self.monster.key): str(self.taunter.key)}
        )
        return field

    def _target_keys(self, request):
        return [str(target.key) for target in request.targets]

    def test_the_legacy_policy_attacks_the_winner_over_a_weaker_ally(self):
        # The ally is the lowest-HP target, so without the taunt the policy
        # would pick it; the active winner overrides that ordinary choice.
        self.other.traits.hp.base = 40
        self.other.traits.hp.current = 40
        field = self._taunted(self._field())
        request = monster_behaviour_policy(
            self.monster, field, context=BattlefieldActionContext(field)
        )
        self.assertEqual(self._target_keys(request), [str(self.taunter.key)])

    def test_a_suppressed_winner_leaves_the_ordinary_choice(self):
        self.other.traits.hp.base = 40
        self.other.traits.hp.current = 40
        field = self._taunted(self._field())
        field.knocked_out.add(str(self.taunter.key))
        request = monster_behaviour_policy(
            self.monster, field, context=BattlefieldActionContext(field)
        )
        self.assertEqual(self._target_keys(request), [str(self.other.key)])

    def test_the_delegated_policy_constrains_a_non_monster_enemy(self):
        self.other.traits.hp.base = 40
        self.other.traits.hp.current = 40
        field = self._taunted(self._field())
        request = default_attack_policy(self.monster, field)
        self.assertEqual(self._target_keys(request), [str(self.taunter.key)])

    def test_a_taunted_enemy_still_flees(self):
        # Stored HP at the flee boundary while the maximum stays full: the
        # taunt does not suppress the profile's own flee decision.
        self.monster.traits.hp.current = 1
        field = self._taunted(self._field())
        request = monster_behaviour_policy(
            self.monster, field, context=BattlefieldActionContext(field)
        )
        self.assertEqual(request.skill_key, FLEE_SKILL_KEY)

    def test_a_taunted_enemy_still_uses_its_area_action(self):
        self.assertEqual(
            BEHAVIOUR_PROFILES[AREA_ARCHETYPE].decision_mode, DecisionMode.LEGACY
        )
        self.monster.behaviour_tree = AREA_ARCHETYPE
        self.monster.db.skills = {"active": [AREA_SKILL.key], "passive": []}
        field = self._taunted(self._field())
        request = monster_behaviour_policy(
            self.monster, field, context=BattlefieldActionContext(field)
        )
        self.assertEqual(request.targets, "all-enemies")


class TauntSessionTests(EvenniaTestCase):
    """A committed Taunt constrains the enemy through one real session round."""

    def setUp(self):
        open_synthetic_scope(
            self,
            "skills",
            "elements",
            "items",
            "item_effect_profiles",
            extra=synth_innate_overlay(),
        )
        super().setUp()
        self.room = create_object(Room, key="taunt session room")
        self.player = _player("taunt commander")
        self.player.location = self.room
        self.monster = _monster("taunt mark", hp=100)
        self.monster.location = self.room
        self.companion = create_object(NPC, key="taunt companion", location=self.room)
        self.companion.race = self.player.race
        self.companion.apply_race_baseline()
        join_party(self.companion, self.player)

    def test_a_taunt_declaration_constrains_the_enemy_and_spends_no_resource(self):
        engage(self.player, self.monster)
        record = read_session(self.player)
        mp_before = self.player.traits.mp.current
        sp_before = self.player.traits.sp.current
        command = {
            "kind": "tactical",
            "payload": {"tactical_key": "taunt", "target_id": int(self.monster.pk)},
        }
        admitted = confirm_actor_command(
            self.player, record.session_id, 0, 0, self.player.pk, command
        )
        self.assertTrue(admitted["ok"], admitted)
        # The declaration costs no resource and advances no time.
        self.assertEqual(self.player.traits.mp.current, mp_before)
        self.assertEqual(self.player.traits.sp.current, sp_before)
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)

        companion_hp = self.companion.traits.hp.current
        player_hp = self.player.traits.hp.current
        with patch("world.rules.combat.damage.roll_d100", return_value=100):
            complete_party_draft(self.player, self.monster, admitted)
        self.assertEqual(read_session(self.player).rounds_elapsed, 1)
        # The enemy was constrained to the taunter: the untouched companion
        # took no damage while the taunter was attacked.
        self.assertEqual(self.companion.traits.hp.current, companion_hp)
        self.assertLess(self.player.traits.hp.current, player_hp)

    def test_two_taunters_of_one_enemy_both_spend_their_action(self):
        from dataclasses import replace

        from world.rules.combat_session import reconstruct_battlefield
        from world.rules.combat_session.rounds import (
            _draft_requests,
            _draft_taunt_declarations,
        )

        engage(self.player, self.monster)
        record = read_session(self.player)
        battlefield = reconstruct_battlefield(self.player, record)
        taunt = {
            "kind": "tactical",
            "payload": {"tactical_key": "taunt", "target_id": int(self.monster.pk)},
        }
        record = replace(
            record,
            draft_entries={self.player.pk: taunt, self.companion.pk: taunt},
        )
        requests = _draft_requests(record, battlefield)
        # Both declarations are consumed as their actors' action, whatever the
        # initiative ranking later decides; neither takes an ordinary action.
        self.assertNotIn(self.player.pk, requests)
        self.assertNotIn(self.companion.pk, requests)
        self.assertEqual(
            _draft_taunt_declarations(record, battlefield),
            {
                str(self.player.key): str(self.monster.key),
                str(self.companion.key): str(self.monster.key),
            },
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
