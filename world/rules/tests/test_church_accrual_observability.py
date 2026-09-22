"""Observability and AI-dead contract for the church accrual paths.

The accrual paths (pray, offering accept/decline, enrolled climax) are part
of the offline deterministic loop: no ``world/ai/`` module participates, all
state writes sit inside ``transaction.atomic()``, and the three events flow
only through the ``world.observability`` facade, commit-bound. This module
runs the whole surface with the dialogue model stubbed to raise and asserts
the commit-bound events, the rolled-back silence, and the stable player-
facing rejection lines. Synthetic entities only; row keys are read from the
live menu, never literal shipped content.
"""

from unittest.mock import patch

from django.db import transaction

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from commands.church import CmdChurchOffer, CmdChurchPray
from world.lore.church.places import resolve_church_place_keys
from world.rules import church
from world.rules.clock import WorldClock
from world.rules.sexual_state import _apply_climax_phase_set
from world.rules.state_reactions import dispatch_phase_reaction  # noqa: F401  (import registers the canonical phase dispatcher)

PRAY_EVENT = "church_pray"
ACCEPTED_EVENT = "church_offering_accepted"
DECLINED_EVENT = "church_offering_declined"


class ChurchAccrualObservabilityBase(EvenniaCommandTestMixin, EvenniaTest):
    """An enrolled character in a church-flagged venue beside a recipient."""

    def setUp(self):
        super().setUp()
        self.clock = WorldClock(tick=0)
        self._clock_patch = patch(
            "world.rules.church.get_world_clock", return_value=self.clock
        )
        self._clock_patch.start()
        self.addCleanup(self._clock_patch.stop)
        self.hall = create_object(Room, key="t_obs_hall")
        place_key = next(iter(resolve_church_place_keys()))
        self.hall.tags.add(place_key)
        self.char1.location = self.hall
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.recipient = create_object(NPC, key="t_obs_recipient", location=self.hall)
        self.recipient.race = "human"
        self.recipient.apply_race_baseline()
        from world.quests.catalog import register_catalog

        register_catalog()
        church.add_merit(self.char1, 0)

    def _events(self, info_mock):
        return [call.args[0] for call in info_mock.call_args_list if call.args]

    def _unenrolled(self, key: str = "t_obs_newcomer") -> PlayerCharacter:
        character = create_object(PlayerCharacter, key=key)
        character.race = "human"
        character.apply_race_baseline()
        character.location = self.hall
        return character

    def _row_key(self) -> str:
        return church.offering_menu(self.char1)[0].key


class ChurchAccrualAiDeadSmokeTests(ChurchAccrualObservabilityBase):
    """The prayer/offering/climax closed loop with every LLM service dead."""

    @covers_requirement(
        "church-ordination::the-accrual-paths-are-offline-deterministic-with-commit-bound-observability"
    )
    def test_the_accrual_paths_run_and_emit_at_commit_with_ai_dead(self):
        raised = AssertionError("the dialogue model must not participate")
        with patch(
            "world.ai.npc_dialogue.generate_npc_reply", side_effect=raised
        ):
            # Prayer.
            with (
                patch("world.rules.church.log_info") as info_pray,
                self.captureOnCommitCallbacks(execute=True),
            ):
                result = church.pray_step(self.char1)
            self.assertEqual(result["outcome"], "prayed")
            self.assertIn(PRAY_EVENT, self._events(info_pray))

            # Offering accept.
            self.recipient.sexual.pleasure.base = 85
            with (
                patch("world.rules.church.roll_d100", return_value=10),
                patch("world.rules.church.log_info") as info_accept,
                self.captureOnCommitCallbacks(execute=True),
            ):
                result = church.offer_step(
                    self.char1, self.recipient, self._row_key()
                )
            self.assertEqual(result["outcome"], "accepted")
            self.assertIn(ACCEPTED_EVENT, self._events(info_accept))

            # Offering decline.
            self.recipient.sexual.pleasure.base = 0
            with (
                patch("world.rules.church.roll_d100", return_value=99),
                patch("world.rules.church.log_info") as info_decline,
                self.captureOnCommitCallbacks(execute=True),
            ):
                result = church.offer_step(
                    self.char1, self.recipient, self._row_key()
                )
            self.assertEqual(result["outcome"], "declined")
            self.assertIn(DECLINED_EVENT, self._events(info_decline))

            # Enrolled climax accrual (event-less by contract, mechanical).
            before = church.merit(self.char1)
            _apply_climax_phase_set(self.char1, "接近")
            _apply_climax_phase_set(self.char1, "進行中")
            self.assertGreater(church.merit(self.char1), before)


class ChurchAccrualRollbackSilenceTests(ChurchAccrualObservabilityBase):
    """A rolled-back church transaction emits no facade event."""

    @covers_requirement(
        "church-ordination::the-accrual-paths-are-offline-deterministic-with-commit-bound-observability"
    )
    def test_a_rolled_back_prayer_emits_nothing(self):
        real_write = church._write_ledger

        def write_then_raise(entity, mutate):
            real_write(entity, mutate)
            raise RuntimeError("simulated prayer failure")

        with (
            patch("world.rules.church._write_ledger", side_effect=write_then_raise),
            patch("world.rules.church.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
            self.assertRaises(RuntimeError),
        ):
            church.pray_step(self.char1)
        self.assertEqual(self._events(info), [])

    @covers_requirement(
        "church-ordination::the-accrual-paths-are-offline-deterministic-with-commit-bound-observability"
    )
    def test_a_rolled_back_acceptance_emits_nothing(self):
        real_write = church._write_ledger

        def write_then_raise(entity, mutate):
            real_write(entity, mutate)
            raise RuntimeError("simulated offering failure")

        self.recipient.sexual.pleasure.base = 85
        with (
            patch("world.rules.church._write_ledger", side_effect=write_then_raise),
            patch("world.rules.church.roll_d100", return_value=10),
            patch("world.rules.church.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
            self.assertRaises(RuntimeError),
        ):
            church.offer_step(self.char1, self.recipient, self._row_key())
        self.assertEqual(self._events(info), [])

    @covers_requirement(
        "church-ordination::the-accrual-paths-are-offline-deterministic-with-commit-bound-observability"
    )
    def test_a_rolled_back_decline_emits_nothing(self):
        # The decline registers its event inside its own empty atomic; a
        # caller's outer rollback must discard that registration too.
        self.recipient.sexual.pleasure.base = 0
        with (
            patch("world.rules.church.roll_d100", return_value=99),
            patch("world.rules.church.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            with transaction.atomic():
                result = church.offer_step(
                    self.char1, self.recipient, self._row_key()
                )
                self.assertEqual(result["outcome"], "declined")
                transaction.set_rollback(True)
        self.assertEqual(self._events(info), [])

    @covers_requirement(
        "church-ordination::the-accrual-paths-are-offline-deterministic-with-commit-bound-observability"
    )
    def test_a_rolled_back_prayer_emits_nothing_from_an_ambient_wrapper(self):
        with (
            patch("world.rules.church.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            with transaction.atomic():
                church.pray_step(self.char1)
                transaction.set_rollback(True)
        self.assertEqual(self._events(info), [])


class ChurchAccrualStableRejectionTests(ChurchAccrualObservabilityBase):
    """Every failure mode renders its stable player-facing line."""

    def test_unenrolled_pray_is_a_stable_rejection(self):
        self.call(
            CmdChurchPray(), "", "你尚未入教。請先與主祭交談", caller=self._unenrolled()
        )

    def test_outside_venue_pray_is_a_stable_rejection(self):
        elsewhere = create_object(Room, key="t_obs_street")
        self.char1.location = elsewhere
        self.call(CmdChurchPray(), "", "這裡並非教會聖所")

    def test_daily_cap_pray_is_a_stable_rejection(self):
        for _ in range(3):
            church.pray_step(self.char1)
        self.call(CmdChurchPray(), "", "你今天已經祈禱夠了")

    def test_unowned_offer_row_is_a_stable_rejection(self):
        self.call(
            CmdChurchOffer(),
            f"{self.recipient.key} offering_t_never_owned",
            "你尚未掌握這項服務",
        )

    def test_unknown_offer_target_is_a_stable_rejection(self):
        self.call(CmdChurchOffer(), "t_no_such_npc", "那不是你可以服務的對象")

    def test_unenrolled_offer_is_a_stable_rejection(self):
        self.call(
            CmdChurchOffer(),
            self.recipient.key,
            "你尚未入教。請先與主祭交談",
            caller=self._unenrolled(),
        )

    @covers_requirement(
        "church-ordination::the-accrual-paths-are-offline-deterministic-with-commit-bound-observability"
    )
    def test_npc_decline_is_a_stable_rejection(self):
        self.recipient.sexual.pleasure.base = 0
        with patch("world.rules.church.roll_d100", return_value=99):
            self.call(
                CmdChurchOffer(),
                f"{self.recipient.key} {self._row_key()}",
                "她婉拒了你的服務",
            )