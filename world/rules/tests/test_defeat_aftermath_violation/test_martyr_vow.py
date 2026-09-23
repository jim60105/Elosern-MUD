"""Slice of ``test_defeat_aftermath_violation``: the martyrdom-vow pool filter.

Church design §5.8: casting ``rite_martyrdom_vow`` during a fight stamps the
durable session id on the combat session record; at defeat settlement the
victim pool applies ONE extra filter — a valid stamp matching a non-fled,
living pool member collapses the pool to her, so the existing single-member
short-circuit returns her with zero target-selection rolls (resist contests
keep their normal draws). Victory consumes the stamp. Every edge (marker
died, marker fled, stale stamp, no stamp) falls back to the byte-identical
normal pool; rollback-retry determinism holds because the stamp is durable
record state and the draws stay state-derived.

The cast rail (the ``session_stamp`` effect handler) is exercised with a
synthetic self-cast skill so no shipped registry key is pinned here; the
row-side declaration is asserted once through the registry.
"""

from dataclasses import replace as dataclass_replace
from unittest.mock import patch

from tools.spec_traceability import covers_requirement

from world.rules import combat_session as combat_session_module
import world.rules.defeat_aftermath.violation as defeat_aftermath_violation_module
from world.rules.action import ActionRequest, ActionResolver
from world.rules.buffs import apply_buff, entity_active_buffs
from world.rules.combat import BattlefieldActionContext
from world.rules.combat_session import (
    engage,
    forfeit,
    read_session,
    settle_session,
    submit_player_action,
)
from world.rules.defeat_aftermath.violation import derived_roll as _module_derived_roll
from world.rules.skip_safety import _active_battlefield_for
from world.skills.registry import TargetSpec

from ._support import ViolationBase, _aftermath_entries

class MartyrVowBase(ViolationBase):
    """A defeat drives an engaged session; helpers stamp the session record."""

    def _stamp(self, *session_ids: str) -> None:
        """Stamp the player's durable session record with one or more ids."""
        record = read_session(self.player)
        combat_session_module._persist(
            self.player,
            dataclass_replace(record, martyr_key=tuple(session_ids)),
        )

    def _companion_session_id(self, companion) -> str:
        """Rebuild the durable session id a companion holds in this session."""
        record = read_session(self.player)
        mode, _, tick = record.session_id.split(":", 2)
        return f"{mode}:{int(companion.pk)}:{tick}"

    def _patch_rolls(self, target_roll, resist_roll):
        """Patch the engine's derivation purpose-aware (companion-victims D-P1)."""

        def roll(session_id, violator_key, victim_key, attempt_index, purpose):
            if purpose == "target":
                return target_roll(attempt_index)
            return resist_roll(attempt_index)

        return patch.object(
            defeat_aftermath_violation_module,
            "derived_roll",
            side_effect=roll,
        )


class MartyrPoolFilterTests(MartyrVowBase):
    """The one added filter stage and every byte-identical fallback."""

    @covers_requirement("church-ordination::martyrdom-vow-collapses-the-defeat-aftermath-victim-pool-to-the-marked-martyr")
    def test_the_marked_sister_is_chosen_with_zero_target_rolls(self):
        """A valid stamp collapses the pool; resist draws still run."""
        self._equalize_scores()
        self._arouse(85)
        resist_calls = []

        def target_roll(attempt_index):  # pragma: no cover - must never fire
            raise AssertionError(
                "a collapsed martyr pool must consume zero target rolls"
            )

        def resist_roll(attempt_index):
            resist_calls.append(attempt_index)
            return 1

        engage(self.player, self.monster)
        record = read_session(self.player)
        self._stamp(record.session_id)
        with self._patch_rolls(target_roll, resist_roll):
            result = forfeit(self.player)
        acts = [
            entry
            for entry in _aftermath_entries(result)
            if entry.kind == "violation_act"
        ]
        self.assertGreater(len(acts), 0)
        self.assertTrue(all(entry.target == str(self.player.key) for entry in acts))
        # The resist contests still drew their normal state-derived values.
        self.assertGreater(len(resist_calls), 0)

    @covers_requirement("church-ordination::martyrdom-vow-collapses-the-defeat-aftermath-victim-pool-to-the-marked-martyr")
    def test_stale_stamp_and_no_stamp_fall_back_to_the_normal_pool(self):
        """A foreign session id (or none) never fires the collapse."""
        self._equalize_scores()
        self._arouse(85)
        companion = self._companion("stale martyr")
        target_rolls = []

        def target_roll(attempt_index):
            target_rolls.append(attempt_index)
            return 0

        def resist_roll(attempt_index):
            return 1

        engage(self.player, self.monster)
        self._knock_out(companion)
        # Stale stamp: an id from a different session (other caster/tick).
        self._stamp("hostile:99999:1")
        with self._patch_rolls(target_roll, resist_roll):
            result = forfeit(self.player)
        acts = [
            e for e in _aftermath_entries(result) if e.kind == "violation_act"
        ]
        self.assertGreater(len(acts), 0)
        self.assertGreater(
            len(target_rolls), 0, "a stale stamp fires the normal pool draw"
        )

        # No stamp at all: identical normal-pool behaviour on a fresh fight.
        engage(self.player, self.monster)
        self._knock_out(companion)
        self._stamp()
        target_rolls.clear()
        with self._patch_rolls(target_roll, resist_roll):
            result = forfeit(self.player)
        acts = [
            e for e in _aftermath_entries(result) if e.kind == "violation_act"
        ]
        self.assertGreater(len(acts), 0)
        self.assertGreater(len(target_rolls), 0)

    @covers_requirement("church-ordination::martyrdom-vow-collapses-the-defeat-aftermath-victim-pool-to-the-marked-martyr")
    def test_multiple_markers_resolve_first_by_canonical_order(self):
        """Two stamped companions collapse to the lower-pk one in pool order."""
        self._equalize_scores()
        self._arouse(85)
        first = self._companion("martyr first")
        second = self._companion("martyr second")
        ordered = sorted((first, second), key=lambda entity: int(entity.pk))
        engage(self.player, self.monster)
        self._knock_out(first)
        self._knock_out(second)
        # Stamped out of canonical order: the pool order decides.
        self._stamp(
            self._companion_session_id(second),
            self._companion_session_id(first),
        )
        with self._patch_rolls(lambda i: 0, lambda i: 1):
            result = forfeit(self.player)
        acts = [
            e for e in _aftermath_entries(result) if e.kind == "violation_act"
        ]
        self.assertGreater(len(acts), 0)
        self.assertTrue(
            all(e.target == str(ordered[0].key) for e in acts),
            "the first canonical-order marker absorbs every attempt",
        )

    @covers_requirement("church-ordination::martyrdom-vow-collapses-the-defeat-aftermath-victim-pool-to-the-marked-martyr")
    def test_marker_died_or_fled_falls_back_to_the_normal_pool(self):
        """A dead or fled marker cannot collapse the pool."""
        self._equalize_scores()
        self._arouse(85)
        draws = []

        def target_roll(attempt_index):
            draws.append("target")
            return 0

        def resist_roll(attempt_index):
            draws.append("resist")
            return 1

        # Died: the stamped companion sits at 0 HP (kill semantics) — the
        # filter finds no survivor and the normal pool draws normally.
        died = self._companion("dead martyr")
        self._companion("standing martyr")
        engage(self.player, self.monster)
        self._knock_out(died)
        died.traits.hp.current = 0
        died.traits.hp.base = 0
        self._stamp(self._companion_session_id(died))
        draws.clear()
        with self._patch_rolls(target_roll, resist_roll):
            result = forfeit(self.player)
        acts = [
            e for e in _aftermath_entries(result) if e.kind == "violation_act"
        ]
        self.assertGreater(len(acts), 0)
        self.assertIn("target", draws, "a dead marker keeps the normal pool draw")

        # Fled: the stamped companion left the fight — no eligible martyr, so
        # the normal pool (player + the standing knockout) draws normally.
        fled = self._companion("fled martyr")
        standing = self._companion("fled companion standing")
        engage(self.player, self.monster)
        self._knock_out(fled)
        self._knock_out(standing)
        self._flee(fled)
        self._stamp(self._companion_session_id(fled))
        draws.clear()
        with self._patch_rolls(target_roll, resist_roll):
            result = forfeit(self.player)
        acts = [
            e for e in _aftermath_entries(result) if e.kind == "violation_act"
        ]
        self.assertGreater(len(acts), 0)
        self.assertIn("target", draws, "a fled marker keeps the normal pool draw")


class MartyrVictoryConsumptionTests(MartyrVowBase):
    """Victory spends the stamp on the durable record write."""

    @covers_requirement("church-ordination::martyrdom-vow-collapses-the-defeat-aftermath-victim-pool-to-the-marked-martyr")
    def test_victory_consumes_the_stamp(self):
        engage(self.player, self.monster)
        record = read_session(self.player)
        self._stamp(record.session_id)
        captured: dict[str, object] = {}
        real_persist = __import__(
            "world.rules.combat_session",
            fromlist=["settlement"],
        ).settlement._persist

        def capturing(_actor, persisted):
            captured["record"] = persisted
            real_persist(_actor, persisted)

        with patch(
            "world.rules.combat_session.settlement._persist", side_effect=capturing
        ):
            with self.captureOnCommitCallbacks(execute=True):
                settle_session(self.player, read_session(self.player), None, "victory")
        persisted = captured["record"]
        self.assertIsNotNone(persisted.settled_tick)
        self.assertIsNone(
            persisted.martyr_key,
            "victory consumes the martyr stamp on the durable record",
        )


class MartyrRollbackDeterminismTests(MartyrVowBase):
    """A rolled-back stamped settlement re-derives the identical collapse."""

    @covers_requirement("church-ordination::martyrdom-vow-collapses-the-defeat-aftermath-victim-pool-to-the-marked-martyr")
    def test_rolled_back_stamped_settlement_rederives_identically(self):
        self._equalize_scores()
        self._arouse(85)
        engage(self.player, self.monster)
        record = read_session(self.player)
        self._stamp(record.session_id)
        calls = []

        def recording_roll(*args):
            calls.append(args)
            # Resist contests draw their normal persistence value (a landed
            # contest); the collapsed pool never touches the target purpose.
            # State-derived-draw identity is the sibling rollback slice's
            # contract; this slice pins the stamp's collapse determinism.
            return 1 if args[4] == "resist" else 0

        violation_module = defeat_aftermath_violation_module
        state = {"failed": False}

        def fail_then_advance(*args, **kwargs):
            if not state["failed"]:
                state["failed"] = True
                raise RuntimeError("injected advance failure")
            return None

        with patch.object(
            violation_module,
            "_advance_attempt_clock",
            side_effect=fail_then_advance,
        ), patch.object(
            violation_module, "derived_roll", side_effect=recording_roll
        ):
            with self.assertRaises(RuntimeError):
                forfeit(self.player)
        first_run_calls = list(calls)
        self.assertGreater(len(first_run_calls), 0)
        # The durable session is still active after the rollback; the retry is
        # a bare re-settlement (no re-engage, no extra round) that must
        # re-derive the identical draw sequence over the same collapsed pool.
        calls.clear()
        with patch.object(
            violation_module, "derived_roll", side_effect=recording_roll
        ):
            result = forfeit(self.player)
        # The completed retry re-derives the identical draws for the same
        # durable state (the aborted run covers its first attempt's resist),
        # then finishes the second attempt it never reached.
        self.assertEqual(calls[: len(first_run_calls)], first_run_calls)
        self.assertGreater(len(calls), len(first_run_calls))
        acts = [
            e for e in _aftermath_entries(result) if e.kind == "violation_act"
        ]
        self.assertGreater(len(acts), 0)
        self.assertTrue(
            all(e.target == str(self.player.key) for e in acts),
            "the collapsed martyr pool persists through the retry",
        )
        self.assertTrue(
            all(call[4] != "target" for call in calls),
            "a collapsed martyr pool consumes zero target rolls on the retry",
        )


class MartyrCastRailTests(MartyrVowBase):
    """The ``session_stamp`` effect handler behind the cast pipeline."""

    def _synth_vow_skill(self, effect_id: str):
        from dataclasses import replace

        from world.rules.tests._combat_session_helpers import (
            open_synthetic_scope,
            synth_damage_skill,
        )

        skill = replace(
            synth_damage_skill(
                "t_rite_vow",
                "合成殉者之誓",
                effects=(effect_id,),
                target_spec=TargetSpec.SELF,
            ),
            usable_out_of_combat=True,
        )
        open_synthetic_scope(
            self,
            "skills",
            "elements",
            extra={"skills": {skill.key: skill}},
        )
        self.player.db.skills = {"active": [skill.key], "passive": []}
        return skill

    def _combat_request(self, skill):
        return ActionRequest(
            self.player,
            skill.key,
            [self.player],
            context=BattlefieldActionContext(
                _active_battlefield_for(self.player)
            ),
        )

    @covers_requirement("church-ordination::martyrdom-vow-collapses-the-defeat-aftermath-victim-pool-to-the-marked-martyr")
    def test_vow_cast_stamps_the_active_session(self):
        skill = self._synth_vow_skill("session_stamp:martyr_key")
        engage(self.player, self.monster)
        result = ActionResolver.resolve(self._combat_request(skill))
        self.assertEqual(result.outcome, "success")
        record = read_session(self.player)
        self.assertEqual(record.martyr_key, (record.session_id,))

    @covers_requirement("church-ordination::martyrdom-vow-collapses-the-defeat-aftermath-victim-pool-to-the-marked-martyr")
    def test_vow_cast_outside_a_fight_is_rejected(self):
        skill = self._synth_vow_skill("session_stamp:martyr_key")
        from world.rules.targeting import RoomActionContext

        request = ActionRequest(
            self.player,
            skill.key,
            [self.player],
            context=RoomActionContext(self.room),
        )
        result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "rejected")
        self.assertEqual(result.reason.value, "action_forbidden")

    @covers_requirement("church-ordination::martyrdom-vow-collapses-the-defeat-aftermath-victim-pool-to-the-marked-martyr")
    def test_round_end_persist_preserves_the_stamp_from_an_in_combat_cast(self):
        """A mid-round cast survives the round's durability merge."""
        skill = self._synth_vow_skill("session_stamp:martyr_key")
        engage(self.player, self.monster)
        with patch("world.rules.combat.battlefield.roll_d100", return_value=1), patch(
            "world.rules.combat.damage.roll_d100", return_value=1
        ), patch("world.rules.combat.rounds.roll_d100", return_value=1):
            # The combat facade accepts no SELF target field: the SELF spec
            # binds the actor inside the resolver.
            result = submit_player_action(self.player, skill.key, [])
        self.assertEqual(result["outcome"], "round")
        record = read_session(self.player)
        self.assertIsNotNone(record)
        self.assertEqual(
            record.martyr_key,
            (record.session_id,),
            "the round-end persist must compose from the live durable record",
        )

    def test_session_stamp_unknown_field_is_rejected(self):
        skill = self._synth_vow_skill("session_stamp:not_a_field")
        engage(self.player, self.monster)
        result = ActionResolver.resolve(self._combat_request(skill))
        self.assertEqual(result.outcome, "rejected")
        self.assertEqual(result.reason.value, "effect_resolution_failed")


class LambSealSessionEndTests(MartyrVowBase):
    """The seal lifts with the fight (design §5.7: ends with the fight)."""

    @covers_requirement("church-ordination::lamb-mark-narrows-monster-target-preference-with-a-charging-buff")
    def test_session_clear_sweeps_the_bearer_lamb_seal(self):
        apply_buff(self.player, "lamb_seal")
        engage(self.player, self.monster)
        with patch("world.rules.combat.battlefield.roll_d100", return_value=1), patch(
            "world.rules.combat.damage.roll_d100", return_value=1
        ), patch("world.rules.combat.rounds.roll_d100", return_value=1):
            with self.captureOnCommitCallbacks(execute=True):
                settle_session(
                    self.player,
                    read_session(self.player),
                    None,
                    "victory",
                )
        self.assertNotIn(
            "lamb_seal",
            entity_active_buffs(self.player),
            "the seal ends with the fight",
        )
