"""Confirmed party exit: bound tokens, one admission, and surrender once.

The bounds this module establishes independently: the request returns a prompt
and changes nothing (cancel keeps every draft entry and advances no time); a
token verifies only for its own commander, session, round revision and
operation, and a stale or repeated confirmation never reaches another round or
session; the confirmed surrender discards the draft and enters the existing
defeat/FAIL settlement with no extra round, no success roll and exactly one
settlement of the already accumulated time; a technical failure anywhere in
that unit restores the draft and every touched surface, and the retry completes;
and no allied personal flee can escape by itself while the enemy's own
disengagement still resolves.
"""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.rooms import Room
from world.rules.clock import WorldClock, get_world_clock
from world.rules.combat_session import (
    BASIC_ATTACK_KEY,
    PARTY_EXIT_RETREAT,
    PARTY_EXIT_SURRENDER,
    CombatSessionError,
    SessionReason,
    confirm_actor_command,
    confirm_party_exit,
    engage,
    is_in_active_session,
    preflight_draft_entries,
    read_session,
    reconstruct_battlefield,
    request_party_exit,
    submit_player_action,
    to_storage,
)
from world.rules.combat_session.lifecycle import _persist
from world.rules.combat_session.records import read_last_combat_receipt
from world.rules.combat_session.rounds import _draft_requests
from world.rules.skip_safety import SkipRejectReason, evaluate_skip_safety

from ._combat_session_helpers import (
    BattlefieldIsolation,
    _monster,
    _player,
    open_synthetic_scope,
    synth_innate_overlay,
)

class PartyExitFixture(BattlefieldIsolation, EvenniaTestCase):
    def setUp(self):
        open_synthetic_scope(
            self, "skills", "elements", "items", "item_effect_profiles",
            extra=synth_innate_overlay(),
        )
        super().setUp()
        self.room = create_object(Room, key="party exit room")
        self.player = _player()
        self.player.location = self.room
        self.monster = _monster("exit goblin")
        self.monster.location = self.room

    def _waiting_companion(self):
        from typeclasses.npcs import NPC
        from world.rules.party import join_party

        companion = create_object(NPC, key="exit companion", location=self.room)
        companion.race = self.player.race
        companion.apply_race_baseline()
        join_party(companion, self.player)
        return companion

    def _engaged_with_pending_draft(self):
        """Engage with one waiting companion and admit the commander's entry."""
        companion = self._waiting_companion()
        engage(self.player, self.monster)
        admitted = submit_player_action(
            self.player, BASIC_ATTACK_KEY, [self.monster]
        )
        self.assertEqual(admitted["outcome"], "draft", admitted)
        return companion, read_session(self.player)


class PartyExitRequestTests(PartyExitFixture):
    @covers_requirement("player-combat-session::active-sessions-block-movement-and-define-pause-forfeit-and-recovery-outcomes")
    @covers_requirement("player-combat-session::party-exit-requires-a-commander-session-round-and-operation-bound-confirmation")
    def test_request_returns_the_party_prompt_and_cancelling_changes_nothing(self):
        _companion, record = self._engaged_with_pending_draft()
        before = to_storage(record)
        clock = WorldClock()
        with patch("world.rules.clock.get_world_clock", return_value=clock):
            prompt = request_party_exit(
                self.player,
                record.session_id,
                record.round_revision,
                PARTY_EXIT_SURRENDER,
            )
        self.assertEqual(prompt["outcome"], "prompt")
        self.assertEqual(prompt["operation"], PARTY_EXIT_SURRENDER)
        self.assertEqual(prompt["session_id"], record.session_id)
        self.assertEqual(prompt["round_revision"], record.round_revision)
        self.assertEqual(prompt["party_scope"], tuple(sorted(record.player_ids)))
        self.assertTrue(prompt["consequences"])
        self.assertTrue(prompt["confirmation_token"])
        # Cancel is discarding the prompt: every draft entry, the revision and
        # every counter are exactly where they were, and no time advanced.
        self.assertEqual(to_storage(read_session(self.player)), before)
        self.assertEqual(clock.tick, 0)
        self.assertTrue(is_in_active_session(self.player))
        # Retreat is the same request boundary with its own operation binding.
        retreat = request_party_exit(
            self.player, record.session_id, record.round_revision, PARTY_EXIT_RETREAT
        )
        self.assertEqual(retreat["operation"], PARTY_EXIT_RETREAT)
        self.assertEqual(retreat["party_scope"], prompt["party_scope"])
        self.assertNotEqual(
            retreat["confirmation_token"], prompt["confirmation_token"]
        )

    @covers_requirement("player-combat-session::party-exit-requires-a-commander-session-round-and-operation-bound-confirmation")
    def test_request_rejects_an_unknown_operation_and_a_stale_view(self):
        _companion, record = self._engaged_with_pending_draft()
        with self.assertRaises(CombatSessionError) as ctx:
            request_party_exit(
                self.player, record.session_id, record.round_revision, "charge"
            )
        self.assertEqual(
            ctx.exception.args[0], SessionReason.UNKNOWN_PARTY_EXIT_OPERATION
        )
        with self.assertRaises(CombatSessionError) as ctx:
            request_party_exit(
                self.player, "hostile:999:0", record.round_revision,
                PARTY_EXIT_SURRENDER,
            )
        self.assertEqual(ctx.exception.args[0], SessionReason.UNKNOWN_SESSION_ID)
        with self.assertRaises(CombatSessionError) as ctx:
            request_party_exit(
                self.player, record.session_id, record.round_revision + 1,
                PARTY_EXIT_SURRENDER,
            )
        self.assertEqual(ctx.exception.args[0], SessionReason.STALE_ROUND_REVISION)


class PartyExitConfirmationTests(PartyExitFixture):
    @covers_requirement("player-combat-session::active-sessions-block-movement-and-define-pause-forfeit-and-recovery-outcomes")
    @covers_requirement("player-combat-session::party-exit-requires-a-commander-session-round-and-operation-bound-confirmation")
    def test_forged_cross_bound_and_malformed_tokens_reject_without_mutation(self):
        _companion, record = self._engaged_with_pending_draft()
        before = to_storage(record)
        prompt = request_party_exit(
            self.player, record.session_id, record.round_revision,
            PARTY_EXIT_SURRENDER,
        )
        token = prompt["confirmation_token"]
        others = _player("unrelated bystander")
        rejections = {
            # cross-operation: a surrender token claimed as a retreat
            "cross_operation": (self.player, record.session_id, 0, PARTY_EXIT_RETREAT, token),
            # cross-session
            "cross_session": (self.player, "hostile:999:0", 0, PARTY_EXIT_SURRENDER, token),
            # cross-account: another commander's digest never verifies
            "cross_account": (others, record.session_id, 0, PARTY_EXIT_SURRENDER, token),
            # truncated and non-token input
            "truncated": (self.player, record.session_id, 0, PARTY_EXIT_SURRENDER, token[:-1]),
            "unknown_opcode": (self.player, record.session_id, 0, PARTY_EXIT_SURRENDER, "X-0-" + token[4:]),
        }
        for label, (commander, session, revision, operation, candidate) in rejections.items():
            with self.subTest(case=label):
                with self.assertRaises(CombatSessionError) as ctx:
                    confirm_party_exit(commander, session, revision, operation, candidate)
                self.assertEqual(
                    ctx.exception.args[0], SessionReason.INVALID_CONFIRMATION_TOKEN
                )
        # A claim that has moved past the token's own revision is stale, not
        # forged: the prompt belongs to an older revision of this session.
        with self.assertRaises(CombatSessionError) as ctx:
            confirm_party_exit(
                self.player,
                record.session_id,
                record.round_revision + 1,
                PARTY_EXIT_SURRENDER,
                token,
            )
        self.assertEqual(ctx.exception.args[0], SessionReason.STALE_ROUND_REVISION)
        for candidate in ("", "S-0", "S-0-ABC", "not a token", token + token):
            with self.subTest(case=candidate):
                with self.assertRaises(CombatSessionError) as ctx:
                    confirm_party_exit(
                        self.player, record.session_id, 0, PARTY_EXIT_SURRENDER,
                        candidate,
                    )
                self.assertIn(
                    ctx.exception.args[0],
                    (
                        SessionReason.INVALID_CONFIRMATION_TOKEN,
                        SessionReason.STALE_ROUND_REVISION,
                    ),
                )
        self.assertEqual(to_storage(read_session(self.player)), before)
        self.assertEqual(get_world_clock().tick, 0)

    @covers_requirement("player-combat-session::round-revisions-execute-at-most-once-across-retries-and-stale-requests")
    @covers_requirement("player-combat-session::party-exit-requires-a-commander-session-round-and-operation-bound-confirmation")
    def test_a_round_consumed_revision_makes_the_confirmation_stale(self):
        engage(self.player, self.monster)
        record = read_session(self.player)
        prompt = request_party_exit(
            self.player, record.session_id, record.round_revision,
            PARTY_EXIT_SURRENDER,
        )
        with patch(
            "world.rules.combat_session.rounds.run_round", return_value=[]
        ):
            resolved = submit_player_action(
                self.player, BASIC_ATTACK_KEY, [self.monster]
            )
        self.assertEqual(resolved["outcome"], "round")
        self.assertEqual(read_session(self.player).round_revision, 1)
        # The old prompt cannot affect the round that consumed its revision,
        # whether the caller restates the old revision or its current view.
        for revision in (record.round_revision, 1):
            with self.subTest(revision=revision):
                with self.assertRaises(CombatSessionError) as ctx:
                    confirm_party_exit(
                        self.player,
                        prompt["session_id"],
                        revision,
                        PARTY_EXIT_SURRENDER,
                        prompt["confirmation_token"],
                    )
                self.assertEqual(
                    ctx.exception.args[0], SessionReason.STALE_ROUND_REVISION
                )
                self.assertTrue(is_in_active_session(self.player))
                self.assertEqual(read_session(self.player).round_revision, 1)


class ConfirmedSurrenderTests(PartyExitFixture):
    @covers_requirement(
        "player-combat-session::active-sessions-block-movement-and-define-pause-forfeit-and-recovery-outcomes",
        "player-combat-session::combat-time-settles-once-at-terminal-session-outcome",
    )
    @covers_requirement("player-combat-session::confirmed-surrender-enters-existing-defeat-or-exam-fail-without-an-extra-round")
    def test_confirmed_surrender_discards_the_draft_and_settles_once(self):
        companion, record = self._engaged_with_pending_draft()
        # One committed ordinary round first, so the accumulated time is real
        # combat time and the revision has advanced.
        with (
            patch("world.rules.combat.battlefield.roll_d100", return_value=1),
            patch("world.rules.combat.damage.roll_d100", return_value=1),
            patch("world.rules.combat.rounds.roll_d100", return_value=1),
        ):
            completed = submit_player_action(
                self.player,
                BASIC_ATTACK_KEY,
                [self.monster],
                commanded_actor=companion,
            )
        self.assertEqual(completed["outcome"], "round", completed)
        record = read_session(self.player)
        self.assertEqual((record.round_revision, record.rounds_elapsed), (1, 1))
        admitted = submit_player_action(
            self.player, BASIC_ATTACK_KEY, [self.monster]
        )
        self.assertEqual(admitted["outcome"], "draft", admitted)
        self.assertTrue(read_session(self.player).draft_entries)

        settled: list[int] = []
        from world.rules.combat_session import settlement as settlement_module

        real_settle = settlement_module.settle_combat_result

        def counting(result, entities):
            settled.append(result.total_seconds)
            return real_settle(result, entities)

        prompt = request_party_exit(
            self.player, record.session_id, record.round_revision,
            PARTY_EXIT_SURRENDER,
        )
        with (
            patch(
                "world.rules.combat_session.settlement.settle_combat_result",
                side_effect=counting,
            ),
            patch("world.rules.combat_session.rounds.run_round") as run,
        ):
            result = confirm_party_exit(
                self.player,
                prompt["session_id"],
                prompt["round_revision"],
                PARTY_EXIT_SURRENDER,
                prompt["confirmation_token"],
            )
        # No extra round, no simulated enemy attack, one settlement of exactly
        # the accumulated time, and no artificial round added.
        run.assert_not_called()
        self.assertEqual(settled, [6])
        self.assertEqual(result["outcome"], "defeat")
        self.assertEqual(result["rounds_elapsed"], 1)
        # The combat clock settled exactly the accumulated one round; the
        # defeat aftermath's own recovery advance is that suite's behaviour.
        self.assertEqual(settled, [6])
        self.assertEqual(result["receipt"]["operation"], PARTY_EXIT_SURRENDER)
        self.assertEqual(result["receipt"]["round_revision"], 1)
        # The session and its draft are gone; nothing grants a new safe exit
        # or restoration privilege.
        self.assertIsNone(self.player.db.active_combat)
        self.assertFalse(is_in_active_session(self.player))

    @covers_requirement(
        "player-combat-session::combat-time-settles-once-at-terminal-session-outcome",
        "player-combat-session::round-revisions-execute-at-most-once-across-retries-and-stale-requests",
    )
    @covers_requirement("player-combat-session::confirmed-surrender-enters-existing-defeat-or-exam-fail-without-an-extra-round")
    def test_a_repeated_confirmation_replays_the_recorded_outcome_once(self):
        engage(self.player, self.monster)
        record = read_session(self.player)
        prompt = request_party_exit(
            self.player, record.session_id, record.round_revision,
            PARTY_EXIT_SURRENDER,
        )
        first = confirm_party_exit(
            self.player,
            prompt["session_id"],
            prompt["round_revision"],
            PARTY_EXIT_SURRENDER,
            prompt["confirmation_token"],
        )
        self.assertEqual(first["outcome"], "defeat")
        tick_after_first = get_world_clock().tick
        from world.rules.combat_session import settlement as settlement_module

        with patch(
            "world.rules.combat_session.settlement.settle_combat_result"
        ) as settle:
            replay = confirm_party_exit(
                self.player,
                prompt["session_id"],
                prompt["round_revision"],
                PARTY_EXIT_SURRENDER,
                prompt["confirmation_token"],
            )
        settle.assert_not_called()
        self.assertTrue(replay["idempotent"])
        self.assertEqual(replay["outcome"], first["outcome"])
        self.assertEqual(replay["receipt"], first["receipt"])
        self.assertEqual(get_world_clock().tick, tick_after_first)
        self.assertIsNone(self.player.db.active_combat)

    @covers_requirement(
        "player-combat-session::active-sessions-block-movement-and-define-pause-forfeit-and-recovery-outcomes",
        "player-combat-session::round-revisions-execute-at-most-once-across-retries-and-stale-requests",
    )
    @covers_requirement("player-combat-session::party-exit-requires-a-commander-session-round-and-operation-bound-confirmation")
    def test_an_exit_and_a_round_race_for_one_revision_admits_only_one(self):
        engage(self.player, self.monster)
        record = read_session(self.player)
        prompt = request_party_exit(
            self.player, record.session_id, record.round_revision,
            PARTY_EXIT_SURRENDER,
        )
        confirm_party_exit(
            self.player,
            prompt["session_id"],
            prompt["round_revision"],
            PARTY_EXIT_SURRENDER,
            prompt["confirmation_token"],
        )
        command = {
            "kind": "skill",
            "payload": {
                "skill_key": BASIC_ATTACK_KEY,
                "targets_or_shorthand": [self.monster.pk],
                "scale": 1.0,
            },
        }
        with patch("world.rules.combat_session.rounds.run_round") as run:
            rejected = confirm_actor_command(
                self.player, record.session_id, record.round_revision, 0,
                self.player.pk, command,
            )
        run.assert_not_called()
        self.assertFalse(rejected["ok"])
        self.assertEqual(rejected["reason"], "already_committed")
        self.assertEqual(rejected["receipt"]["operation"], PARTY_EXIT_SURRENDER)

    @covers_requirement("player-combat-session::active-sessions-block-movement-and-define-pause-forfeit-and-recovery-outcomes")
    @covers_requirement("player-combat-session::confirmed-surrender-enters-existing-defeat-or-exam-fail-without-an-extra-round")
    def test_a_failure_after_the_settlement_restores_the_draft_and_the_retry_completes(self):
        companion, _record = self._engaged_with_pending_draft()
        with (
            patch("world.rules.combat.battlefield.roll_d100", return_value=1),
            patch("world.rules.combat.damage.roll_d100", return_value=1),
            patch("world.rules.combat.rounds.roll_d100", return_value=1),
        ):
            submit_player_action(
                self.player,
                BASIC_ATTACK_KEY,
                [self.monster],
                commanded_actor=companion,
            )
        admitted = submit_player_action(
            self.player, BASIC_ATTACK_KEY, [self.monster]
        )
        self.assertEqual(admitted["outcome"], "draft", admitted)
        record = read_session(self.player)
        self.assertEqual(record.rounds_elapsed, 1)
        draft = dict(record.draft_entries)
        self.assertTrue(draft)
        prompt = request_party_exit(
            self.player, record.session_id, record.round_revision,
            PARTY_EXIT_SURRENDER,
        )
        tick_before = get_world_clock().tick
        receipt_before = read_last_combat_receipt(self.player)
        with patch(
            "world.rules.combat_session.exit.write_last_combat_receipt",
            side_effect=RuntimeError("receipt write failed"),
        ):
            with self.assertRaisesRegex(RuntimeError, "receipt write failed"):
                confirm_party_exit(
                    self.player,
                    prompt["session_id"],
                    prompt["round_revision"],
                    PARTY_EXIT_SURRENDER,
                    prompt["confirmation_token"],
                )
        # The durable session, its draft and every in-process surface survive:
        # the session is still active, still blocks time skips, and holds the
        # very entries the player had selected.
        current = read_session(self.player)
        self.assertIsNotNone(current)
        self.assertEqual(current.draft_entries, draft)
        self.assertEqual(current.round_revision, prompt["round_revision"])
        self.assertEqual(current.rounds_elapsed, 1)
        # The rolled-back receipt write left the *previous* round's receipt
        # exactly as it was; this exit recorded nothing.
        self.assertEqual(read_last_combat_receipt(self.player), receipt_before)
        self.assertNotIn("operation", receipt_before)
        self.assertTrue(is_in_active_session(self.player))
        self.assertEqual(
            evaluate_skip_safety(self.player), SkipRejectReason.IN_COMBAT
        )
        self.assertEqual(get_world_clock().tick, tick_before)

        from world.rules.combat_session import settlement as settlement_module

        real_settle = settlement_module.settle_combat_result
        settled: list[int] = []

        def counting(result, entities):
            settled.append(result.total_seconds)
            return real_settle(result, entities)

        # The later valid retry completes exactly once.
        with patch(
            "world.rules.combat_session.settlement.settle_combat_result",
            side_effect=counting,
        ):
            result = confirm_party_exit(
                self.player,
                prompt["session_id"],
                prompt["round_revision"],
                PARTY_EXIT_SURRENDER,
                prompt["confirmation_token"],
            )
        self.assertEqual(settled, [6])
        self.assertEqual(result["outcome"], "defeat")
        self.assertIsNone(self.player.db.active_combat)

    @covers_requirement("player-combat-session::active-sessions-block-movement-and-define-pause-forfeit-and-recovery-outcomes")
    def test_retreat_confirmation_reaches_no_settlement(self):
        engage(self.player, self.monster)
        record = read_session(self.player)
        prompt = request_party_exit(
            self.player, record.session_id, record.round_revision,
            PARTY_EXIT_RETREAT,
        )
        with patch(
            "world.rules.combat_session.settlement.settle_combat_result"
        ) as settle:
            with self.assertRaises(CombatSessionError) as ctx:
                confirm_party_exit(
                    self.player,
                    prompt["session_id"],
                    prompt["round_revision"],
                    PARTY_EXIT_RETREAT,
                    prompt["confirmation_token"],
                )
        self.assertEqual(
            ctx.exception.args[0], SessionReason.PARTY_EXIT_UNAVAILABLE
        )
        settle.assert_not_called()
        self.assertTrue(is_in_active_session(self.player))
        self.assertEqual(get_world_clock().tick, 0)
        self.assertIsNone(read_last_combat_receipt(self.player))

    @covers_requirement("player-combat-session::active-sessions-block-movement-and-define-pause-forfeit-and-recovery-outcomes")
    @covers_requirement("player-combat-session::confirmed-surrender-enters-existing-defeat-or-exam-fail-without-an-extra-round")
    def test_an_unreconstructable_battlefield_still_restores_every_gate(self):
        # A deleted participant makes the battlefield unreconstructable, so the
        # settlement runs with no battlefield at all — the branch whose wider
        # snapshot is the exit's own. A failure after that settlement body must
        # still leave the durable session, the in-process session cache and the
        # skip-safety registration exactly as they were.
        from world.rules.skip_safety import _BATTLEFIELDS

        engage(self.player, self.monster)
        record = read_session(self.player)
        self.monster.delete()
        prompt = request_party_exit(
            self.player, record.session_id, record.round_revision,
            PARTY_EXIT_SURRENDER,
        )
        tick_before = get_world_clock().tick
        receipt_before = read_last_combat_receipt(self.player)
        self.assertIn(str(self.player.pk), _BATTLEFIELDS)
        with patch(
            "world.rules.combat_session.exit.write_last_combat_receipt",
            side_effect=RuntimeError("receipt write failed"),
        ):
            with self.assertRaisesRegex(RuntimeError, "receipt write failed"):
                confirm_party_exit(
                    self.player,
                    prompt["session_id"],
                    prompt["round_revision"],
                    PARTY_EXIT_SURRENDER,
                    prompt["confirmation_token"],
                )
        current = read_session(self.player)
        self.assertIsNotNone(current)
        self.assertEqual(current.round_revision, record.round_revision)
        self.assertEqual(current.rounds_elapsed, record.rounds_elapsed)
        self.assertTrue(is_in_active_session(self.player))
        self.assertIn(str(self.player.pk), _BATTLEFIELDS)
        self.assertEqual(read_last_combat_receipt(self.player), receipt_before)
        self.assertEqual(get_world_clock().tick, tick_before)

        # The later valid retry completes the surrender exactly once.
        result = confirm_party_exit(
            self.player,
            prompt["session_id"],
            prompt["round_revision"],
            PARTY_EXIT_SURRENDER,
            prompt["confirmation_token"],
        )
        self.assertEqual(result["outcome"], "defeat")
        self.assertEqual(result["receipt"]["operation"], PARTY_EXIT_SURRENDER)
        self.assertIsNone(self.player.db.active_combat)
        self.assertNotIn(str(self.player.pk), _BATTLEFIELDS)


class AlliedFleeRemovalTests(PartyExitFixture):
    @covers_requirement("player-combat-session::active-sessions-block-movement-and-define-pause-forfeit-and-recovery-outcomes")
    @covers_requirement("player-combat-session::party-exit-requires-a-commander-session-round-and-operation-bound-confirmation")
    def test_the_facade_cannot_perform_an_allied_personal_flee(self):
        engage(self.player, self.monster)
        before = to_storage(read_session(self.player))
        with self.assertRaises(CombatSessionError) as ctx:
            submit_player_action(self.player, "flee", [])
        self.assertEqual(
            ctx.exception.args[0], SessionReason.PERSONAL_FLEE_FORBIDDEN
        )
        self.assertEqual(to_storage(read_session(self.player)), before)
        self.assertEqual(get_world_clock().tick, 0)

    @covers_requirement("player-combat-session::active-sessions-block-movement-and-define-pause-forfeit-and-recovery-outcomes")
    @covers_requirement("player-combat-session::party-exit-requires-a-commander-session-round-and-operation-bound-confirmation")
    def test_a_persisted_personal_flee_entry_never_resolves(self):
        engage(self.player, self.monster)
        record = read_session(self.player)
        flee_entry = {
            "kind": "skill",
            "payload": {
                "skill_key": "flee",
                "targets_or_shorthand": [],
                "scale": 1.0,
            },
        }
        from dataclasses import replace

        _persist(
            self.player,
            replace(
                record,
                draft_entries={self.player.pk: flee_entry},
                confirmed_actors=(self.player.pk,),
            ),
        )
        current = read_session(self.player)
        battlefield = reconstruct_battlefield(self.player, current)
        progress = preflight_draft_entries(self.player, current, battlefield)
        self.assertFalse(progress["is_complete"])
        self.assertEqual(
            progress["reselection_reasons"][self.player.pk]["reason"],
            "personal_flee_forbidden",
        )
        with self.assertRaisesRegex(ValueError, "confirmed party exit"):
            _draft_requests(current, battlefield)

    @covers_requirement("player-combat-session::combat-time-settles-once-at-terminal-session-outcome")
    def test_enemy_disengagement_still_resolves_through_the_action_pipeline(self):
        engage(self.player, self.monster)
        hp_before = self.player.traits.hp.current
        with (
            patch("world.rules.monster_behaviour._should_flee", return_value=True),
            patch("world.rules.disengage.roll_d100", return_value=100),
            patch("world.rules.combat.rounds.roll_d100", return_value=1),
            patch("world.rules.combat.battlefield.roll_d100", return_value=1),
            patch("world.rules.combat.damage.roll_d100", return_value=1),
        ):
            result = submit_player_action(
                self.player, BASIC_ATTACK_KEY, [self.monster]
            )
        # The enemy's own disengagement resolved through its policy: it fled
        # instead of attacking, so the player took no damage from it and the
        # session settled because no living foe remained.
        kinds = [
            entry.kind for log in result["logs"] for entry in log.entries
        ]
        self.assertIn("disengage_attempt", kinds)
        self.assertEqual(self.player.traits.hp.current, hp_before)
        self.assertEqual(result["outcome"], "victory")
