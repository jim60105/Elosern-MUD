"""The cross-change end-to-end proof (church design §6/§7, delta requirement 3).

The full sub-project-1 loop — ``church join`` → ``church pray`` → ``church
offer`` → enrolled climax accrual → ``church redeem`` — executes as ONE
registered integration test with every LLM service stubbed to raise, all five
observability events observed at their commits, deterministic with AI dead. A
rollback-silence test pins that a rolled-back church transaction emits no
facade event. Every balance number is read live (offering menu rows, the
redemption catalogue's cheapest entry, the prayed/offered accruals) — never a
shipped literal — so the loop is the archive-gate proof: if any predecessor
change's fincal drifted, this test IS the regression signal.
"""

from unittest.mock import patch

from django.db import transaction

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.components import ChurchHost
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.lore.church.places import resolve_church_place_keys
from world.rules import church
from world.rules.clock import WorldClock
from world.rules.sexual_state import _apply_climax_phase_set

# Importing the reaction engine registers the canonical phase dispatcher, so
# the enrolled climax accrual fires through the same registered rail the
# shipped game runs.
from world.rules import state_reactions  # noqa: F401

ENROLL_EVENT = "church_enrolled"
PRAY_EVENT = "church_pray"
ACCEPTED_EVENT = "church_offering_accepted"
DECLINED_EVENT = "church_offering_declined"
REDEEM_EVENT = "church_skill_redeemed"

_ALL_EVENTS = (
    ENROLL_EVENT,
    PRAY_EVENT,
    ACCEPTED_EVENT,
    DECLINED_EVENT,
    REDEEM_EVENT,
)


class ChurchCombatMinistryLoopBase(EvenniaTest):
    """An unenrolled character in a church venue beside a ChurchHost."""

    def setUp(self):
        super().setUp()
        self.clock = WorldClock(tick=0)
        self._clock_patch = patch(
            "world.rules.church.get_world_clock", return_value=self.clock
        )
        self._clock_patch.start()
        self.addCleanup(self._clock_patch.stop)
        self.hall = create_object(Room, key="t_loop_hall")
        place_key = next(iter(resolve_church_place_keys()))
        self.hall.tags.add(place_key)
        self.char1.location = self.hall
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.celebrant = create_object(NPC, key="t_loop_celebrant", location=self.hall)
        self.component = ChurchHost.create(self.celebrant, service_id="t_loop_celebrant")
        self.celebrant.components.add(self.component)
        self.recipient = create_object(NPC, key="t_loop_recipient", location=self.hall)
        self.recipient.race = "human"
        self.recipient.apply_race_baseline()
        from world.quests.catalog import register_catalog

        register_catalog()

    def _events(self, info_mock):
        return [call.args[0] for call in info_mock.call_args_list if call.args]

    def _row_key(self) -> str:
        return church.offering_menu(self.char1)[0].key

    def _cheapest_entry(self):
        listing = church.redemption_catalogue(self.char1)
        return min((row for row, _ in listing), key=lambda row: row.merit_price)


class ChurchCombatMinistryLoopTests(ChurchCombatMinistryLoopBase):
    """The full loop with every LLM service dead (delta scenario)."""

    @covers_requirement("church-ordination::the-combat-rails-are-offline-deterministic-and-the-full-church-loop-runs-end-to-end-with-ai-dead")
    def test_the_full_loop_runs_end_to_end_with_ai_dead(self):
        raised = AssertionError("the dialogue model must not participate")
        with patch("world.ai.npc_dialogue.generate_npc_reply", side_effect=raised):
            # 1. Join: the ledger-levelled enrollment rite, one commit event.
            with (
                patch("world.rules.church.log_info") as info,
                self.captureOnCommitCallbacks(execute=True),
            ):
                record = church.enroll(self.char1, self.celebrant)
            self.assertFalse(record["vessel_branch"])
            self.assertIn(ENROLL_EVENT, self._events(info))

            # 2. Pray: venue-gated, time-costed, daily-capped accrual.
            with (
                patch("world.rules.church.log_info") as info,
                self.captureOnCommitCallbacks(execute=True),
            ):
                result = church.pray_step(self.char1)
            self.assertEqual(result["outcome"], "prayed")
            self.assertIn(PRAY_EVENT, self._events(info))
            # Two more prayers fill the daily cap for the merit base.
            for _ in range(2):
                with self.captureOnCommitCallbacks(execute=True):
                    church.pray_step(self.char1)

            target = self._cheapest_entry()

            # 3. Offering accept + decline: the two settlement events.
            row_key = self._row_key()
            self.recipient.sexual.pleasure.base = 85
            with (
                patch("world.rules.church.roll_d100", return_value=10),
                patch("world.rules.church.log_info") as info,
                self.captureOnCommitCallbacks(execute=True),
            ):
                result = church.offer_step(self.char1, self.recipient, row_key)
            self.assertEqual(result["outcome"], "accepted")
            self.assertIn(ACCEPTED_EVENT, self._events(info))
            self.recipient.sexual.pleasure.base = 0
            with (
                patch("world.rules.church.roll_d100", return_value=99),
                patch("world.rules.church.log_info") as info,
                self.captureOnCommitCallbacks(execute=True),
            ):
                result = church.offer_step(self.char1, self.recipient, row_key)
            self.assertEqual(result["outcome"], "declined")
            self.assertIn(DECLINED_EVENT, self._events(info))

            # 4. Enrolled climax accrual: mechanical, event-less by contract.
            before = church.merit(self.char1)
            _apply_climax_phase_set(self.char1, "接近")
            _apply_climax_phase_set(self.char1, "進行中")
            self.assertGreater(church.merit(self.char1), before)

            # 5. Fund the cheapest catalogue entry through accepted offerings,
            # then redeem it: one all-or-nothing grace purchase, one event.
            self.recipient.sexual.pleasure.base = 85
            offers = 0
            while church.merit(self.char1) < target.merit_price:
                offers += 1
                self.assertLessEqual(offers, 300, "offering funding loop bound")
                # The clergy may climax mid-ministry: riding 進行中 locks her
                # actions (combat rule climax_in_progress_locks_actions), so
                # the afterglow lift restores her ministerial capability —
                # the same deterministic edge the shipped game walks.
                if self.char1.sexual.climax_phase.level == "進行中":
                    _apply_climax_phase_set(self.char1, "餘韻")
                with (
                    patch("world.rules.church.roll_d100", return_value=10),
                    self.captureOnCommitCallbacks(execute=True),
                ):
                    church.offer_step(self.char1, self.recipient, self._row_key())
            with (
                patch("world.rules.church.log_info") as info,
                self.captureOnCommitCallbacks(execute=True),
            ):
                church.redeem_step(self.char1, target.skill_key)
            self.assertIn(REDEEM_EVENT, self._events(info))
            self.assertIn(target.skill_key, church.redeemed_keys(self.char1))

    @covers_requirement("church-ordination::the-combat-rails-are-offline-deterministic-and-the-full-church-loop-runs-end-to-end-with-ai-dead")
    def test_rolled_back_loop_transaction_emits_no_events(self):
        """A rolled-back church transaction leaves the facade silent."""
        raised = AssertionError("the dialogue model must not participate")
        with patch(
            "world.ai.npc_dialogue.generate_npc_reply", side_effect=raised
        ):
            with (
                patch("world.rules.church.log_info") as info,
                self.captureOnCommitCallbacks(execute=True),
            ):
                with transaction.atomic():
                    church.enroll(self.char1, self.celebrant)
                    transaction.set_rollback(True)
            self.assertEqual(
                self._events(info), [], "no facade event survives a rollback"
            )
            # The DB — not the transaction-unaware in-memory attribute cache —
            # proves the ledger write never landed.
            from evennia.objects.models import ObjectDB

            through = ObjectDB.db_attributes.through
            persisted = {
                getattr(row, "attribute").db_key
                for row in through.objects.filter(objectdb__pk=self.char1.pk)
            }
            self.assertFalse(
                {"church", "skills", "inventory"} & persisted,
                "a rolled-back enrollment leaves no persisted state",
            )
