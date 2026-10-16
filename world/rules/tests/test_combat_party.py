"""Companion joint-combat integration tests (party-combat).

Covers the party-combat contract end to end: co-located living companions join
the session's allied team on ``engage``, act at most once per round from their
own selected command through the complete draft's provider (never fleeing,
never consuming the player's selected request), cannot die (per-entity
nonlethal knockout floored at 1 HP and
marked on the battlefield in the same commit), stay knocked out across rebuilds
and re-engagements until clock-driven regen lifts HP above 1, are excluded from
all target selection while knocked out, and settle player-centric terminal
rules (player defeat ends the session even with companions standing). Also
pins the battlefield-shaped snapshot/restore covering ``fled`` AND
``knocked_out`` with its commit rollback.
"""

from tools.spec_traceability import covers_requirement

from pathlib import Path
import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.rules.action import (
    ActionRequest,
    PendingEffect,
    RejectReason,
    _commit,
    _snapshot_touched,
    _restore_touched,
)
from world.rules.clock import _settle_gauge_regen
from world.rules.combat import Battlefield, _handle_damage, run_round
from world.rules.combat_session import (
    _context_for,
    BASIC_ATTACK_KEY,
    PARTY_EXIT_RETREAT,
    authorize_combat_actor,
    CombatSessionError,
    SessionReason,
    confirm_party_exit,
    engage,
    engage_group,
    forfeit,
    read_session,
    reconstruct_battlefield,
    request_party_exit,
    submit_player_action,
    submit_player_item_use,
)
from world.rules.combat_session.policies import _party_round_provider
from world.rules.disengage import FLEE_SKILL_KEY
from world.rules.monster_behaviour import monster_behaviour_policy
from world.rules.party import join_party, party_ids
from world.rules.skip_safety import (
    SkipRejectReason,
    _BATTLEFIELDS,
    evaluate_skip_safety,
)
from world.rules.targeting import expand_target_shorthand

from .combat_fixtures import FakeEntity
from .combat_fixtures import BattlefieldIsolation, grant_lineage
from ._combat_session_helpers import (
    _behaviour_archetype_key,
    _monster_tier_key,
    _race_key,
    open_synthetic_scope,
    synth_innate_overlay,
)
from world.tests.synthetic_data import SYNTH_SKILLS

# Fixture mechanics resolve through the synthetic kit: the spell and martial
# carriers are kit rows, the delivered-cast element is the kit element, and
# race/threshold keys arrive through runtime probes (identical values outside
# a scope, kit rows inside one). Monster rounds execute against the LIVE tier
# vocabulary — monster_tiers is deliberately never scoped here.
_T_CAST = SYNTH_SKILLS["t_ember_burst"].key
_T_MARTIAL = SYNTH_SKILLS["t_cinder_cleave"].key
_T_DAMAGE_EFFECT = "damage:" + SYNTH_SKILLS["t_ember_burst"].element.key + ":magic"
_SCOPE_LOGICALS = ("skills", "elements", "races", "subraces", "static_tiers")


def _player(key="combat party player"):
    player = create_object(PlayerCharacter, key=key)
    player.race = _race_key()
    player.apply_race_baseline()
    # Static magic_power raised so element-gated kit casts pass tuning.
    player.traits.magic_power.base = 30
    grant_lineage(player, [_T_CAST, _T_MARTIAL])
    return player


def _monster(key="goblin", hp=100, atk=10, agility=10):
    monster = create_object(Monster, key=key)
    monster.threat_tier = _monster_tier_key()
    monster.behaviour_tree = _behaviour_archetype_key()
    monster.apply_monster_tier("floor")
    monster.traits.hp.base = hp
    monster.traits.hp.current = hp
    monster.traits.atk_phys.base = atk
    monster.traits.agility.base = agility
    return monster


def _companion(player, key, hp=100, agility=10):
    npc = create_object(NPC, key=key, location=player.location)
    npc.race = _race_key()
    npc.apply_race_baseline()
    npc.traits.hp.base = hp
    npc.traits.hp.current = hp
    npc.traits.agility.base = agility
    join_party(npc, player)
    return npc


def _entry_kinds(logs):
    return [entry.kind for log in logs for entry in log.entries]


def _damage_entries(logs):
    return [
        entry
        for log in logs
        for entry in log.entries
        if entry.kind == "damage"
    ]


class EngagePartyTests(BattlefieldIsolation, EvenniaTestCase):
    """Task 1.4: allied-team collection on engage."""

    def setUp(self):
        open_synthetic_scope(
            self, *_SCOPE_LOGICALS, extra=synth_innate_overlay()
        )
        super().setUp()
        from world.quests.catalog import register_catalog

        register_catalog()
        self.room = create_object(Room, key="combat party arena")
        self.player = _player()
        self.player.location = self.room
        self.monster = _monster("party goblin", hp=500)
        self.monster.location = self.room

    @covers_requirement("player-combat-session::engage-creates-one-persistent-local-combat-session")
    @covers_requirement("party-system::companions-fight-as-allies-in-the-player-s-combat-session")
    def test_co_located_living_companions_join_the_allied_team(self):
        first = _companion(self.player, "第一")
        second = _companion(self.player, "第二")
        result = engage(self.player, self.monster)
        self.assertEqual(
            result["record"].player_ids,
            (self.player.pk, first.pk, second.pk),
        )
        battlefield = reconstruct_battlefield(
            self.player, read_session(self.player)
        )
        self.assertIn(str(first.key), battlefield.roster)
        self.assertIn(str(second.key), battlefield.roster)
        self.assertEqual(party_ids(self.player), [first.pk, second.pk])

    @covers_requirement("player-combat-session::engage-creates-one-persistent-local-combat-session")
    @covers_requirement("party-system::companions-fight-as-allies-in-the-player-s-combat-session")
    def test_distant_dead_or_knocked_out_companions_do_not_join(self):
        other_room = create_object(Room, key="distant room")
        far = _companion(self.player, "遠方")
        far.location = other_room
        dead = _companion(self.player, "陣亡", hp=0)
        floored = _companion(self.player, "倒下", hp=50)
        floored.traits.hp.current = 1
        result = engage(self.player, self.monster)
        self.assertEqual(result["record"].player_ids, (self.player.pk,))
        for companion in (far, dead, floored):
            self.assertNotIn(int(companion.pk), result["record"].player_ids)

    @covers_requirement("player-combat-session::engage-creates-one-persistent-local-combat-session")
    def test_empty_party_engage_behaves_exactly_as_before(self):
        result = engage(self.player, self.monster)
        self.assertEqual(result["record"].player_ids, (self.player.pk,))
        with patch("world.rules.combat.battlefield.roll_d100", return_value=100), patch("world.rules.combat.damage.roll_d100", return_value=100), patch("world.rules.combat.rounds.roll_d100", return_value=100):
            outcome = submit_player_action(
                self.player, _T_CAST, [self.monster]
            )
        self.assertIn(outcome["outcome"], ("round", "victory", "defeat"))
        self.assertEqual(read_session(self.player).rounds_elapsed, 1)

    @covers_requirement("player-combat-session::final-member-confirmation-automatically-submits-one-complete-ordinary-round")
    def test_each_participant_receives_at_most_one_request_per_round(self):
        first = _companion(self.player, "第一", hp=500)
        second = _companion(self.player, "第二", hp=500)
        self.player.traits.hp.base = 500
        self.player.traits.hp.current = 500
        monster_a = _monster("狼一", hp=500, atk=20)
        monster_a.location = self.room
        monster_b = _monster("狼二", hp=500, atk=20)
        monster_b.location = self.room
        engage(self.player, monster_a)
        record = read_session(self.player)
        from world.rules.combat_session import _persist, from_storage, to_storage

        record = from_storage(
            {
                **to_storage(record),
                "enemy_ids": [monster_a.pk, monster_b.pk],
            }
        )
        _persist(self.player, record)
        battlefield = reconstruct_battlefield(self.player, record)
        context = _context_for(battlefield, record)
        request = ActionRequest(
            self.player, _T_CAST, [monster_a], context
        )
        # The complete draft's provider: each participant is provisioned at
        # most one slot per round, and an interactive ally without a selected
        # command receives no request at all.
        provider = _party_round_provider(
            {int(self.player.pk): request}, battlefield, record
        )
        calls: dict[str, int] = {}

        def counting(entity, field):
            calls[str(entity.key)] = calls.get(str(entity.key), 0) + 1
            return provider(entity, field)

        with patch("world.rules.combat.battlefield.roll_d100", return_value=100), patch("world.rules.combat.damage.roll_d100", return_value=100), patch("world.rules.combat.rounds.roll_d100", return_value=100):
            run_round(battlefield, counting)
        for key in (self.player.key, first.key, second.key, monster_a.key, monster_b.key):
            self.assertEqual(calls.get(str(key), 0), 1, key)

    @covers_requirement("player-combat-session::engage-creates-one-persistent-local-combat-session")
    @covers_requirement("party-system::companions-fight-as-allies-in-the-player-s-combat-session")
    def test_freely_targetable_skill_can_select_companion_with_penalty(self):
        companion = _companion(self.player, "同伴")
        engage(self.player, self.monster)
        # ANY damage skills accept a companion as an explicit target; the
        # friendly-fire penalty contract applies instead of a faction
        # rejection (friendly-fire reachability).
        from world.rules.affinity import AffinitySource, apply_affinity_change

        apply_affinity_change(
            companion, self.player, AffinitySource.QUEST_COMPLETION, 10
        )
        with patch("world.rules.combat.battlefield.roll_d100", return_value=100), patch("world.rules.combat.damage.roll_d100", return_value=100), patch("world.rules.combat.rounds.roll_d100", return_value=100):
            result = submit_player_action(
                self.player, _T_CAST, [companion]
            )
            self.assertEqual(result["outcome"], "draft")
            result = submit_player_action(self.player, BASIC_ATTACK_KEY, [self.monster], commanded_actor=companion)
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(read_session(self.player).rounds_elapsed, 1)
        self.assertEqual(companion.relations.affinity_for(self.player), 9)

    @covers_requirement("player-combat-session::engage-creates-one-persistent-local-combat-session")
    @covers_requirement("party-system::companions-fight-as-allies-in-the-player-s-combat-session")
    def test_opposing_combatant_can_target_companion(self):
        companion = _companion(self.player, "誘餌", hp=50)
        monster = _monster("追擊者", hp=500, atk=20, agility=100)
        monster.location = self.room
        engage(self.player, monster)
        record = read_session(self.player)
        battlefield = reconstruct_battlefield(self.player, record)
        context = _context_for(battlefield, record)
        request = ActionRequest(
            self.player, _T_CAST, [monster], context
        )
        provider = _party_round_provider(
            {int(self.player.pk): request}, battlefield, record
        )
        with patch("world.rules.combat.battlefield.roll_d100", return_value=100), patch("world.rules.combat.damage.roll_d100", return_value=100), patch("world.rules.combat.rounds.roll_d100", return_value=100):
            logs = run_round(battlefield, provider)
        targets = [entry.target for entry in _damage_entries(logs)]
        self.assertIn(str(companion.key), targets)

    @covers_requirement("party-system::companions-fight-as-allies-in-the-player-s-combat-session")
    def test_companion_fallback_policy_attacks_the_opposing_team(self):
        companion = _companion(self.player, "戰友")
        engage(self.player, self.monster)
        battlefield = reconstruct_battlefield(
            self.player, read_session(self.player)
        )
        request = monster_behaviour_policy(companion, battlefield)
        self.assertIsNotNone(request)
        self.assertNotEqual(request.skill_key, FLEE_SKILL_KEY)
        foe_team = next(
            team for team in battlefield.teams if team != battlefield.team_of(str(companion.key))
        )
        for target in request.targets:
            self.assertIn(str(target.key), battlefield.teams[foe_team])

    @covers_requirement("party-system::companions-fight-as-allies-in-the-player-s-combat-session")
    def test_companion_round_never_emits_a_flee_entry(self):
        companion = _companion(self.player, "堅守", hp=200, agility=500)
        monster = _monster("慢狼", hp=500, atk=20, agility=10)
        monster.location = self.room
        engage(self.player, monster)
        record = read_session(self.player)
        battlefield = reconstruct_battlefield(self.player, record)
        context = _context_for(battlefield, record)
        request = ActionRequest(self.player, _T_CAST, [monster], context)
        # Each interactive ally acts from its own selected command: the
        # companion's commanded action is still never a flee request.
        companion_request = ActionRequest(companion, BASIC_ATTACK_KEY, [monster], context)
        provider = _party_round_provider(
            {int(self.player.pk): request, int(companion.pk): companion_request},
            battlefield,
            record,
        )
        with patch("world.rules.combat.battlefield.roll_d100", return_value=100), patch("world.rules.combat.damage.roll_d100", return_value=100), patch("world.rules.combat.rounds.roll_d100", return_value=100):
            logs = run_round(battlefield, provider)
        companion_damage = [
            entry
            for entry in _damage_entries(logs)
            if entry.actor == str(companion.key)
        ]
        self.assertTrue(companion_damage)
        self.assertNotIn(
            "disengage_attempt",
            [
                entry.kind
                for log in logs
                for entry in log.entries
                if entry.actor == str(companion.key)
            ],
        )
        self.assertNotIn(str(companion.key), battlefield.fled)


class KnockoutStateTests(BattlefieldIsolation, EvenniaTestCase):
    """Tasks 2.7 and 3.3: per-entity nonlethal knockout as battlefield state."""

    def setUp(self):
        open_synthetic_scope(
            self, *_SCOPE_LOGICALS, extra=synth_innate_overlay()
        )
        super().setUp()
        self.room = create_object(Room, key="knockout arena")
        self.player = _player()
        self.player.location = self.room
        self.player.traits.hp.base = 500
        self.player.traits.hp.current = 500
        self.companion = _companion(self.player, "軟腳蝦", hp=50)
        self.monster = _monster("痛擊狼", hp=500, atk=30, agility=20)
        self.monster.location = self.room

    def _run_one_round(self):
        record = read_session(self.player)
        battlefield = reconstruct_battlefield(self.player, record)
        context = _context_for(battlefield, record)
        request = ActionRequest(
            self.player, _T_CAST, [self.monster], context
        )
        provider = _party_round_provider(
            {int(self.player.pk): request}, battlefield, record
        )
        with patch("world.rules.combat.battlefield.roll_d100", return_value=100), patch("world.rules.combat.damage.roll_d100", return_value=100), patch("world.rules.combat.rounds.roll_d100", return_value=100):
            logs = run_round(battlefield, provider)
        from dataclasses import replace
        from world.rules.combat_session import _persist
        from world.rules.combat_session.rounds import _knocked_out_ids

        _persist(self.player, replace(record, knocked_out_ids=_knocked_out_ids(logs, battlefield)))
        return battlefield, logs

    @covers_requirement("action-resolution-pipeline::nonlethal-policy-transforms-lethal-projection-before-eventlog-planners")
    @covers_requirement("party-system::knocked-out-companions-are-persistent-battlefield-state-and-can-never-die")
    def test_companion_lethal_crossing_floors_hp_and_marks_knockout(self):
        engage(self.player, self.monster)
        battlefield, logs = self._run_one_round()
        self.assertEqual(self.companion.traits.hp.current, 1)
        self.assertIn(str(self.companion.key), battlefield.knocked_out)
        kinds = _entry_kinds(logs)
        self.assertIn("target_knocked_out", kinds)
        self.assertNotIn("target_defeated", kinds)
        knockout_entries = [
            entry
            for log in logs
            for entry in log.entries
            if entry.kind == "target_knocked_out"
        ]
        self.assertEqual(
            knockout_entries[0].data["target_id"],
            int(self.companion.pk),
        )

    @covers_requirement("action-resolution-pipeline::nonlethal-policy-transforms-lethal-projection-before-eventlog-planners")
    def test_hostile_kills_stay_lethal_in_the_same_session(self):
        self.monster.traits.hp.base = 1
        self.monster.traits.hp.current = 1
        engage(self.player, self.monster)
        battlefield, logs = self._run_one_round()
        self.assertEqual(self.monster.traits.hp.current, 0)
        kinds = _entry_kinds(logs)
        self.assertIn("target_defeated", kinds)
        self.assertNotIn(str(self.monster.key), battlefield.knocked_out)

    @covers_requirement("party-system::knocked-out-companions-are-persistent-battlefield-state-and-can-never-die")
    def test_knocked_out_companion_receives_no_policy_request(self):
        engage(self.player, self.monster)
        self._run_one_round()
        real_policy = monster_behaviour_policy
        calls: list[str] = []

        def spy(entity, field, **kwargs):
            calls.append(str(entity.key))
            return real_policy(entity, field, **kwargs)

        with (
            patch(
                "world.rules.combat_session.policies.monster_behaviour_policy",
                side_effect=spy,
            ),
            patch("world.rules.combat.battlefield.roll_d100", return_value=100),
            patch("world.rules.combat.damage.roll_d100", return_value=100),
            patch("world.rules.combat.rounds.roll_d100", return_value=100),
        ):
            result = submit_player_action(
                self.player, _T_CAST, [self.monster]
            )
        self.assertEqual(result["outcome"], "round")
        self.assertNotIn(str(self.companion.key), calls)
        self.assertIn(str(self.monster.key), calls)

    @covers_requirement("party-system::knocked-out-companions-are-persistent-battlefield-state-and-can-never-die")
    def test_knocked_out_companion_is_excluded_from_all_shorthands(self):
        engage(self.player, self.monster)
        record = read_session(self.player)
        battlefield = reconstruct_battlefield(self.player, record)
        battlefield.knocked_out.add(str(self.companion.key))
        context = _context_for(battlefield, record)
        for shorthand in ("all-allies", "all-enemies", "all"):
            candidates = expand_target_shorthand(
                self.player, context, shorthand
            )
            self.assertNotIn(self.companion, candidates)
        self.assertIn(self.player, expand_target_shorthand(
            self.player, context, "all-allies"
        ))

    @covers_requirement("party-system::knocked-out-companions-are-persistent-battlefield-state-and-can-never-die")
    def test_knocked_out_companion_is_never_selected_by_the_opposing_team(self):
        engage(self.player, self.monster)
        battlefield = reconstruct_battlefield(
            self.player, read_session(self.player)
        )
        battlefield.knocked_out.add(str(self.companion.key))
        request = monster_behaviour_policy(self.monster, battlefield)
        self.assertIsNotNone(request)
        for target in request.targets:
            self.assertNotEqual(str(target.key), str(self.companion.key))
            self.assertEqual(
                str(target.key),
                str(self.player.key),
            )

    def test_knocked_out_companion_is_never_a_flee_pursuer(self):
        from world.rules.disengage import (
            _adjusted_agility,
            _fastest_pursuer_agility,
        )

        companion = _companion(self.player, "倒下追兵", hp=50, agility=500)
        engage(self.player, self.monster)
        battlefield = reconstruct_battlefield(
            self.player, read_session(self.player)
        )
        battlefield.knocked_out.add(str(companion.key))
        self.assertEqual(
            _fastest_pursuer_agility(battlefield, self.monster),
            _adjusted_agility(self.companion),
        )

    @covers_requirement("party-system::knocked-out-companions-are-persistent-battlefield-state-and-can-never-die")
    def test_knockout_state_survives_a_battlefield_rebuild(self):
        engage(self.player, self.monster)
        submit_player_action(self.player, BASIC_ATTACK_KEY, [self.monster], commanded_actor=self.companion)
        with patch("world.rules.combat.battlefield.roll_d100", return_value=100), patch("world.rules.combat.damage.roll_d100", return_value=100), patch("world.rules.combat.rounds.roll_d100", return_value=100):
            submit_player_action(self.player, _T_CAST, [self.monster])
        record = read_session(self.player)
        self.assertIn(int(self.companion.pk), record.knocked_out_ids)
        rebuilt = reconstruct_battlefield(self.player, record)
        self.assertIn(str(self.companion.key), rebuilt.knocked_out)

    @covers_requirement("party-system::knocked-out-companions-are-persistent-battlefield-state-and-can-never-die")
    def test_knocked_out_companion_cannot_reengage_before_recovery(self):
        # Stop clock-driven regen so the settlement never lifts the companion
        # off the nonlethal floor before the re-engagement.
        self.companion.traits.hp.rate = 0
        engage(self.player, self.monster)
        self._run_one_round()
        result = forfeit(self.player)
        self.assertEqual(result["outcome"], "defeat")
        self.assertEqual(self.companion.traits.hp.current, 1)
        new_result = engage(self.player, self.monster)
        self.assertEqual(new_result["record"].player_ids, (self.player.pk,))

    @covers_requirement("player-combat-session::combat-time-settles-once-at-terminal-session-outcome")
    @covers_requirement("party-system::combat-settlement-includes-companions-in-the-regen-scope")
    def test_terminal_settlement_regenerates_knocked_out_companion(self):
        # The terminal settlement regenerates the whole living roster
        # (fix-combat-session-roster-and-overwhelm D1): the first round
        # floors the companion at 1 HP, the forfeit settlement advances the
        # round's combat seconds and lifts the companion above the nonlethal
        # floor, and a later engagement includes it again.
        engage(self.player, self.monster)
        submit_player_action(self.player, BASIC_ATTACK_KEY, [self.monster], commanded_actor=self.companion)
        with patch("world.rules.combat.battlefield.roll_d100", return_value=100), patch("world.rules.combat.damage.roll_d100", return_value=100), patch("world.rules.combat.rounds.roll_d100", return_value=100):
            result = submit_player_action(
                self.player, _T_CAST, [self.monster]
            )
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(self.companion.traits.hp.current, 1)
        result = forfeit(self.player)
        self.assertEqual(result["outcome"], "defeat")
        self.assertGreater(self.companion.traits.hp.current, 1)
        new_result = engage(self.player, self.monster)
        self.assertEqual(
            new_result["record"].player_ids,
            (self.player.pk, self.companion.pk),
        )

    @covers_requirement("party-system::knocked-out-companions-are-persistent-battlefield-state-and-can-never-die")
    @covers_requirement("party-system::combat-terminal-rules-are-player-centric")
    def test_recovery_above_1_hp_rejoins_a_later_engagement(self):
        engage(self.player, self.monster)
        self._run_one_round()
        forfeit(self.player)
        _settle_gauge_regen([self.companion], 60)
        self.assertGreater(self.companion.traits.hp.current, 1)
        new_result = engage(self.player, self.monster)
        self.assertEqual(
            new_result["record"].player_ids,
            (self.player.pk, self.companion.pk),
        )
        self.assertEqual(
            party_ids(self.player), [int(self.companion.pk)]
        )


class TerminalAndCleanupTests(BattlefieldIsolation, EvenniaTestCase):
    """Task 4.3: player-centric terminal rules and participant cleanup."""

    def setUp(self):
        open_synthetic_scope(
            self, *_SCOPE_LOGICALS, extra=synth_innate_overlay()
        )
        super().setUp()
        self.room = create_object(Room, key="terminal arena")
        self.player = _player()
        self.player.location = self.room
        self.monster = _monster("決勝狼", hp=500, atk=100, agility=15)
        self.monster.location = self.room

    @covers_requirement("party-system::combat-terminal-rules-are-player-centric")
    def test_player_defeat_settles_with_companions_standing(self):
        self.player.traits.hp.base = 1
        self.player.traits.hp.current = 1
        companion = _companion(self.player, "仍站著", hp=100)
        engage(self.player, self.monster)
        submit_player_action(self.player, BASIC_ATTACK_KEY, [self.monster], commanded_actor=companion)
        with patch("world.rules.combat.battlefield.roll_d100", return_value=100), patch("world.rules.combat.damage.roll_d100", return_value=100), patch("world.rules.combat.rounds.roll_d100", return_value=100):
            result = submit_player_action(
                self.player, _T_CAST, [self.monster]
            )
        self.assertEqual(result["outcome"], "defeat")
        self.assertEqual(result["rounds_elapsed"], 1)
        defeated = [
            entry
            for log in result["logs"]
            for entry in log.entries
            if entry.kind == "target_defeated"
        ]
        self.assertEqual(
            defeated[0].data["target_id"], int(self.player.pk)
        )
        self.assertGreater(companion.traits.hp.current, 0)
        self.assertIsNone(self.player.db.active_combat)
        self.assertFalse(any(
            str(entity.pk) in _BATTLEFIELDS
            for entity in (self.player, companion, self.monster)
        ))

    @covers_requirement("party-system::combat-terminal-rules-are-player-centric")
    def test_victory_requires_only_the_foes_team_to_be_gone(self):
        self.player.traits.agility.base = 50
        self.player.traits.magic_power.base = 200
        companion = _companion(self.player, "觀戰者", hp=100)
        self.monster.traits.hp.base = 100
        self.monster.traits.hp.current = 100
        self.monster.traits.agility.base = 5
        engage(self.player, self.monster)
        submit_player_action(self.player, BASIC_ATTACK_KEY, [self.monster], commanded_actor=companion)
        with patch("world.rules.combat.battlefield.roll_d100", return_value=100), patch("world.rules.combat.damage.roll_d100", return_value=100), patch("world.rules.combat.rounds.roll_d100", return_value=100):
            result = submit_player_action(
                self.player, _T_CAST, [self.monster]
            )
        self.assertEqual(result["outcome"], "victory")
        self.assertEqual(result["rounds_elapsed"], 1)
        self.assertGreater(self.player.traits.hp.current, 0)
        self.assertGreater(companion.traits.hp.current, 0)
        self.assertIsNone(self.player.db.active_combat)

    @covers_requirement("party-system::combat-terminal-rules-are-player-centric")
    def test_knocked_out_companion_does_not_end_the_session(self):
        companion = _companion(self.player, "先倒下", hp=50)
        engage(self.player, self.monster)
        submit_player_action(self.player, BASIC_ATTACK_KEY, [self.monster], commanded_actor=companion)
        with patch("world.rules.combat.battlefield.roll_d100", return_value=100), patch("world.rules.combat.damage.roll_d100", return_value=100), patch("world.rules.combat.rounds.roll_d100", return_value=100):
            result = submit_player_action(
                self.player, _T_CAST, [self.monster]
            )
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(companion.traits.hp.current, 1)
        record = read_session(self.player)
        self.assertIn(int(companion.pk), record.knocked_out_ids)
        self.assertTrue(is_active_session(self.player))

    def test_missing_participant_cleanup_unregisters_every_survivor(self):
        companion = _companion(self.player, "留下來", hp=100)
        engage(self.player, self.monster)
        for entity in (self.player, companion, self.monster):
            self.assertIn(str(entity.pk), _BATTLEFIELDS)
        self.monster.delete()
        result = forfeit(self.player)
        self.assertEqual(result["outcome"], "defeat")
        for entity in (self.player, companion, self.monster):
            self.assertNotIn(str(entity.pk), _BATTLEFIELDS)
        self.assertIsNone(self.player.db.active_combat)

    def test_a_deleted_participant_s_key_never_blocks_a_replacement(self):
        companion = _companion(self.player, "替身先例", hp=100)
        engage(self.player, self.monster)
        monster_key = str(self.monster.key)
        self.monster.delete()
        forfeit(self.player)
        replacement = _monster(monster_key, hp=100)
        replacement.location = self.room
        from world.rules.skip_safety import evaluate_skip_safety

        self.assertNotEqual(
            evaluate_skip_safety(replacement),
            SkipRejectReason.IN_COMBAT,
        )


def is_active_session(actor) -> bool:
    from world.rules.combat_session import is_in_active_session

    return is_in_active_session(actor)


class MultiTargetKnockoutProjectionTests(unittest.TestCase):
    """Multi-target damage marks each protected target exactly once."""

    @covers_requirement("action-resolution-pipeline::nonlethal-policy-transforms-lethal-projection-before-eventlog-planners")
    def test_area_damage_floors_and_marks_each_protected_target_once(self):
        actor = FakeEntity("caster", atk_phys=20)
        first = FakeEntity("第一", hp=5)
        second = FakeEntity("第二", hp=5)
        field = Battlefield(
            {
                "party": frozenset({"caster", "第一", "第二"}),
                "foes": frozenset({"foe"}),
            },
            {
                "caster": actor,
                "第一": first,
                "第二": second,
                "foe": FakeEntity("foe"),
            },
        )
        with (
            patch("world.rules.combat.damage.roll_d100", return_value=100),
            patch(
                "world.rules.combat.damage.evaluate_combat_modifiers",
                return_value={},
            ),
            patch(
                "world.rules.combat.battlefield.evaluate_combat_modifiers",
                return_value={},
            ),
        ):
            pending = _handle_damage(
                actor,
                [first, second],
                _T_DAMAGE_EFFECT,
                {
                    "battlefield": field,
                    "nonlethal_keys": frozenset({"第一", "第二"}),
                },
                1.0,
            )
        for effect in pending:
            effect.apply()
        self.assertEqual(first.traits.hp.value, 1)
        self.assertEqual(second.traits.hp.value, 1)
        self.assertEqual(field.knocked_out, {"第一", "第二"})


class BattlefieldCommitSurfaceTests(EvenniaTestCase):
    """battlefield-commit-surface: ``fled`` AND ``knocked_out`` snapshot/restore."""

    def _field(self, entity):
        return Battlefield(
            {
                "party": frozenset({str(entity.key)}),
                "foes": frozenset({"pursuer"}),
            },
            {str(entity.key): entity, "pursuer": FakeEntity("pursuer")},
        )

    @covers_requirement("battlefield-commit-surface::a-battlefield-shaped-object-is-snapshotted-and-restored-by-shape-not-by-explicit")
    def test_snapshot_captures_and_restores_both_sets(self):
        entity = create_object(PlayerCharacter, key="snapshot host")
        field = self._field(entity)
        field.fled.add("pursuer")
        field.knocked_out.add(str(entity.key))
        snapshot = _snapshot_touched(field, frozenset())
        self.assertEqual(
            snapshot["battlefield"],
            (frozenset({"pursuer"}), frozenset({str(entity.key)})),
        )
        field.fled.clear()
        field.knocked_out.clear()
        _restore_touched(field, snapshot, frozenset())
        self.assertEqual(field.fled, {"pursuer"})
        self.assertEqual(field.knocked_out, {str(entity.key)})

    @covers_requirement("battlefield-commit-surface::a-commit-failure-rolls-back-a-battlefield-mutation-exactly-as-it-rolls-back-an-entity")
    def test_knockout_mark_is_rolled_back_with_the_commit(self):
        entity = create_object(PlayerCharacter, key="rollback host")
        entity.race = _race_key()
        entity.apply_race_baseline()
        field = self._field(entity)
        effects = [
            PendingEffect(
                field,
                "knocked_out_mark|actor",
                frozenset(),
                lambda: field.knocked_out.add(str(entity.key)),
            ),
            PendingEffect(
                field,
                "synthetic",
                frozenset(),
                lambda: (_ for _ in ()).throw(RuntimeError("injected")),
            ),
        ]
        with self.assertRaises(Exception) as caught:
            _commit(effects, char="tester", action="test_skill")
        self.assertIs(caught.exception.reason, RejectReason.COMMIT_FAILED)
        self.assertEqual(field.knocked_out, set())
        self.assertEqual(field.fled, set())

    @covers_requirement(
        "battlefield-commit-surface::a-commit-failure-rolls-back-a-battlefield-mutation-exactly-as-it-rolls-back-an-entity",
        "action-resolution-pipeline::resolution-is-atomic-a-failure-at-any-step-leaves-zero-state-mutated",
    )
    def test_entity_and_battlefield_restore_in_one_commit(self):
        entity = create_object(PlayerCharacter, key="mixed host")
        entity.race = _race_key()
        entity.apply_race_baseline()
        before = entity.traits.atk_phys.value
        field = self._field(entity)
        field.knocked_out.add(str(entity.key))
        effects = [
            PendingEffect(
                entity,
                "damage|{key}|100|1|10".format(key=str(entity.key)),
                frozenset({"traits"}),
                lambda: setattr(entity.traits.atk_phys, "value", before + 10),
            ),
            PendingEffect(
                field,
                "knocked_out_mark|pursuer",
                frozenset(),
                lambda: field.knocked_out.add("pursuer"),
            ),
            PendingEffect(
                field,
                "synthetic",
                frozenset(),
                lambda: (_ for _ in ()).throw(RuntimeError("injected")),
            ),
        ]
        with self.assertRaises(Exception) as caught:
            _commit(effects, char="tester", action="test_skill")
        self.assertIs(caught.exception.reason, RejectReason.COMMIT_FAILED)
        self.assertEqual(entity.traits.atk_phys.value, before)
        self.assertEqual(field.knocked_out, {str(entity.key)})

    def test_action_module_uses_shape_dispatch_for_both_sets(self):
        # The snapshot/restore mechanism moved to the action package's
        # transaction module; the shape-dispatch contract lives with it.
        source = (
            Path(__file__).parents[1] / "action" / "transaction.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("from world.rules.combat import Battlefield", source)
        self.assertNotIn("isinstance(context, Battlefield", source)
        self.assertIn('"knocked_out"', source)


class PartyActorCommandsTests(BattlefieldIsolation, EvenniaTestCase):
    """Actor commands, commander authorization, and actor-scoped skill and item use."""

    def setUp(self):
        open_synthetic_scope(
            self, *_SCOPE_LOGICALS, "items", "item_effect_profiles", extra=synth_innate_overlay()
        )
        super().setUp()
        from world.quests.catalog import register_catalog

        register_catalog()
        self.room = create_object(Room, key="combat party actor arena")
        self.player = _player()
        self.player.location = self.room
        self.monster = _monster("party actor goblin", hp=500)
        self.monster.location = self.room

    @covers_requirement(
        "player-combat-session::commander-may-select-only-currently-controllable-allied-actors"
    )
    def test_commander_authorization_rejects_enemy_and_other_party(self):
        companion = _companion(self.player, "同行夥伴", hp=100)
        other_player = create_object(PlayerCharacter, key="路人玩家")
        other_player.location = self.room
        other_companion = _companion(other_player, "別人的夥伴", hp=100)
        engage(self.player, self.monster)

        # 1. Commander choosing enemy
        with self.assertRaises(CombatSessionError) as caught:
            submit_player_action(
                self.player,
                BASIC_ATTACK_KEY,
                [self.monster],
                commanded_actor=self.monster,
            )
        self.assertEqual(caught.exception.args[0], SessionReason.FORBIDDEN_ACTOR)

        # 2. Commander choosing another player's companion
        with self.assertRaises(CombatSessionError) as caught:
            submit_player_action(
                self.player,
                BASIC_ATTACK_KEY,
                [self.monster],
                commanded_actor=other_companion,
            )
        self.assertEqual(caught.exception.args[0], SessionReason.FORBIDDEN_ACTOR)

        # 3. Commander account puppet stays unchanged
        self.assertIsNone(self.player.account)

    @covers_requirement(
        "player-combat-session::commander-may-select-only-currently-controllable-allied-actors"
    )
    def test_commander_authorization_rejects_stale_moved_down_or_forbidden_actor(self):
        companion = _companion(self.player, "狀態同伴", hp=100)
        engage(self.player, self.monster)
        record = read_session(self.player)
        field = reconstruct_battlefield(self.player, record)

        # Moved companion
        companion.location = None
        with self.assertRaises(CombatSessionError) as caught:
            authorize_combat_actor(self.player, companion, record, field)
        self.assertEqual(caught.exception.args[0], SessionReason.FORBIDDEN_ACTOR)
        companion.location = self.player.location

        # Fled companion
        field.fled.add(str(companion.key))
        with self.assertRaises(CombatSessionError) as caught:
            authorize_combat_actor(self.player, companion, record, field)
        self.assertEqual(caught.exception.args[0], SessionReason.FORBIDDEN_ACTOR)
        field.fled.clear()

        # Knocked out companion
        field.knocked_out.add(str(companion.key))
        with self.assertRaises(CombatSessionError) as caught:
            authorize_combat_actor(self.player, companion, record, field)
        self.assertEqual(caught.exception.args[0], SessionReason.FORBIDDEN_ACTOR)
        field.knocked_out.clear()

        # Defeated companion (HP 0)
        companion.traits.hp.current = 0
        with self.assertRaises(CombatSessionError) as caught:
            authorize_combat_actor(self.player, companion, record, field)
        self.assertEqual(caught.exception.args[0], SessionReason.FORBIDDEN_ACTOR)
        companion.traits.hp.current = 100

        # Action-forbidden companion (actions_per_turn == 0)
        with patch("world.rules.combat_session.battlefield.evaluate_combat_modifiers_no_create", return_value={"actions_per_turn": 0}):
            with self.assertRaises(CombatSessionError) as caught:
                authorize_combat_actor(self.player, companion, record, field)
            self.assertEqual(caught.exception.args[0], SessionReason.FORBIDDEN_ACTOR)

    @covers_requirement(
        "player-combat-session::all-personal-skill-choices-and-costs-are-actor-scoped"
    )
    def test_companion_skill_choices_self_binding_and_resource_deduction(self):
        companion = _companion(self.player, "魔法同伴", hp=100)
        companion.traits.mp.base = 50
        companion.traits.mp.current = 50
        grant_lineage(companion, [_T_CAST])
        self.player.traits.mp.base = 50
        self.player.traits.mp.current = 50
        # Player does not know _T_CAST
        self.player.db.skills = ()

        engage(self.player, self.monster)
        from world.rules.combat_view import build_combat_view

        # 1. View choices for companion
        view = build_combat_view(self.player, for_actor=companion)
        skill_keys = [s.key for s in view.skills]
        self.assertIn(_T_CAST, skill_keys)

        # 2. View choices for commander lacks companion skill
        commander_view = build_combat_view(self.player)
        self.assertNotIn(_T_CAST, [s.key for s in commander_view.skills])

        # 3. Companion executes _T_CAST
        submit_player_action(self.player, BASIC_ATTACK_KEY, [self.monster])
        result = submit_player_action(
            self.player,
            _T_CAST,
            [self.monster],
            commanded_actor=companion,
        )
        self.assertEqual(result["outcome"], "round")
        # Companion MP deducted, player MP untouched
        self.assertLess(companion.traits.mp.current, 50)
        self.assertEqual(self.player.traits.mp.current, 50)

    @covers_requirement(
        "player-combat-session::all-personal-skill-choices-and-costs-are-actor-scoped"
    )
    def test_companion_freeform_magnitude_eligibility_without_leakage(self):
        companion = _companion(self.player, "風靈同伴", hp=100)
        companion.traits.mp.base = 100
        companion.traits.mp.current = 100
        grant_lineage(companion, [_T_CAST])
        # Companion does not have wind mastery
        engage(self.player, self.monster)

        from world.rules.action import RejectReason
        # Forged scale by companion without mastery rejects
        result = submit_player_action(
            self.player,
            _T_CAST,
            [self.monster],
            scale=2.0,
            commanded_actor=companion,
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["reason"], RejectReason.SCALED_CAST_FORBIDDEN)

    @covers_requirement(
        "player-combat-session::free-inspection-and-equipment-operations-do-not-select-round-commands"
    )
    def test_free_inspection_causes_no_round_advancement(self):
        companion = _companion(self.player, "巡察同伴", hp=100)
        engage(self.player, self.monster)
        before_rounds = read_session(self.player).rounds_elapsed

        from world.rules.combat_view import build_combat_view
        from world.rules.items import enumerate_actor_item_choices
        record = read_session(self.player)
        field = reconstruct_battlefield(self.player, record)
        context = _context_for(field, record)

        # Inspect choices
        _ = build_combat_view(self.player, for_actor=companion)
        _ = enumerate_actor_item_choices(companion, context)

        # No round advance, dice roll, or resource cost
        after_rounds = read_session(self.player).rounds_elapsed
        self.assertEqual(before_rounds, after_rounds)

    @covers_requirement(
        "item-use-resolution::controllable-companion-item-requests-use-that-actors-complete-item-rules"
    )
    def test_companion_item_requests_use_companion_inventory_and_mirrors(self):
        companion = _companion(self.player, "背包同伴", hp=50)
        companion.traits.hp.base = 100
        companion.traits.hp.current = 50
        # Use t_ember_spray which is already in synthetic scope and is combat-allowed self-heal
        companion.db.inventory = ["t_ember_spray"]
        self.player.db.inventory = []

        engage(self.player, self.monster)
        record = read_session(self.player)
        field = reconstruct_battlefield(self.player, record)
        context = _context_for(field, record)

        from world.rules.items import enumerate_actor_item_choices, ItemUseReason
        # Companion item choices exist
        choices = enumerate_actor_item_choices(companion, context)
        self.assertTrue(any(c.item_key == "t_ember_spray" and c.enabled for c in choices))

        # Commander lacks item
        cmd_choices = enumerate_actor_item_choices(self.player, context)
        self.assertFalse(any(c.item_key == "t_ember_spray" for c in cmd_choices))

        # Forged item request for commander who lacks t_ember_spray
        rej = submit_player_item_use(
            self.player,
            "t_ember_spray",
            commanded_actor=self.player,
        )
        self.assertEqual(rej["outcome"], "rejected")
        self.assertEqual(rej["reason"], ItemUseReason.ITEM_NOT_HELD)

        # Forged item request for companion naming item companion lacks
        companion.db.inventory = []
        rej2 = submit_player_item_use(
            self.player,
            "t_ember_spray",
            commanded_actor=companion,
        )
        self.assertEqual(rej2["outcome"], "rejected")
        self.assertEqual(rej2["reason"], ItemUseReason.ITEM_NOT_HELD)
        companion.db.inventory = ["t_ember_spray"]

        # Valid item use by companion heals companion and consumes companion mirror
        submit_player_action(self.player, BASIC_ATTACK_KEY, [self.monster])
        result = submit_player_item_use(
            self.player,
            "t_ember_spray",
            commanded_actor=companion,
        )
        self.assertEqual(result["outcome"], "round")
        self.assertGreater(companion.traits.hp.current, 50)
        self.assertEqual(companion.db.inventory.count("t_ember_spray"), 0)


class PartyRetreatTests(BattlefieldIsolation, EvenniaTestCase):
    """Tasks 1.1-4.1: the confirmed party retreat's one contest and its round.

    The bounds established here: the contest uses the SLOWEST able ally against
    the FASTEST living pursuer and ignores accuracy; no pursuer escapes without
    a roll and no able ally takes the ordinary defeat path; a success carries
    the whole present party — knocked-out companions included and excluded from
    the minimum — with no enemy action and one elapsed round settled exactly
    once; a failure consumes every allied opportunity, runs one ordinary enemy
    round with no draft action and no tactical benefit, costs no resource and
    leaves a fresh empty next-round draft; and a failure after the round's own
    writes rolls the whole unit back for a safe retry, while a replay or a
    round that already spent the revision cannot retreat twice.
    """

    def setUp(self):
        open_synthetic_scope(
            self, *_SCOPE_LOGICALS, extra=synth_innate_overlay()
        )
        super().setUp()
        from world.quests.catalog import register_catalog

        register_catalog()
        self.room = create_object(Room, key="retreat arena")
        self.player = _player(key="retreat player")
        self.player.location = self.room
        self.monster = _monster("retreat goblin", hp=500, atk=10, agility=15)
        self.monster.location = self.room

    def _retreat_prompt(self):
        record = read_session(self.player)
        return request_party_exit(
            self.player,
            record.session_id,
            record.round_revision,
            PARTY_EXIT_RETREAT,
        )

    def _confirm(self, prompt):
        return confirm_party_exit(
            self.player,
            prompt["session_id"],
            prompt["round_revision"],
            prompt["operation"],
            prompt["confirmation_token"],
        )

    def _hours(self):
        from world.rules.combat_session import settlement as settlement_module

        real = settlement_module.settle_combat_result
        seen: list[int] = []

        def counting(result, entities):
            seen.append(result.total_seconds)
            return real(result, entities)

        return seen, counting

    @covers_requirement("player-combat-session::active-sessions-block-movement-and-define-pause-forfeit-and-recovery-outcomes")
    def test_the_contest_uses_the_slowest_able_ally_against_the_fastest_pursuer(self):
        from world.rules.disengage import _adjusted_agility

        self.player.traits.agility.base = 20
        companion = _companion(self.player, "慢速同伴", hp=200, agility=10)
        fast = _monster("快速追兵", hp=500, agility=12)
        fast.location = self.room
        engage_group(self.player, [self.monster, fast])
        # The premise the fixed dice below are read against: the able allys
        # adjusted agilities are 10 and 20, and the living pursuers' maximum
        # is self.monster's 15 (not the slower 12 of the second pursuer).
        self.assertEqual(_adjusted_agility(companion), 10)
        self.assertEqual(_adjusted_agility(self.player), 20)
        self.assertEqual(_adjusted_agility(self.monster), 15)
        self.assertEqual(_adjusted_agility(fast), 12)

        # 54 + 10 = 64 fails against 51 + 15 = 66. Were the faster ally used
        # (74) or the slower pursuer compared against (63), it would succeed:
        # this single outcome pins both the minimum and the maximum.
        self.player.traits.hp.base = 1000
        self.player.traits.hp.current = 1000
        prompt = self._retreat_prompt()
        with (
            patch("world.rules.disengage.roll_d100", return_value=54),
            patch("world.rules.combat.battlefield.roll_d100", return_value=100),
            patch("world.rules.combat.damage.roll_d100", return_value=1),
            patch("world.rules.combat.rounds.roll_d100", return_value=100),
        ):
            failed = self._confirm(prompt)
        self.assertEqual(failed["outcome"], "round")
        self.assertEqual(read_session(self.player).rounds_elapsed, 1)

        # 56 + 10 = 66 meets the boundary exactly, per §6.1's own example.
        prompt = self._retreat_prompt()
        with patch("world.rules.disengage.roll_d100", return_value=56):
            escaped = self._confirm(prompt)
        self.assertEqual(escaped["outcome"], "fled")
        self.assertIsNone(self.player.db.active_combat)

    @covers_requirement("player-combat-session::active-sessions-block-movement-and-define-pause-forfeit-and-recovery-outcomes")
    def test_accuracy_never_moves_the_contest(self):
        # The Dodge threshold bonus is a round-start declaration, and the
        # failed-retreat test below establishes that no declaration is even
        # projected on this path; this one pins accuracy's own independence.
        from world.rules.combat_modifiers import evaluate_combat_modifiers
        from world.rules.disengage import _adjusted_agility

        self.player.traits.agility.base = 20
        companion = _companion(self.player, "準確同伴", hp=200, agility=10)
        engage(self.player, self.monster)

        def with_accuracy(entity):
            bundle = dict(evaluate_combat_modifiers(entity))
            bundle["accuracy"] = "+900%"
            return bundle

        with patch(
            "world.rules.disengage.evaluate_combat_modifiers",
            side_effect=with_accuracy,
        ):
            self.assertEqual(_adjusted_agility(companion), 10)
            self.assertEqual(_adjusted_agility(self.player), 20)
            # 55 + 10 = 65 still misses 66: not one accuracy point entered it.
            prompt = self._retreat_prompt()
            with patch("world.rules.disengage.roll_d100", return_value=55):
                result = self._confirm(prompt)
        self.assertEqual(result["outcome"], "round")
        self.assertTrue(is_active_session(self.player))

    @covers_requirement("player-combat-session::active-sessions-block-movement-and-define-pause-forfeit-and-recovery-outcomes")
    def test_a_success_carries_the_knocked_out_companion_and_settles_one_round_once(self):
        self.player.traits.agility.base = 20
        self.player.traits.hp.base = 100
        self.player.traits.hp.current = 50
        # Above the nonlethal floor so engagement collects it at all; the
        # knockout mark below is what takes it out of action.
        companion = _companion(self.player, "倒地同伴", hp=2, agility=1)
        self.assertEqual(party_ids(self.player), [companion.pk])
        engage(self.player, self.monster)
        # The companion is out of action and would drag the minimum to 1 if it
        # were still counted; it must be carried instead. The durable record is
        # the source every entry point rebuilds from, so the mark lives there.
        from dataclasses import replace

        from world.rules.combat_session.lifecycle import _persist

        record = read_session(self.player)
        self.assertIn(int(companion.pk), record.player_ids)
        _persist(
            self.player,
            replace(
                record,
                knocked_out_ids=(int(companion.pk),),
            ),
        )
        companion.traits.hp.current = 1
        self.monster.traits.hp.current = 400

        prompt = self._retreat_prompt()
        settled, counting = self._hours()
        with (
            patch("world.rules.disengage.roll_d100", return_value=56),
            patch(
                "world.rules.combat_session.settlement.settle_combat_result",
                side_effect=counting,
            ),
            patch("world.rules.combat_session.rounds.run_round") as run,
        ):
            result = self._confirm(prompt)

        # No enemy action ran at all, and exactly one elapsed round settled.
        run.assert_not_called()
        self.assertEqual(settled, [6])
        self.assertEqual(result["outcome"], "fled")
        self.assertEqual(result["rounds_elapsed"], 1)
        self.assertEqual(result["receipt"]["operation"], PARTY_EXIT_RETREAT)
        kinds = [
            entry.kind for log in result["logs"] for entry in log.entries
        ]
        self.assertIn("party_retreat", kinds)
        # The whole party left, and the carried companion gained nothing: no
        # healing, no revival, and nobody was relocated.
        self.assertIsNone(self.player.db.active_combat)
        self.assertFalse(is_active_session(self.player))
        self.assertFalse(is_active_session(companion))
        # No subset stayed in combat, and every participant was released from
        # the registration that blocks time skips.
        self.assertNotEqual(
            evaluate_skip_safety(self.player), SkipRejectReason.IN_COMBAT
        )
        for entity in (self.player, companion, self.monster):
            self.assertNotIn(str(entity.pk), _BATTLEFIELDS)
        self.assertEqual(self.player.traits.hp.current, 50)
        # Carried, not regenerated: the settlement's scope excludes the whole
        # departed party, so the companion stays on the nonlethal floor.
        self.assertEqual(companion.traits.hp.current, 1)
        self.assertGreater(self.monster.traits.hp.current, 0)
        self.assertEqual(self.player.location, self.room)

    @covers_requirement("player-combat-session::active-sessions-block-movement-and-define-pause-forfeit-and-recovery-outcomes")
    def test_a_failed_retreat_consumes_every_opportunity_and_runs_one_enemy_round(self):
        self.player.traits.agility.base = 20
        self.player.traits.hp.base = 1000
        self.player.traits.hp.current = 1000
        companion = _companion(self.player, "指令同伴", hp=200, agility=10)
        companion.traits.mp.base = 50
        companion.traits.mp.current = 50
        grant_lineage(companion, [_T_CAST])
        engage(self.player, self.monster)
        # A pending draft of personal commands whose one admitted entry is a
        # casting that costs MP: the last member's confirmation is what would
        # auto-submit the round, so the retreat is confirmed with that
        # selection still unspent and its resource untouched.
        admitted = submit_player_action(
            self.player,
            _T_CAST,
            [self.monster],
            commanded_actor=companion,
        )
        self.assertEqual(admitted["outcome"], "draft", admitted)
        record = read_session(self.player)
        draft_before = dict(record.draft_entries)
        self.assertEqual(len(draft_before), 1)
        party_hp_before = (
            self.player.traits.hp.current + companion.traits.hp.current
        )

        prompt = self._retreat_prompt()
        with (
            patch("world.rules.disengage.roll_d100", return_value=1),
            patch("world.rules.combat.battlefield.roll_d100", return_value=100),
            patch("world.rules.combat.damage.roll_d100", return_value=100),
            patch("world.rules.combat.rounds.roll_d100", return_value=100),
            patch(
                "world.rules.combat_session.rounds._draft_tactical_declarations"
            ) as tactical,
            patch(
                "world.rules.combat_session.rounds._draft_taunt_declarations"
            ) as taunt,
            patch(
                "world.rules.combat_session.rounds._draft_requests"
            ) as requests,
        ):
            result = self._confirm(prompt)

        # The party stayed, the round counted, and a fresh empty draft waits.
        self.assertEqual(result["outcome"], "round")
        current = read_session(self.player)
        self.assertEqual((current.rounds_elapsed, current.round_revision), (1, 1))
        self.assertEqual(current.draft_entries, {})
        self.assertEqual(current.confirmed_actors, ())
        self.assertTrue(is_active_session(self.player))
        # No old draft entry executed, no declaration was even projected, and
        # the attempt spent no MP or SP.
        self.assertEqual(self.monster.traits.hp.current, 500)
        tactical.assert_not_called()
        taunt.assert_not_called()
        requests.assert_not_called()
        # The admitted casting never resolved, so its cost was never charged.
        self.assertEqual(companion.traits.mp.current, 50)
        # The enemies did act under ordinary rules.
        self.assertLess(
            self.player.traits.hp.current + companion.traits.hp.current,
            party_hp_before,
        )
        kinds = [entry.kind for log in result["logs"] for entry in log.entries]
        self.assertIn("party_retreat", kinds)

    @covers_requirement("player-combat-session::active-sessions-block-movement-and-define-pause-forfeit-and-recovery-outcomes")
    def test_a_failed_retreat_still_honors_an_enemys_own_capability(self):
        # "Eligible enemies act under normal rules": an enemy the ordinary
        # round's own action gate locks takes no action, logs the existing skip
        # event, and the round still counts and still performs its upkeep.
        from world.rules.combat_modifiers import evaluate_combat_modifiers

        self.player.traits.hp.base = 1000
        self.player.traits.hp.current = 1000
        engage(self.player, self.monster)
        record = read_session(self.player)
        prompt = self._retreat_prompt()

        def locked_enemy(entity):
            if entity is self.monster:
                return {"actions_per_turn": 0}
            return evaluate_combat_modifiers(entity)

        settled, counting = self._hours()
        with (
            patch("world.rules.disengage.roll_d100", return_value=1),
            patch(
                "world.rules.combat.rounds.evaluate_combat_modifiers",
                side_effect=locked_enemy,
            ),
            patch("world.rules.combat.battlefield.roll_d100", return_value=100),
            patch(
                "world.rules.combat_session.settlement.settle_combat_result",
                side_effect=counting,
            ),
        ):
            result = self._confirm(prompt)
        self.assertEqual(result["outcome"], "round")
        current = read_session(self.player)
        self.assertEqual(current.round_revision, record.round_revision + 1)
        self.assertEqual(current.draft_entries, {})
        kinds = [entry.kind for log in result["logs"] for entry in log.entries]
        self.assertIn("action_skipped", kinds)
        self.assertIn("party_retreat", kinds)
        # The locked enemy dealt no damage, but its round still elapsed and its
        # upkeep still ran, so the party's total time is unchanged for now
        # (nothing settles until a terminal outcome).
        self.assertEqual(self.player.traits.hp.current, 1000)
        self.assertEqual(settled, [])

    @covers_requirement("player-combat-session::active-sessions-block-movement-and-define-pause-forfeit-and-recovery-outcomes")
    def test_a_party_with_no_pursuer_left_escapes_without_a_roll(self):
        self.player.traits.agility.base = 20
        companion = _companion(self.player, "同行者", hp=200, agility=10)
        engage(self.player, self.monster)
        # The last living pursuer falls before the retreat is confirmed (no
        # round settles between the two, so the session is still active).
        self.monster.traits.hp.current = 0
        prompt = self._retreat_prompt()
        settled, counting = self._hours()
        with (
            patch("world.rules.disengage.roll_d100") as roll,
            patch(
                "world.rules.combat_session.settlement.settle_combat_result",
                side_effect=counting,
            ),
        ):
            result = self._confirm(prompt)
        roll.assert_not_called()
        self.assertEqual(result["outcome"], "fled")
        self.assertEqual(settled, [6])
        self.assertFalse(is_active_session(self.player))
        self.assertFalse(is_active_session(companion))

    @covers_requirement("player-combat-session::active-sessions-block-movement-and-define-pause-forfeit-and-recovery-outcomes")
    def test_a_failed_escape_write_rolls_the_party_back_into_combat(self):
        from world.rules.clock import get_world_clock

        self.player.traits.agility.base = 20
        companion = _companion(self.player, "同退同伴", hp=200, agility=10)
        engage(self.player, self.monster)
        prompt = self._retreat_prompt()
        tick_before = get_world_clock().tick
        with (
            patch("world.rules.disengage.roll_d100", return_value=56),
            patch(
                "world.rules.combat_session.exit.write_last_combat_receipt",
                side_effect=RuntimeError("receipt write failed"),
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "receipt write failed"):
                self._confirm(prompt)
        # No subset left combat: the whole party is still in the session, the
        # fled marks were rolled back, and the clock did not move.
        self.assertTrue(is_active_session(self.player))
        self.assertEqual(get_world_clock().tick, tick_before)
        self.assertEqual(
            evaluate_skip_safety(self.player), SkipRejectReason.IN_COMBAT
        )
        for entity in (self.player, companion, self.monster):
            self.assertIn(str(entity.pk), _BATTLEFIELDS)
        record = read_session(self.player)
        self.assertEqual(record.fled_ids, ())
        self.assertEqual((record.rounds_elapsed, record.round_revision), (0, 0))

        # The later valid retry completes and takes the whole party out.
        settled, counting = self._hours()
        with (
            patch("world.rules.disengage.roll_d100", return_value=56),
            patch(
                "world.rules.combat_session.settlement.settle_combat_result",
                side_effect=counting,
            ),
        ):
            result = self._confirm(prompt)
        self.assertEqual(settled, [6])
        self.assertEqual(result["outcome"], "fled")
        self.assertFalse(is_active_session(self.player))
        self.assertFalse(is_active_session(companion))
        for entity in (self.player, companion, self.monster):
            self.assertNotIn(str(entity.pk), _BATTLEFIELDS)

    @covers_requirement("player-combat-session::active-sessions-block-movement-and-define-pause-forfeit-and-recovery-outcomes")
    def test_no_able_allied_member_takes_the_ordinary_defeat_path(self):
        engage(self.player, self.monster)
        prompt = self._retreat_prompt()
        with (
            patch(
                "world.rules.combat_session.rounds.get_required_combat_actors",
                return_value=(),
            ),
            patch("world.rules.disengage.roll_d100") as roll,
            patch("world.rules.combat_session.rounds.run_round") as run,
        ):
            result = self._confirm(prompt)
        # No roll, no round, no enemy action: the approved defeat branch.
        roll.assert_not_called()
        run.assert_not_called()
        self.assertEqual(result["outcome"], "defeat")
        self.assertEqual(result["receipt"]["outcome"], "defeat")
        self.assertIsNone(self.player.db.active_combat)
        self.assertFalse(is_active_session(self.player))

    @covers_requirement("player-combat-session::active-sessions-block-movement-and-define-pause-forfeit-and-recovery-outcomes")
    def test_an_unreconstructable_battlefield_takes_the_same_defeat_path(self):
        engage(self.player, self.monster)
        prompt = self._retreat_prompt()
        self.monster.delete()
        with patch("world.rules.combat_session.rounds.run_round") as run:
            result = self._confirm(prompt)
        run.assert_not_called()
        self.assertEqual(result["outcome"], "defeat")
        self.assertIsNone(self.player.db.active_combat)

    @covers_requirement("player-combat-session::combat-time-settles-once-at-terminal-session-outcome")
    def test_a_failed_retreat_the_enemy_round_decides_settles_terminal_once(self):
        # The pursuers defeat the party inside the failed retreat's own round:
        # the ordinary enemy round is what ends the session, and the whole
        # party's accumulated time still settles exactly once, from the round
        # boundary rather than from a second settlement of its own.
        self.player.traits.hp.base = 1
        self.player.traits.hp.current = 1
        self.monster.traits.atk_phys.base = 100
        engage(self.player, self.monster)
        prompt = self._retreat_prompt()
        settled, counting = self._hours()
        with (
            patch("world.rules.disengage.roll_d100", return_value=1),
            patch("world.rules.combat.battlefield.roll_d100", return_value=100),
            patch("world.rules.combat.damage.roll_d100", return_value=100),
            patch("world.rules.combat.rounds.roll_d100", return_value=100),
            patch(
                "world.rules.combat_session.settlement.settle_combat_result",
                side_effect=counting,
            ),
        ):
            result = self._confirm(prompt)
        self.assertEqual(result["outcome"], "defeat")
        # One elapsed round's six seconds settle once, and only once.
        self.assertEqual(settled, [6])
        self.assertIsNone(self.player.db.active_combat)
        self.assertFalse(is_active_session(self.player))

    @covers_requirement("player-combat-session::combat-time-settles-once-at-terminal-session-outcome")
    @covers_requirement("player-combat-session::round-revisions-execute-at-most-once-across-retries-and-stale-requests")
    def test_a_replayed_confirmation_settles_once(self):
        self.player.traits.agility.base = 20
        engage(self.player, self.monster)
        prompt = self._retreat_prompt()
        _, counting = self._hours()
        with (
            patch("world.rules.disengage.roll_d100", return_value=56),
            patch(
                "world.rules.combat_session.settlement.settle_combat_result",
                side_effect=counting,
            ),
        ):
            first = self._confirm(prompt)
        self.assertEqual(first["outcome"], "fled")

        from world.rules.clock import get_world_clock

        tick_after = get_world_clock().tick
        with patch(
            "world.rules.combat_session.settlement.settle_combat_result"
        ) as settle:
            replay = self._confirm(prompt)
        settle.assert_not_called()
        self.assertTrue(replay["idempotent"])
        self.assertEqual(replay["receipt"], first["receipt"])
        self.assertEqual(get_world_clock().tick, tick_after)
        self.assertIsNone(self.player.db.active_combat)

    @covers_requirement("player-combat-session::round-revisions-execute-at-most-once-across-retries-and-stale-requests")
    def test_a_round_that_spent_the_revision_refuses_the_stale_retreat(self):
        engage(self.player, self.monster)
        prompt = self._retreat_prompt()
        with (
            patch("world.rules.combat.battlefield.roll_d100", return_value=100),
            patch("world.rules.combat.damage.roll_d100", return_value=100),
            patch("world.rules.combat.rounds.roll_d100", return_value=100),
        ):
            resolved = submit_player_action(
                self.player, BASIC_ATTACK_KEY, [self.monster]
            )
        self.assertEqual(resolved["outcome"], "round")
        self.assertEqual(read_session(self.player).round_revision, 1)
        for revision in (prompt["round_revision"], 1):
            with self.subTest(revision=revision):
                with self.assertRaises(CombatSessionError) as ctx:
                    confirm_party_exit(
                        self.player,
                        prompt["session_id"],
                        revision,
                        PARTY_EXIT_RETREAT,
                        prompt["confirmation_token"],
                    )
                self.assertEqual(
                    ctx.exception.args[0], SessionReason.STALE_ROUND_REVISION
                )
                self.assertTrue(is_active_session(self.player))
        self.assertEqual(read_session(self.player).round_revision, 1)

    @covers_requirement("player-combat-session::active-sessions-block-movement-and-define-pause-forfeit-and-recovery-outcomes")
    def test_a_failure_after_the_round_rolls_every_touched_surface_back(self):
        from world.rules.clock import get_world_clock

        self.player.traits.agility.base = 20
        self.player.traits.hp.base = 1000
        self.player.traits.hp.current = 1000
        companion = _companion(self.player, "回溯同伴", hp=200, agility=10)
        engage(self.player, self.monster)
        admitted = submit_player_action(
            self.player, BASIC_ATTACK_KEY, [self.monster]
        )
        self.assertEqual(admitted["outcome"], "draft", admitted)
        record = read_session(self.player)
        draft = dict(record.draft_entries)
        player_hp = self.player.traits.hp.current
        companion_hp = companion.traits.hp.current
        tick_before = get_world_clock().tick

        prompt = self._retreat_prompt()
        with (
            patch("world.rules.disengage.roll_d100", return_value=1),
            patch("world.rules.combat.battlefield.roll_d100", return_value=100),
            patch("world.rules.combat.damage.roll_d100", return_value=100),
            patch("world.rules.combat.rounds.roll_d100", return_value=100),
            patch(
                "world.rules.combat_session.exit.write_last_combat_receipt",
                side_effect=RuntimeError("receipt write failed"),
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "receipt write failed"):
                self._confirm(prompt)

        # Every durable and in-process surface survived the rolled-back unit,
        # including the failed round's HP writes.
        current = read_session(self.player)
        self.assertIsNotNone(current)
        self.assertEqual(current.draft_entries, draft)
        self.assertEqual(
            (current.rounds_elapsed, current.round_revision),
            (record.rounds_elapsed, record.round_revision),
        )
        self.assertEqual(self.player.traits.hp.current, player_hp)
        self.assertEqual(companion.traits.hp.current, companion_hp)
        self.assertEqual(self.monster.traits.hp.current, 500)
        self.assertEqual(get_world_clock().tick, tick_before)
        self.assertTrue(is_active_session(self.player))
        self.assertEqual(
            evaluate_skip_safety(self.player), SkipRejectReason.IN_COMBAT
        )

        # The later valid retry completes once, and the retreat's own round
        # settles the accumulated time exactly once.
        settled, counting = self._hours()
        with (
            patch("world.rules.disengage.roll_d100", return_value=56),
            patch(
                "world.rules.combat_session.settlement.settle_combat_result",
                side_effect=counting,
            ),
        ):
            result = self._confirm(prompt)
        self.assertEqual(settled, [6])
        self.assertEqual(result["outcome"], "fled")
        self.assertIsNone(self.player.db.active_combat)


class PartyRetreatContestTests(EvenniaTestCase):
    """Task 1.1: the contest's own roll-free branches, at the helper boundary."""

    def _field(self, allies, foes):
        roster = {entity.key: entity for entity in (*allies, *foes)}
        return Battlefield(
            teams={
                "party": frozenset(entity.key for entity in allies),
                "foes": frozenset(entity.key for entity in foes),
            },
            roster=roster,
        )

    def test_no_pursuer_escapes_without_drawing_a_roll(self):
        from world.rules.disengage import party_retreat_attempt

        ally = FakeEntity("ally", agility=3)
        fled = FakeEntity("fled foe", agility=90)
        knocked = FakeEntity("knocked foe", agility=90, hp=0)
        field = self._field([ally], [fled, knocked])
        field.fled.add("fled foe")
        field.knocked_out.add("knocked foe")
        with patch("world.rules.disengage.roll_d100") as roll:
            success, detail = party_retreat_attempt(field, "party", [ally])
        roll.assert_not_called()
        self.assertTrue(success)
        self.assertIsNone(detail["roll"])
        self.assertEqual(detail["allied_agility"], 3)
        self.assertIsNone(detail["pursuer_agility"])

    def test_no_acting_ally_reports_the_defeat_branch_without_a_roll(self):
        from world.rules.disengage import party_retreat_attempt

        foe = FakeEntity("foe", agility=90)
        field = self._field([], [foe])
        with patch("world.rules.disengage.roll_d100") as roll:
            success, detail = party_retreat_attempt(field, "party", [])
        roll.assert_not_called()
        self.assertIsNone(success)
        self.assertIsNone(detail["allied_agility"])

    def test_one_roll_compares_the_slowest_ally_and_the_fastest_pursuer(self):
        # Saturation gaps, not the boundary arithmetic: each arm offers the
        # same fixed roll to two calls whose ally set (or pursuer set) differs
        # in exactly the extreme that must decide it, so the outcome flips
        # whatever the shipped constant is. Nothing here restates that constant
        # or its formula.
        from world.rules.disengage import party_retreat_attempt

        slow = FakeEntity("slow", agility=1)
        fast = FakeEntity("fast", agility=200)
        pursuer = FakeEntity("pursuer", agility=100)
        # The slowest ally can never reach this hill of a pursuer while the
        # fastest alone cannot miss it: the attempt that has both able allies
        # available must use the slower one and fail.
        field = self._field([slow, fast], [pursuer])
        with patch("world.rules.disengage.roll_d100", return_value=100):
            both, detail = party_retreat_attempt(
                field, "party", [slow, fast]
            )
            alone, _ = party_retreat_attempt(field, "party", [fast])
        self.assertFalse(both)
        self.assertTrue(alone)
        self.assertEqual(detail["allied_agility"], 1)
        self.assertEqual(detail["pursuer_agility"], 100)
        self.assertEqual(detail["roll"], 100)

        # The same for the pursuer side: one puny pursuer cannot stop the
        # party, and adding a fearsome one must be the term the contest uses.
        weak = FakeEntity("weak", agility=1)
        fearsome = FakeEntity("fearsome", agility=200)
        ally = FakeEntity("ally", agility=50)
        with patch("world.rules.disengage.roll_d100", return_value=100):
            escaped, weak_detail = party_retreat_attempt(
                self._field([ally], [weak]), "party", [ally]
            )
            missed, fearsome_detail = party_retreat_attempt(
                self._field([ally], [weak, fearsome]), "party", [ally]
            )
        self.assertTrue(escaped)
        self.assertFalse(missed)
        self.assertEqual(weak_detail["pursuer_agility"], 1)
        self.assertEqual(fearsome_detail["pursuer_agility"], 200)


if __name__ == "__main__":
    unittest.main()
