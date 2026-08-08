"""Companion joint-combat integration tests (party-combat).

Covers the party-combat contract end to end: co-located living companions join
the session's allied team on ``engage``, act once per round through the
deterministic policy provider (never fleeing, never consuming the player's
queued request), cannot die (per-entity nonlethal knockout floored at 1 HP and
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
from evennia.utils.test_resources import EvenniaTest

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
    _round_provider,
    engage,
    forfeit,
    read_session,
    reconstruct_battlefield,
    submit_player_action,
)
from world.rules.disengage import FLEE_SKILL_KEY
from world.rules.monster_behaviour import monster_behaviour_policy
from world.rules.party import join_party, party_ids
from world.rules.skip_safety import SkipRejectReason, _BATTLEFIELDS
from world.rules.targeting import expand_target_shorthand

from .combat_fixtures import FakeEntity


def _player(key="combat party player"):
    player = create_object(PlayerCharacter, key=key)
    player.race = "human"
    player.apply_race_baseline()
    player.db.skills = {"active": ["fire_ball", "wind_blade"], "passive": []}
    return player


def _monster(key="goblin", hp=100, atk=10, agility=10):
    monster = create_object(Monster, key=key)
    monster.threat_tier = "low"
    monster.apply_monster_tier("floor")
    monster.traits.hp.base = hp
    monster.traits.hp.current = hp
    monster.traits.atk_phys.base = atk
    monster.traits.agility.base = agility
    return monster


def _companion(player, key, hp=100, agility=10):
    npc = create_object(NPC, key=key, location=player.location)
    npc.race = "human"
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


class EngagePartyTests(EvenniaTest):
    """Task 1.4: allied-team collection on engage."""

    def setUp(self):
        super().setUp()
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
        with patch("world.rules.combat.roll_d100", return_value=100):
            outcome = submit_player_action(
                self.player, "fire_ball", [self.monster]
            )
        self.assertIn(outcome["outcome"], ("round", "victory", "defeat"))
        self.assertEqual(read_session(self.player).rounds_elapsed, 1)

    @covers_requirement("player-combat-session::one-preflight-valid-player-action-drives-one-complete-ordinary-combat-round")
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
            self.player, "fire_ball", [monster_a], context
        )
        provider = _round_provider(self.player, request, battlefield, record)
        calls: dict[str, int] = {}

        def counting(entity, field):
            calls[str(entity.key)] = calls.get(str(entity.key), 0) + 1
            return provider(entity, field)

        with patch("world.rules.combat.roll_d100", return_value=100):
            run_round(battlefield, counting)
        for key in (self.player.key, first.key, second.key, monster_a.key, monster_b.key):
            self.assertEqual(calls.get(str(key), 0), 1, key)

    @covers_requirement("player-combat-session::engage-creates-one-persistent-local-combat-session")
    @covers_requirement("party-system::companions-fight-as-allies-in-the-player-s-combat-session")
    def test_enemy_targeting_skill_never_selects_companion(self):
        companion = _companion(self.player, "同伴")
        engage(self.player, self.monster)
        result = submit_player_action(
            self.player, "fire_ball", [companion]
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["reason"], RejectReason.TARGET_FACTION_FORBIDDEN)
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)

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
            self.player, "fire_ball", [monster], context
        )
        provider = _round_provider(self.player, request, battlefield, record)
        with patch("world.rules.combat.roll_d100", return_value=100):
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
        request = ActionRequest(self.player, "fire_ball", [monster], context)
        provider = _round_provider(self.player, request, battlefield, record)
        with patch("world.rules.combat.roll_d100", return_value=100):
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


class KnockoutStateTests(EvenniaTest):
    """Tasks 2.7 and 3.3: per-entity nonlethal knockout as battlefield state."""

    def setUp(self):
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
            self.player, "fire_ball", [self.monster], context
        )
        provider = _round_provider(self.player, request, battlefield, record)
        with patch("world.rules.combat.roll_d100", return_value=100):
            return battlefield, run_round(battlefield, provider)

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

        def spy(entity, field):
            calls.append(str(entity.key))
            return real_policy(entity, field)

        with (
            patch(
                "world.rules.combat_session.monster_behaviour_policy",
                side_effect=spy,
            ),
            patch("world.rules.combat.roll_d100", return_value=100),
        ):
            result = submit_player_action(
                self.player, "fire_ball", [self.monster]
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
        with patch("world.rules.combat.roll_d100", return_value=100):
            submit_player_action(self.player, "fire_ball", [self.monster])
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


class TerminalAndCleanupTests(EvenniaTest):
    """Task 4.3: player-centric terminal rules and participant cleanup."""

    def setUp(self):
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
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = submit_player_action(
                self.player, "fire_ball", [self.monster]
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
            str(key) in _BATTLEFIELDS
            for key in (self.player.key, companion.key, self.monster.key)
        ))

    @covers_requirement("party-system::combat-terminal-rules-are-player-centric")
    def test_victory_requires_only_the_foes_team_to_be_gone(self):
        self.player.traits.agility.base = 50
        self.player.traits.magic_level.base = 200
        companion = _companion(self.player, "觀戰者", hp=100)
        self.monster.traits.hp.base = 100
        self.monster.traits.hp.current = 100
        self.monster.traits.agility.base = 5
        engage(self.player, self.monster)
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = submit_player_action(
                self.player, "fire_ball", [self.monster]
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
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = submit_player_action(
                self.player, "fire_ball", [self.monster]
            )
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(companion.traits.hp.current, 1)
        record = read_session(self.player)
        self.assertIn(int(companion.pk), record.knocked_out_ids)
        self.assertTrue(is_active_session(self.player))

    def test_missing_participant_cleanup_unregisters_every_survivor(self):
        companion = _companion(self.player, "留下來", hp=100)
        engage(self.player, self.monster)
        for key in (self.player.key, companion.key, self.monster.key):
            self.assertIn(str(key), _BATTLEFIELDS)
        self.monster.delete()
        result = forfeit(self.player)
        self.assertEqual(result["outcome"], "defeat")
        for key in (self.player.key, companion.key, self.monster.key):
            self.assertNotIn(str(key), _BATTLEFIELDS)
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
            patch("world.rules.combat.roll_d100", return_value=100),
            patch(
                "world.rules.combat.evaluate_combat_modifiers",
                return_value={},
            ),
        ):
            pending = _handle_damage(
                actor,
                [first, second],
                "damage:fire:magic",
                {
                    "battlefield": field,
                    "nonlethal_keys": frozenset({"第一", "第二"}),
                },
            )
        for effect in pending:
            effect.apply()
        self.assertEqual(first.traits.hp.value, 1)
        self.assertEqual(second.traits.hp.value, 1)
        self.assertEqual(field.knocked_out, {"第一", "第二"})


class BattlefieldCommitSurfaceTests(EvenniaTest):
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
        entity.race = "human"
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
            _commit(effects)
        self.assertIs(caught.exception.reason, RejectReason.COMMIT_FAILED)
        self.assertEqual(field.knocked_out, set())
        self.assertEqual(field.fled, set())

    @covers_requirement(
        "battlefield-commit-surface::a-commit-failure-rolls-back-a-battlefield-mutation-exactly-as-it-rolls-back-an-entity",
        "action-resolution-pipeline::resolution-is-atomic-a-failure-at-any-step-leaves-zero-state-mutated",
    )
    def test_entity_and_battlefield_restore_in_one_commit(self):
        entity = create_object(PlayerCharacter, key="mixed host")
        entity.race = "human"
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
            _commit(effects)
        self.assertIs(caught.exception.reason, RejectReason.COMMIT_FAILED)
        self.assertEqual(entity.traits.atk_phys.value, before)
        self.assertEqual(field.knocked_out, {str(entity.key)})

    def test_action_module_uses_shape_dispatch_for_both_sets(self):
        source = (
            Path(__file__).parents[1] / "action.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("from world.rules.combat import Battlefield", source)
        self.assertNotIn("isinstance(context, Battlefield", source)
        self.assertIn('"knocked_out"', source)


if __name__ == "__main__":
    unittest.main()
