"""Data-contract test: church accrual tune finals and the offering baseline

Pins the shipped church tune finals and the shipped baseline over the live
rulebook/catalogue: the pray tuning, the exhaustive acceptance-curve matrix
(ordinal x boundary die over the decided finals), the offering menu's seed
rows, and the climax-while-enrolled accrual final. The ``implement-church-
accrual`` change (design §5.2/§5.3/§5.4) turns those finals into behaviour —
venue-bound prayer, the explicit-selection offering judged by arousal and
injected dice (never affinity), the side-reaction climax accrual — this module
proves the dynamics consume exactly the tuned numbers. Synthetic entities and
synthetic catalogue rows carry ``t_`` keys.
"""

from copy import deepcopy
from dataclasses import replace
from unittest.mock import patch

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.lore.church import OFFERING_CATALOG, OfferingRow
from world.lore.church.places import resolve_church_place_keys
from world.rules import church
from world.rules.church import (
    OfferingError,
    OfferingReason,
    PrayerError,
    PrayerReason,
)
from world.rules.church_rulebook import get_church_rules
from world.rules.clock import CLOCK_YAML, WorldClock
from world.rules.sexual_state import _apply_climax_phase_set
from world.rules.state_reactions import dispatch_phase_reaction  # noqa: F401  (import registers the canonical phase dispatcher)

_DAY_SECONDS = CLOCK_YAML["seconds_per_hour"] * CLOCK_YAML["hours_per_day"]

#: The tuned acceptance curve finals (church.yaml ``acceptance`` rows) and the
#: arousal band floors they map from (``sexual_pleasure.yaml``): ordinal ->
#: (band floor pleasure, accept percent). The loader's monotonicity gate pins
#: the shape; the matrix here proves the runtime decision consumes exactly
#: (ordinal, roll).
_CURVE = (
    (0, 0, 50),
    (1, 15, 65),
    (2, 35, 80),
    (3, 60, 90),
    (4, 85, 100),
)

#: The shipped climax-while-enrolled accrual final (church.yaml
#: ``accrual_climax_while_enrolled``; design §5.4 "small").
CLIMAX_ACCRUAL = get_church_rules().accrual["accrual_climax_while_enrolled"]


def _synthetic_offering_row(key: str, act_key: str) -> OfferingRow:
    """One synthetic catalogue row the player never owns."""
    return OfferingRow(key=key, act_key=act_key, merit=1, copper=None)


class ChurchAccrualBase(EvenniaTest):
    """An enrolled character in a church-flagged venue, with a frozen clock."""

    def setUp(self):
        super().setUp()
        self.clock = WorldClock(tick=0)
        self._clock_patch = patch(
            "world.rules.church.get_world_clock", return_value=self.clock
        )
        self._clock_patch.start()
        self.addCleanup(self._clock_patch.stop)
        self.hall = create_object(Room, key="t_church_hall")
        place_key = next(iter(resolve_church_place_keys()))
        self.hall.tags.add(place_key)
        self.char1.location = self.hall
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.recipient = create_object(NPC, key="t_recipient", location=self.hall)
        # An act target must be a living body: race traits (HP) come from the
        # baseline, exactly like any shipped NPC would carry.
        self.recipient.race = "human"
        self.recipient.apply_race_baseline()
        # The out-of-combat sexual-resist gate resolves quest definitions from
        # the quest catalog; a normal cast of a resistible act needs it.
        from world.quests.catalog import register_catalog

        register_catalog()
        # Materialize the ledger without the host machinery: the accrual
        # primitives only require an existing ledger.
        church.add_merit(self.char1, 0)

    def _events(self, info_mock):
        return [call.args[0] for call in info_mock.call_args_list if call.args]

    def _persisted_attribute_keys(self, character):
        from evennia.objects.models import ObjectDB

        through = ObjectDB.db_attributes.through
        return {
            getattr(row, "attribute").db_key
            for row in through.objects.filter(objectdb__pk=character.pk)
        }

    def _first_row_key(self) -> str:
        return church.offering_menu(self.char1)[0].key

    def _set_ordinal(self, entity, ordinal: int) -> None:
        entity.sexual.pleasure.base = _CURVE[ordinal][1]


class ChurchPrayTests(ChurchAccrualBase):
    """``pray_step``: time cost, merit, cap, venue, and rollback."""

    @covers_requirement(
        "church-ordination::prayer-is-a-time-costed-capped-venue-bound-accrual"
    )
    def test_a_prayer_spends_time_and_earns_merit(self):
        rules = get_church_rules().pray
        accrual = get_church_rules().accrual["accrual_pray_completed"]
        before = church.merit(self.char1)
        with (
            patch("world.rules.church.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            result = church.pray_step(self.char1)
        self.assertEqual(result["outcome"], "prayed")
        self.assertEqual(result["tick"], rules.duration_seconds)
        self.assertEqual(church.merit(self.char1), before + int(accrual["merit"]))
        self.assertEqual(church.daily(self.char1), {"day": 0, "pray": 1})
        (event,), kwargs = info.call_args
        self.assertEqual(event, "church_pray")
        self.assertEqual(kwargs["context"]["char"], str(self.char1))
        self.assertEqual(kwargs["context"]["tick"], rules.duration_seconds)

    @covers_requirement(
        "church-ordination::prayer-is-a-time-costed-capped-venue-bound-accrual"
    )
    def test_prayer_credits_the_accrual_row_as_the_authority(self):
        # The delta requires prayer to apply the ``pray_completed`` accrual
        # row; a divergence between the pray section and the accrual row must
        # resolve in the accrual row's favour.
        rules = get_church_rules()
        divergent = replace(
            rules,
            accrual={
                **rules.accrual,
                "accrual_pray_completed": {"merit": 7, "daily_cap": 3},
            },
        )
        before = church.merit(self.char1)
        with patch(
            "world.rules.church_rulebook.get_church_rules", return_value=divergent
        ):
            result = church.pray_step(self.char1)
        self.assertEqual(result["outcome"], "prayed")
        self.assertEqual(church.merit(self.char1), before + 7)
        self.assertEqual(result["tick"], rules.pray.duration_seconds)

    @covers_requirement(
        "church-ordination::prayer-is-a-time-costed-capped-venue-bound-accrual"
    )
    def test_the_daily_cap_rejects_cleanly(self):
        rules = get_church_rules().pray
        for _ in range(rules.daily_cap):
            church.pray_step(self.char1)
        self.assertEqual(
            church.daily(self.char1), {"day": 0, "pray": rules.daily_cap}
        )
        before_merit = church.merit(self.char1)
        with (
            patch("world.rules.church.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            with self.assertRaises(PrayerError) as caught:
                church.pray_step(self.char1)
        self.assertEqual(caught.exception.args[0], PrayerReason.DAILY_CAP)
        self.assertEqual(
            self.clock.tick, rules.duration_seconds * rules.daily_cap
        )
        self.assertEqual(church.merit(self.char1), before_merit)
        self.assertEqual(self._events(info), [])

    @covers_requirement(
        "church-ordination::prayer-is-a-time-costed-capped-venue-bound-accrual"
    )
    def test_outside_a_church_venue_rejects_cleanly(self):
        elsewhere = create_object(Room, key="t_not_a_venue")
        self.char1.location = elsewhere
        before = deepcopy(church.read_ledger(self.char1))
        with (
            patch("world.rules.church.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            with self.assertRaises(PrayerError) as caught:
                church.pray_step(self.char1)
        self.assertEqual(caught.exception.args[0], PrayerReason.OUTSIDE_VENUE)
        self.assertEqual(self.clock.tick, 0)
        self.assertEqual(church.read_ledger(self.char1), before)
        self.assertEqual(self._events(info), [])

    @covers_requirement(
        "church-ordination::prayer-is-a-time-costed-capped-venue-bound-accrual"
    )
    def test_the_unenrolled_are_told_to_speak_with_the_celebrant(self):
        fresh = create_object(PlayerCharacter, key="t_never_enrolled")
        fresh.race = "human"
        fresh.apply_race_baseline()
        fresh.location = self.hall
        with (
            patch("world.rules.church.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            with self.assertRaises(PrayerError) as caught:
                church.pray_step(fresh)
        self.assertEqual(caught.exception.args[0], PrayerReason.NOT_ENROLLED)
        self.assertEqual(self._events(info), [])
        self.assertEqual(self.clock.tick, 0)

    def test_a_malformed_ledger_is_a_stable_inert_rejection(self):
        self.char1.db.church = "not_a_mapping"
        before_wallet = int(self.char1.db.wallet or 0)
        with self.assertRaises(PrayerError) as caught:
            church.pray_step(self.char1)
        self.assertEqual(caught.exception.args[0], PrayerReason.MALFORMED_LEDGER)
        self.assertEqual(self.clock.tick, 0)
        self.assertEqual(int(self.char1.db.wallet or 0), before_wallet)

    def test_a_non_player_actor_is_rejected(self):
        room = create_object(Room, key="t_prayer_room")
        with self.assertRaises(PrayerError) as caught:
            church.pray_step(room)
        self.assertEqual(caught.exception.args[0], PrayerReason.NOT_A_PLAYER)

    @covers_requirement(
        "church-ordination::prayer-is-a-time-costed-capped-venue-bound-accrual"
    )
    def test_the_daily_counters_reset_across_a_clock_day_boundary(self):
        rules = get_church_rules().pray
        for _ in range(rules.daily_cap):
            church.pray_step(self.char1)
        # The world moves to the next day; the lazy reset lets her pray again.
        self.clock.tick += _DAY_SECONDS
        with (
            patch("world.rules.church.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            result = church.pray_step(self.char1)
        self.assertEqual(result["outcome"], "prayed")
        self.assertEqual(church.daily(self.char1)["pray"], 1)
        self.assertEqual(self._events(info), ["church_pray"])

    @covers_requirement(
        "church-ordination::prayer-is-a-time-costed-capped-venue-bound-accrual"
    )
    def test_a_rolled_back_prayer_restores_clock_ledger_and_events(self):
        real_write = church._write_ledger

        def write_then_raise(entity, mutate):
            real_write(entity, mutate)
            raise RuntimeError("simulated post-write prayer failure")

        before = deepcopy(church.read_ledger(self.char1))
        with (
            patch("world.rules.church._write_ledger", side_effect=write_then_raise),
            patch("world.rules.church.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
            self.assertRaises(RuntimeError),
        ):
            church.pray_step(self.char1)
        self.assertEqual(self.clock.tick, 0)
        self.assertEqual(church.read_ledger(self.char1), before)
        self.assertEqual(self._events(info), [])


class ChurchOfferingMenuTests(ChurchAccrualBase):
    """The row menu is a projection over owned acts, never a copy."""

    @covers_requirement(
        "church-ordination::sexual-offering-is-explicit-selection-ministry-gated-on-the-npc-s-arousal-never-affinity"
    )
    def test_menu_projects_exactly_the_owned_catalogue_rows(self):
        planted = _synthetic_offering_row("offering_t_gated", "t_never_owned")
        with patch(
            "world.rules.church.OFFERING_CATALOG", OFFERING_CATALOG + (planted,)
        ):
            menu = church.offering_menu(self.char1)
        keys = {row.key for row in menu}
        self.assertNotIn("offering_t_gated", keys)
        self.assertTrue(keys, "a fresh character owns every seed act")
        owned = set(self.char1.skills.owned_keys())
        for row in menu:
            self.assertIn(row.act_key, owned)

    @covers_requirement(
        "church-ordination::sexual-offering-is-explicit-selection-ministry-gated-on-the-npc-s-arousal-never-affinity"
    )
    def test_unowned_or_unknown_row_keys_are_stable_rejections(self):
        with self.assertRaises(OfferingError) as caught:
            church.offer_step(self.char1, self.recipient, "offering_t_never_owned")
        self.assertEqual(caught.exception.args[0], OfferingReason.ROW_NOT_UNLOCKED)
        planted = _synthetic_offering_row("offering_t_gated", "t_never_owned")
        with patch(
            "world.rules.church.OFFERING_CATALOG", OFFERING_CATALOG + (planted,)
        ):
            with self.assertRaises(OfferingError) as caught:
                church.offer_step(self.char1, self.recipient, "offering_t_gated")
            self.assertEqual(caught.exception.args[0], OfferingReason.ROW_NOT_UNLOCKED)


class ChurchOfferingAcceptanceTests(ChurchAccrualBase):
    """The exhaustive ordinal x boundary-die curve matrix, never affinity."""

    @covers_requirement(
        "church-ordination::sexual-offering-is-explicit-selection-ministry-gated-on-the-npc-s-arousal-never-affinity"
    )
    def test_acceptance_follows_the_curve_for_every_ordinal(self):
        row_key = self._first_row_key()
        for ordinal, pleasure, percent in _CURVE:
            with self.subTest(ordinal=ordinal, percent=percent):
                self._set_ordinal(self.recipient, ordinal)
                self.assertEqual(self.recipient.sexual.arousal.value, ordinal)
                # The boundary die itself accepts (roll == percent).
                with patch("world.rules.church.roll_d100", return_value=percent):
                    result = church.offer_step(self.char1, self.recipient, row_key)
                    self.assertEqual(result["outcome"], "accepted")
                # The first die past the boundary declines.
                with patch("world.rules.church.roll_d100", return_value=percent + 1):
                    result = church.offer_step(self.char1, self.recipient, row_key)
                    self.assertEqual(result["outcome"], "declined")

    @covers_requirement(
        "church-ordination::sexual-offering-is-explicit-selection-ministry-gated-on-the-npc-s-arousal-never-affinity"
    )
    def test_ordinal_zero_accepts_exactly_inside_its_half_band(self):
        row_key = self._first_row_key()
        self._set_ordinal(self.recipient, 0)
        for roll in (1, 25, 50):
            with patch("world.rules.church.roll_d100", return_value=roll):
                self.assertEqual(
                    church.offer_step(self.char1, self.recipient, row_key)["outcome"],
                    "accepted",
                )
        for roll in (51, 75, 100):
            with patch("world.rules.church.roll_d100", return_value=roll):
                self.assertEqual(
                    church.offer_step(self.char1, self.recipient, row_key)["outcome"],
                    "declined",
                )

    @covers_requirement(
        "church-ordination::sexual-offering-is-explicit-selection-ministry-gated-on-the-npc-s-arousal-never-affinity"
    )
    def test_the_top_ordinal_accepts_unconditionally(self):
        row_key = self._first_row_key()
        self._set_ordinal(self.recipient, 4)
        for roll in (1, 50, 100):
            with patch("world.rules.church.roll_d100", return_value=roll):
                self.assertEqual(
                    church.offer_step(self.char1, self.recipient, row_key)["outcome"],
                    "accepted",
                )

    @covers_requirement(
        "church-ordination::sexual-offering-is-explicit-selection-ministry-gated-on-the-npc-s-arousal-never-affinity"
    )
    def test_acceptance_is_monotonic_in_the_ordinal_for_a_fixed_die(self):
        # Decision-only probe: the acceptance decision is made before any act
        # executes, so the pipeline is stubbed here to keep the probe free of
        # act side effects (the rails themselves are proven in the settlement
        # tests) — the property under test is that the decision never
        # regresses as the ordinal rises.
        from world.rules.action import ActionResolver, ActionResult

        row_key = self._first_row_key()
        with patch.object(
            ActionResolver,
            "resolve",
            return_value=ActionResult.success(None, 0),
        ):
            for roll in (50, 65, 80, 90):
                accepted = []
                for ordinal, pleasure, _ in _CURVE:
                    self._set_ordinal(self.recipient, ordinal)
                    with patch("world.rules.church.roll_d100", return_value=roll):
                        result = church.offer_step(
                            self.char1, self.recipient, row_key
                        )
                    accepted.append(result["outcome"] == "accepted")
                # Acceptance never regresses as the ordinal rises: the
                # outcomes are non-decreasing from decline to accept.
                self.assertEqual(accepted, sorted(accepted), f"die {roll}")

    @covers_requirement(
        "church-ordination::sexual-offering-is-explicit-selection-ministry-gated-on-the-npc-s-arousal-never-affinity"
    )
    def test_no_affinity_term_participates_in_the_decision(self):
        # The offering decision must not consult affinity anywhere: the rolled
        # outcome is a pure function of (ordinal, die), and the shipped
        # module's offering code never names the concept.
        from pathlib import Path

        source = (
            Path(__file__).parents[1] / "church.py"
        ).read_text(encoding="utf-8")
        offer_region = source.split("def offering_menu", 1)[1]
        offer_region = offer_region.split("def _snapshot_offering_state", 1)[0]
        self.assertNotIn("affinity", offer_region)
        row_key = self._first_row_key()
        self._set_ordinal(self.recipient, 1)
        with patch("world.rules.church.roll_d100", return_value=65):
            result = church.offer_step(self.char1, self.recipient, row_key)
        self.assertEqual(result["outcome"], "accepted")
        self.assertEqual(result["accept_percent"], 65)


class ChurchOfferingSettlementTests(ChurchAccrualBase):
    """Accepted/declined settlement: one transaction, byte-identical decline."""

    @covers_requirement(
        "church-ordination::sexual-offering-is-explicit-selection-ministry-gated-on-the-npc-s-arousal-never-affinity"
    )
    def test_an_accepted_offering_settles_in_one_transaction(self):
        row = church.offering_menu(self.char1)[0]
        self._set_ordinal(self.recipient, 4)
        before_merit = church.merit(self.char1)
        before_wallet = int(self.char1.db.wallet or 0)
        before_pleasure = self.char1.sexual.pleasure.base
        with (
            patch("world.rules.church.roll_d100", return_value=10),
            patch("world.rules.church.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            result = church.offer_step(self.char1, self.recipient, row.key)
        self.assertEqual(result["outcome"], "accepted")
        self.assertEqual(church.merit(self.char1), before_merit + row.merit)
        self.assertEqual(
            int(self.char1.db.wallet or 0), before_wallet + result["copper"]
        )
        self.assertIsInstance(result["copper"], int)
        band = get_church_rules().offering
        self.assertGreaterEqual(result["copper"], band.copper_lo)
        self.assertLessEqual(result["copper"], band.copper_hi)
        # The act's normal rails ran on the actor: her pleasure gauge moved
        # with the act's authored gain through the action pipeline.
        self.assertGreater(self.char1.sexual.pleasure.base, before_pleasure)
        (event,), kwargs = info.call_args
        self.assertEqual(event, "church_offering_accepted")
        self.assertEqual(kwargs["context"]["char"], str(self.char1))
        self.assertEqual(kwargs["context"]["npc"], str(self.recipient))
        self.assertEqual(kwargs["context"]["row"], row.key)

    @covers_requirement(
        "church-ordination::sexual-offering-is-explicit-selection-ministry-gated-on-the-npc-s-arousal-never-affinity"
    )
    def test_a_partner_offering_forwards_the_npc_and_runs_both_bodies(self):
        row = next(
            candidate
            for candidate in OFFERING_CATALOG
            if candidate.act_key == "partner_caress"
        )
        self._set_ordinal(self.recipient, 4)
        duo_before = self.recipient.sexual.duo_act_count
        with (
            patch("world.rules.church.roll_d100", return_value=10),
            patch("world.rules.action.gates.roll_d100", return_value=1),
            patch("world.rules.church.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            result = church.offer_step(self.char1, self.recipient, row.key)
        self.assertEqual(result["outcome"], "accepted")
        self.assertEqual(self._events(info), ["church_offering_accepted"])
        # The pipeline forwarded the NPC as the act target: her pair counter
        # ran (a participant rail), and the actor's pleasure rail ran too.
        self.assertEqual(self.recipient.sexual.duo_act_count, duo_before + 1)
        self.assertGreater(self.char1.sexual.pleasure.base, 0)

    @covers_requirement(
        "church-ordination::sexual-offering-is-explicit-selection-ministry-gated-on-the-npc-s-arousal-never-affinity"
    )
    def test_offering_a_partner_act_to_oneself_is_rejected(self):
        row = next(
            candidate
            for candidate in OFFERING_CATALOG
            if candidate.act_key == "partner_caress"
        )
        with (
            patch("world.rules.church.roll_d100", return_value=10),
        ):
            with self.assertRaises(OfferingError) as caught:
                church.offer_step(self.char1, self.char1, row.key)
        self.assertEqual(caught.exception.args[0], OfferingReason.ACT_REJECTED)

    @covers_requirement(
        "church-ordination::sexual-offering-is-explicit-selection-ministry-gated-on-the-npc-s-arousal-never-affinity"
    )
    def test_the_payout_respects_band_edges_overrides_and_row_copper(self):
        from contextlib import ExitStack

        from world.rules.church_rulebook import OfferingConfig

        def _accept(row_key, roll, rules=None):
            self._set_ordinal(self.recipient, 4)
            patchers = [patch("world.rules.church.roll_d100", return_value=roll)]
            if rules is not None:
                patchers.append(
                    patch("world.rules.church_rulebook.get_church_rules", return_value=rules)
                )
            with ExitStack() as stack:
                for patcher in patchers:
                    stack.enter_context(patcher)
                with self.captureOnCommitCallbacks(execute=True):
                    return church.offer_step(self.char1, self.recipient, row_key)

        base = get_church_rules()
        row_key = self._first_row_key()
        result = _accept(row_key, 1)
        self.assertEqual(result["copper"], base.offering.copper_lo)
        result = _accept(row_key, 100)
        self.assertEqual(result["copper"], base.offering.copper_hi)
        overridden = replace(
            base,
            offering=OfferingConfig(
                copper_lo=base.offering.copper_lo,
                copper_hi=base.offering.copper_hi,
                overrides={row_key: {"copper": 77}},
                enrollment_required=True,
            ),
        )
        result = _accept(row_key, 1, rules=overridden)
        self.assertEqual(result["copper"], 77)
        # A catalogue row's own copper override wins over everything.
        capped = OfferingRow(
            key="offering_t_nine",
            act_key="solo_self_touch",
            merit=1,
            copper=9,
        )
        with patch(
            "world.rules.church.OFFERING_CATALOG", OFFERING_CATALOG + (capped,)
        ):
            result = _accept("offering_t_nine", 100)
        self.assertEqual(result["copper"], 9)

    @covers_requirement(
        "church-ordination::sexual-offering-is-explicit-selection-ministry-gated-on-the-npc-s-arousal-never-affinity"
    )
    def test_a_rolled_back_acceptance_leaves_both_bodies_byte_identical(self):
        real_write = church._write_ledger

        def write_then_raise(entity, mutate):
            real_write(entity, mutate)
            raise RuntimeError("simulated post-settlement offering failure")

        row = church.offering_menu(self.char1)[0]
        self._set_ordinal(self.recipient, 4)
        ledger_before = deepcopy(church.read_ledger(self.char1))
        wallet_before = deepcopy(self.char1.attributes.get("wallet"))
        npc_sexual_before = deepcopy(
            self.recipient.attributes.get("sexual_traits", category="traits")
        )
        npc_pleasure_cached = self.recipient.sexual.pleasure.base
        with (
            patch("world.rules.church._write_ledger", side_effect=write_then_raise),
            patch("world.rules.church.roll_d100", return_value=10),
            patch("world.rules.action.gates.roll_d100", return_value=1),
            patch("world.rules.church.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
            self.assertRaises(RuntimeError),
        ):
            church.offer_step(self.char1, self.recipient, row.key)
        self.assertEqual(church.read_ledger(self.char1), ledger_before)
        self.assertEqual(deepcopy(self.char1.attributes.get("wallet")), wallet_before)
        self.assertEqual(
            deepcopy(
                self.recipient.attributes.get("sexual_traits", category="traits")
            ),
            npc_sexual_before,
            "the act's rails rolled back on the NPC body",
        )
        self.assertEqual(self.recipient.sexual.pleasure.base, npc_pleasure_cached)
        self.assertEqual(self._events(info), [])

    @covers_requirement(
        "church-ordination::sexual-offering-is-explicit-selection-ministry-gated-on-the-npc-s-arousal-never-affinity"
    )
    def test_a_declined_offer_never_materializes_the_npc(self):
        # A never-touched NPC carries no state at all; the consent read and
        # the decline must not create any — the zero-write promise is
        # byte-level, so even the sexual-handler materialization is a write.
        pristine = create_object(NPC, key="t_pristine_recipient", location=self.hall)
        row_key = self._first_row_key()
        ledger_before = deepcopy(church.read_ledger(self.char1))
        keys_before = self._persisted_attribute_keys(pristine)
        with (
            patch("world.rules.church.roll_d100", return_value=99),
            patch("world.rules.church.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            result = church.offer_step(self.char1, pristine, row_key)
        self.assertEqual(result["outcome"], "declined")
        self.assertEqual(self._events(info), ["church_offering_declined"])
        self.assertEqual(church.read_ledger(self.char1), ledger_before)
        self.assertEqual(self._persisted_attribute_keys(pristine), keys_before)
        for key in ("sexual_traits", "virgin", "experience_types"):
            self.assertNotIn(key, keys_before)

    @covers_requirement(
        "church-ordination::sexual-offering-is-explicit-selection-ministry-gated-on-the-npc-s-arousal-never-affinity"
    )
    def test_a_rolled_back_accept_restores_the_npc_s_absence(self):
        real_write = church._write_ledger

        def write_then_raise(entity, mutate):
            real_write(entity, mutate)
            raise RuntimeError("simulated post-settlement offering failure")

        pristine = create_object(NPC, key="t_pristine_accept", location=self.hall)
        pristine.race = "human"
        pristine.apply_race_baseline()
        row = next(
            candidate
            for candidate in OFFERING_CATALOG
            if candidate.act_key == "partner_caress"
        )
        keys_before = self._persisted_attribute_keys(pristine)
        with (
            patch("world.rules.church._write_ledger", side_effect=write_then_raise),
            patch("world.rules.church.roll_d100", return_value=10),
            patch("world.rules.church.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
            self.assertRaises(RuntimeError),
        ):
            church.offer_step(self.char1, pristine, row.key)
        self.assertEqual(self._persisted_attribute_keys(pristine), keys_before)
        for key in ("sexual_traits", "virgin", "experience_types"):
            self.assertNotIn(key, keys_before)
        self.assertEqual(self._events(info), [])

    @covers_requirement(
        "church-ordination::sexual-offering-is-explicit-selection-ministry-gated-on-the-npc-s-arousal-never-affinity"
    )
    def test_a_declined_offering_writes_nothing_and_is_immediately_reproposable(self):
        row = church.offering_menu(self.char1)[0]
        self._set_ordinal(self.recipient, 0)
        ledger_before = deepcopy(church.read_ledger(self.char1))
        wallet_before = deepcopy(self.char1.attributes.get("wallet"))
        npc_sexual_before = deepcopy(
            self.recipient.attributes.get("sexual_traits", category="traits")
        )
        with (
            patch("world.rules.church.roll_d100", return_value=99),
            patch("world.rules.church.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            result = church.offer_step(self.char1, self.recipient, row.key)
        self.assertEqual(result["outcome"], "declined")
        self.assertEqual(self._events(info), ["church_offering_declined"])
        self.assertEqual(church.read_ledger(self.char1), ledger_before)
        self.assertEqual(deepcopy(self.char1.attributes.get("wallet")), wallet_before)
        self.assertEqual(
            deepcopy(
                self.recipient.attributes.get("sexual_traits", category="traits")
            ),
            npc_sexual_before,
        )
        # No cooldown: the identical offer with an accepting die succeeds.
        with (
            patch("world.rules.church.roll_d100", return_value=10),
            patch("world.rules.church.log_info") as info2,
            self.captureOnCommitCallbacks(execute=True),
        ):
            result2 = church.offer_step(self.char1, self.recipient, row.key)
        self.assertEqual(result2["outcome"], "accepted")
        self.assertEqual(self._events(info2), ["church_offering_accepted"])

    @covers_requirement(
        "church-ordination::sexual-offering-is-explicit-selection-ministry-gated-on-the-npc-s-arousal-never-affinity"
    )
    def test_normal_partnered_sex_never_auto_counts(self):
        # The same act cast through the ordinary out-of-combat pipeline (the
        # normal partnered-sex rails) adds no church merit, no copper, and no
        # church event: normal sex stays outside the offering flow.
        from world.rules.action import ActionRequest
        from world.rules.cast_settlement import settle_out_of_combat_cast
        from world.rules.targeting import RoomActionContext

        request = ActionRequest(
            actor=self.char1,
            skill_key="partner_caress",
            targets=[self.recipient],
            context=RoomActionContext(self.hall),
        )
        ledger_before = deepcopy(church.read_ledger(self.char1))
        wallet_before = int(self.char1.db.wallet or 0)
        with (
            patch("world.rules.church.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            settled = settle_out_of_combat_cast(request, clock=WorldClock(tick=0))
        self.assertEqual(settled.result.outcome, "success")
        self.assertEqual(church.read_ledger(self.char1), ledger_before)
        self.assertEqual(int(self.char1.db.wallet or 0), wallet_before)
        self.assertEqual(self._events(info), [])


class ChurchClimaxAccrualTests(ChurchAccrualBase):
    """The ``climax_while_enrolled`` rail: once per entry, fails closed."""

    @covers_requirement(
        "church-ordination::climax-accrual-rides-the-side-reaction-rail-and-fails-closed-for-the-unenrolled"
    )
    def test_an_enrolled_climax_credits_merit_once_per_entry(self):
        before = church.merit(self.char1)
        _apply_climax_phase_set(self.char1, "接近")
        with (
            patch("world.rules.church.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            _apply_climax_phase_set(self.char1, "進行中")
        # No dedicated church event rides the rail (the facade contract for
        # this change names the three offering/pray events only).
        self.assertEqual(self._events(info), [])
        self.assertEqual(church.merit(self.char1), before + CLIMAX_ACCRUAL["merit"])
        # A second climax cycle pays out again: once per entry, not once ever.
        _apply_climax_phase_set(self.char1, "餘韻")
        _apply_climax_phase_set(self.char1, "未達")
        _apply_climax_phase_set(self.char1, "接近")
        _apply_climax_phase_set(self.char1, "進行中")
        self.assertEqual(
            church.merit(self.char1), before + 2 * CLIMAX_ACCRUAL["merit"]
        )

    @covers_requirement(
        "church-ordination::climax-accrual-rides-the-side-reaction-rail-and-fails-closed-for-the-unenrolled"
    )
    def test_unenrolled_climax_settlement_is_byte_identical(self):
        fresh = create_object(PlayerCharacter, key="t_unenrolled_climax")
        fresh.race = "human"
        fresh.apply_race_baseline()
        fresh.location = self.hall
        self.assertIsNone(church.read_ledger(fresh))
        wallet_before = int(fresh.db.wallet or 0)
        with (
            patch("world.rules.church.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            _apply_climax_phase_set(fresh, "接近")
            _apply_climax_phase_set(fresh, "進行中")
            _apply_climax_phase_set(fresh, "餘韻")
        self.assertIsNone(church.read_ledger(fresh))
        self.assertEqual(int(fresh.db.wallet or 0), wallet_before)
        self.assertEqual(self._events(info), [])
        self.assertNotIn(
            "church",
            self._persisted_attribute_keys(fresh),
            "the rail row never fires for the unenrolled — no church write",
        )

    @covers_requirement(
        "church-ordination::climax-accrual-rides-the-side-reaction-rail-and-fails-closed-for-the-unenrolled"
    )
    def test_staying_in_progress_does_not_credit_again(self):
        before = church.merit(self.char1)
        _apply_climax_phase_set(self.char1, "接近")
        _apply_climax_phase_set(self.char1, "進行中")
        self.assertEqual(church.merit(self.char1), before + CLIMAX_ACCRUAL["merit"])
        # A second transition into 進行中 from the same phase is not a
        # canonical edge; the dispatcher fires only on real transitions.
        _apply_climax_phase_set(self.char1, "進行中")
        self.assertEqual(church.merit(self.char1), before + CLIMAX_ACCRUAL["merit"])