"""Whole-party camping: read-only preview, atomic admission and settlement.

Every expected wake tick and reserve below is computed by hand from the
synthetic fixture (sleep +12 units/s, awake -4 units/s, reserve maximum
360000, wake threshold 72000), never from the calculator under test.
"""

from evennia.scripts.models import ScriptDB
from evennia.utils.create import create_object
from evennia.utils.search import search_script
from evennia.utils.test_resources import EvenniaTest

from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from tools.spec_traceability import covers_requirement
from world.rules.camping import plan_camp, preview_camp
from world.rules.clock import CLOCK_YAML, _EVENT_SOURCES, get_world_clock
from world.rules.fatigue import POSTURE_ATTRIBUTE, RESERVE_ATTRIBUTE, SleepPosture, read_optional_fatigue_state, write_fatigue_state
from world.rules.party import join_party
from world.rules.sleep_receipt import MODE_RECOVERY, MODE_UNTIL_DAWN
from world.rules.time_skip import SleepRefused, enter_sleep

HOUR = CLOCK_YAML["seconds_per_hour"]
DAY = HOUR * CLOCK_YAML["hours_per_day"]
FULL = 360000


class CampFixture(EvenniaTest):
    """A safe owner with full gauges in a quiet room (no test methods)."""

    def setUp(self):
        super().setUp()
        self._event_sources = dict(_EVENT_SOURCES)
        _EVENT_SOURCES.clear()
        self.addCleanup(_EVENT_SOURCES.update, self._event_sources)
        self.addCleanup(_EVENT_SOURCES.clear)
        self.player = self.char1
        self._body(self.player)
        self.player.location = self.room1
        self.player.save()
        write_fatigue_state(self.player, FULL, SleepPosture.AWAKE)

    @staticmethod
    def _body(body):
        body.race = "human"
        body.apply_race_baseline()
        for key in ("hp", "mp", "sp"):
            gauge = getattr(body.traits, key)
            gauge.current = gauge.max
            gauge.rate = 0.0

    def _companion(self, key, reserve=FULL, posture=SleepPosture.AWAKE, location=None):
        npc = create_object(NPC, key=key, location=self.room1)
        self._body(npc)
        join_party(npc, self.player)
        write_fatigue_state(npc, reserve, posture)
        if location is not None:
            npc.location = location
            npc.save()
        return npc

    def _at(self, day, hour):
        clock = get_world_clock()
        clock._script.db.tick = day * DAY + hour * HOUR
        return int(get_world_clock().tick)

    @staticmethod
    def _surfaces(*bodies):
        return {
            int(body.pk): sorted(
                (attr.db_key, attr.db_category or "", repr(attr.value))
                for attr in body.attributes.all()
            )
            for body in bodies
        }


class CampPreviewTests(CampFixture):
    @covers_requirement("wilderness-camping::camp-preview-is-read-only-and-authoritative")
    def test_preview_parity_and_no_writes(self):
        tired = self._companion("疲憊同伴", reserve=180000)
        remote = self._companion("遠方同伴", reserve=36000, location=self.room2)
        resting = self._companion("小睡同伴", reserve=180000)
        tick = self._at(3, 20)
        enter_sleep(self.player, member_id=resting.pk, mode="duration", seconds=3600)
        forced = self._companion("昏睡同伴", reserve=60000, posture=SleepPosture.FORCED)
        bodies = (self.player, tired, remote, resting, forced)
        before = self._surfaces(*bodies)
        scripts = ScriptDB.objects.count()

        data = preview_camp(self.player)

        # Read-only: nothing durable moved, nothing was created.
        self.assertEqual(self._surfaces(*bodies), before)
        self.assertEqual(ScriptDB.objects.count(), scripts)
        self.assertEqual(get_world_clock().tick, tick)

        self.assertTrue(data["available"])
        self.assertIsNone(data["refusal"])
        self.assertEqual(data["default_mode"], "until-dawn")  # 20:00 is night
        self.assertEqual(data["current_tick"], tick)
        self.assertEqual([mode["mode"] for mode in data["modes"]], ["until-dawn", "until-recovered"])
        dawn, recovered = data["modes"]
        ids = [str(body.pk) for body in (self.player, tired, resting, forced)]

        # Dawn: the endpoint is the next 06:00 (10 h); the remote member is
        # excluded and the existing sleepers keep their own targets.
        self.assertTrue(dawn["available"])
        self.assertTrue(dawn["dream_offerable"])
        self.assertEqual(dawn["wake_tick"], tick + 10 * HOUR)
        rows = {row["member_id"]: row for row in dawn["members"]}
        self.assertEqual(sorted(rows), sorted(ids))
        self.assertNotIn(str(remote.pk), rows)
        self.assertEqual(rows[str(self.player.pk)]["wake_tick"], tick + 10 * HOUR)
        self.assertEqual(rows[str(self.player.pk)]["predicted_reserve"], FULL)
        self.assertEqual(rows[str(tired.pk)]["predicted_reserve"], FULL)
        self.assertEqual(rows[str(resting.pk)]["wake_tick"], tick + 3600)
        # 180000 + 12*3600 = 223200, then awake for 32400 s: -129600.
        self.assertEqual(rows[str(resting.pk)]["predicted_reserve"], 93600)
        # Forced: wakes at 72000 after 1000 s, then 35000 s awake: it reaches
        # zero after 18000 s and collapses; forced sleep of 6000 s brings it
        # back to 72000, then 11000 s awake leave 28000.
        self.assertEqual(rows[str(forced.pk)]["wake_tick"], tick + 1000)
        self.assertEqual(rows[str(forced.pk)]["predicted_reserve"], 28000)
        self.assertEqual(rows[str(tired.pk)]["current_percent"], 50)
        self.assertEqual(rows[str(tired.pk)]["predicted_percent"], 100)

        # Recovery: the full owner stays awake (no opt-in), the tired
        # companion needs 15000 s and is the slowest selected sleeper.
        self.assertTrue(recovered["available"])
        self.assertFalse(recovered["dream_offerable"])
        self.assertEqual(recovered["wake_tick"], tick + 15000)
        rows = {row["member_id"]: row for row in recovered["members"]}
        self.assertEqual(rows[str(self.player.pk)]["wake_tick"], tick)
        self.assertEqual(rows[str(self.player.pk)]["predicted_reserve"], FULL - 4 * 15000)
        self.assertEqual(rows[str(tired.pk)]["predicted_reserve"], FULL)
        self.assertEqual(rows[str(resting.pk)]["predicted_reserve"], 223200 - 4 * 11400)

        # The internal plan carries the same accepted targets.
        plan = plan_camp(self.player, mode=MODE_UNTIL_DAWN)
        targets = {int(item["member"].pk): item for item in plan["targets"]}
        self.assertFalse(targets[int(tired.pk)]["existing"])
        self.assertTrue(targets[int(resting.pk)]["existing"])
        self.assertEqual(targets[int(resting.pk)]["target_tick"], tick + 3600)

    def test_mode_defaults_full_party_and_refusals(self):
        # Day defaults to recovery; a wholly full party can camp only to dawn.
        tick = self._at(4, 10)
        data = preview_camp(self.player)
        self.assertEqual(data["default_mode"], "until-recovered")
        dawn, recovered = data["modes"]
        self.assertTrue(dawn["available"])
        self.assertEqual(dawn["wake_tick"], tick + 20 * HOUR if 20 * HOUR <= CLOCK_YAML["max_sleep_seconds"] else tick + CLOCK_YAML["max_sleep_seconds"])
        self.assertFalse(recovered["available"])
        self.assertEqual(recovered["refusal"]["code"], "party_unavailable")
        self.assertIsNone(recovered["wake_tick"])
        self.assertEqual(recovered["members"], [])
        self.assertTrue(data["available"])

        # A hostile in the room refuses both modes with the skip-safety code.
        monster = create_object(Monster, key="哥布林", location=self.room1)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        data = preview_camp(self.player)
        self.assertFalse(data["available"])
        self.assertEqual(data["refusal"]["code"], "hostile_present")
        self.assertEqual({mode["refusal"]["code"] for mode in data["modes"]}, {"hostile_present"})
        with self.assertRaises(SleepRefused) as caught:
            plan_camp(self.player, mode=MODE_UNTIL_DAWN)
        self.assertEqual(caught.exception.code, "hostile_present")
        monster.delete()

        # An ineligible present member refuses with the all-party code.
        fallen = self._companion("倒下同伴", reserve=180000)
        fallen.traits.hp.current = 0
        data = preview_camp(self.player)
        self.assertFalse(data["available"])
        self.assertEqual(data["refusal"]["code"], "party_unavailable")
        self.assertIn("倒下同伴", data["refusal"]["message"])
        fallen.delete()

        # A stale possession flag on the acting companion refuses too.
        rider = self._companion("同伴", reserve=180000)
        rider.db.possessed_by = int(self.player.pk)
        data = preview_camp(rider)
        self.assertFalse(data["available"])
        self.assertEqual(data["refusal"]["code"], "party_unavailable")
        self.assertFalse(any(mode["dream_offerable"] for mode in data["modes"]))

    def test_missing_surfaces_are_never_initialized(self):
        blank = create_object(NPC, key="未建立同伴", location=self.room1)
        blank.race = "human"
        blank.apply_race_baseline()
        join_party(blank, self.player)
        # Physiology never constructed on this body (the creation hook
        # constructs it, so the fixture removes the pair).
        blank.attributes.remove(RESERVE_ATTRIBUTE)
        blank.attributes.remove(POSTURE_ATTRIBUTE)
        for script in search_script("world_clock"):
            script.delete()
        data = preview_camp(self.player)
        self.assertFalse(data["available"])
        self.assertEqual(data["current_tick"], 0)
        self.assertEqual(search_script("world_clock").count(), 0)
        self.assertIsNone(read_optional_fatigue_state(blank))
        with self.assertRaises(SleepRefused):
            plan_camp(self.player, mode=MODE_RECOVERY)


class CampActionTests(CampFixture):
    """The committed camp: atomic admission, continuation and its one result."""

    def setUp(self):
        super().setUp()
        from world.rules import travel_events

        self.facts = []
        saved = list(travel_events._observers)
        self.addCleanup(lambda: travel_events._observers.__init__(saved))
        travel_events.register_travel_observer(self.facts.append)

    def _camp(self, actor=None, *, mode="until-recovered", dream=False, operation_id="camp-op", **kwargs):
        from server.camp_service import camp

        with self.captureOnCommitCallbacks(execute=True):
            return camp(actor or self.player, mode=mode, dream=dream, operation_id=operation_id, **kwargs)

    def _rows(self, data):
        return {row["member_id"]: row for row in data["members"]}

    def _assert_parity(self, preview_mode, result):
        """Each predicted wake and reserve equals the committed result."""
        predicted = {row["member_id"]: row for row in preview_mode["members"]}
        actual = self._rows(result)
        self.assertEqual(sorted(predicted), sorted(actual))
        for member_id, row in predicted.items():
            self.assertEqual(actual[member_id]["reserve_after"], row["predicted_reserve"], member_id)
        self.assertEqual(result["timing"]["wake_tick"], preview_mode["wake_tick"])

    @covers_requirement("wilderness-camping::camp-commits-consent-and-continues-accepted-party-sleep")
    def test_atomic_admission_and_continuation(self):
        from world.rules.sleep_receipt import read_sleep_receipt, read_sleep_view_decision

        # A full awake owner and a tired companion under recovery.
        tired = self._companion("疲憊同伴", reserve=180000)
        tick = self._at(5, 10)
        preview = preview_camp(self.player)["modes"][1]
        data = self._camp()["data"]
        self.assertEqual(data["phase"], "complete")
        self.assertFalse(data["interrupted"])
        self.assertEqual(data["timing"]["elapsed_seconds"], 15000)
        self.assertEqual(get_world_clock().tick, tick + 15000)
        self.assertIsNone(read_sleep_receipt(self.player))
        self.assertIsNone(read_sleep_view_decision(self.player))
        self.assertIs(read_optional_fatigue_state(tired).posture, SleepPosture.AWAKE)
        self.assertEqual(self._rows(data)[str(tired.pk)]["wake_tick"], tick + 15000)
        self.assertIsNone(self._rows(data)[str(self.player.pk)]["wake_tick"])
        self._assert_parity(preview, data)
        self.assertEqual([fact.events[0].kind for fact in self.facts], ["camp_result"])

    def test_slower_companion_and_forced_sleeper_wake_before_success(self):
        write_fatigue_state(self.player, 300000, SleepPosture.AWAKE)
        slow = self._companion("慢醒同伴", reserve=36000)
        forced = self._companion("昏睡同伴", reserve=60000, posture=SleepPosture.FORCED)
        tick = self._at(6, 20)
        preview = preview_camp(self.player)["modes"][0]
        data = self._camp(mode="until-dawn", operation_id="camp-dawn")["data"]
        self.assertEqual(data["phase"], "complete")
        self.assertEqual(get_world_clock().tick, tick + 10 * HOUR)
        self._assert_parity(preview, data)
        for body in (self.player, slow, forced):
            self.assertIs(read_optional_fatigue_state(body).posture, SleepPosture.AWAKE)

        # Recovery: the owner wakes first and spends awake reserve while the
        # slower companion sleeps on to its own target.
        write_fatigue_state(self.player, 300000, SleepPosture.AWAKE)
        write_fatigue_state(slow, 36000, SleepPosture.AWAKE)
        write_fatigue_state(forced, FULL, SleepPosture.AWAKE)
        tick = self._at(7, 10)
        preview = preview_camp(self.player)["modes"][1]
        data = self._camp(operation_id="camp-slow")["data"]
        rows = self._rows(data)
        self.assertEqual(rows[str(self.player.pk)]["wake_tick"], tick + 5000)
        self.assertEqual(rows[str(slow.pk)]["wake_tick"], tick + 27000)
        self.assertEqual(rows[str(self.player.pk)]["reserve_after"], FULL - 4 * 22000)
        self.assertEqual(data["timing"]["wake_tick"], tick + 27000)
        self._assert_parity(preview, data)

    @covers_requirement("wilderness-camping::camp-commits-consent-and-continues-accepted-party-sleep")
    def test_refusals_write_nothing(self):
        from server.camp_service import camp
        from world.rules.time_skip import SleepRefused

        tired = self._companion("疲憊同伴", reserve=180000)
        self._at(8, 10)
        bodies = (self.player, tired)
        before = self._surfaces(*bodies)
        tick = get_world_clock().tick
        # Dream opt-in where the owner is not entering a new sleep.
        with self.assertRaises(SleepRefused) as caught:
            camp(self.player, mode="until-recovered", dream=True, operation_id="x1")
        self.assertEqual(caught.exception.code, "dream_not_offerable")
        # Unknown mode.
        with self.assertRaises(SleepRefused):
            camp(self.player, mode="until-noon", dream=False, operation_id="x2")
        # A hostile: the same gate code as the preview.
        monster = create_object(Monster, key="哥布林", location=self.room1)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        with self.assertRaises(SleepRefused) as caught:
            camp(self.player, mode="until-recovered", dream=False, operation_id="x3")
        self.assertEqual(caught.exception.code, preview_camp(self.player)["refusal"]["code"])
        monster.delete()
        # A failed write inside the entry rolls everything back.
        from unittest.mock import patch

        with patch("world.rules.sleep_receipt.write_camp_operation", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                camp(self.player, mode="until-recovered", dream=False, operation_id="x4")
        self.assertEqual(self._surfaces(*bodies), before)
        self.assertEqual(get_world_clock().tick, tick)
        self.assertEqual(self.facts, [])

    @covers_requirement("wilderness-camping::camp-results-describe-committed-recovery-once")
    def test_result_interruption_dream_and_replay(self):
        from world.rules.clock import ScheduledEvent, register_event_source
        from world.rules.sleep_receipt import read_camp_operation, read_sleep_receipt
        from world.rules.time_skip import continue_owner_sleep, owner_sleep_view_state

        tired = self._companion("疲憊同伴", reserve=180000)
        write_fatigue_state(self.player, 180000, SleepPosture.AWAKE)
        tick = self._at(9, 20)
        boundary = tick + 1000
        register_event_source(
            "shop_hours",
            lambda begin, end: [ScheduledEvent("synthetic_interactive", end, {})]
            if begin < boundary <= end
            else [],
            next_boundary=lambda begin, end: boundary if begin < boundary <= end else None,
            # The shop calendar is an interactive boundary source: every event
            # it settles pauses an interruptible skip (unlike a maintenance
            # stage, whose events are not interactive).
            interactive=True,
        )
        first = self._camp(mode="until-dawn", operation_id="camp-int")
        data = first["data"]
        self.assertEqual(data["phase"], "interrupted")
        self.assertTrue(data["interrupted"])
        self.assertEqual(data["interruption_reason"], "interactive_event")
        self.assertEqual(data["timing"]["elapsed_seconds"], 1000)
        self.assertIsNone(data["timing"]["wake_tick"])
        self.assertIn("synthetic_interactive", [event["kind"] for event in data["events"]])
        self.assertEqual(len(self.facts), 1)
        event_id = self.facts[0].events[0].id

        # Replay: the stored result, the same logical event, no settlement.
        clock_before = get_world_clock().tick
        replay = self._camp(mode="until-dawn", operation_id="camp-int")
        self.assertEqual(replay["data"], data)
        self.assertEqual(get_world_clock().tick, clock_before)
        self.assertEqual({fact.events[0].id for fact in self.facts}, {event_id})

        # An explicit resume keeps sleep progress without a second camp result.
        state = owner_sleep_view_state(self.player)
        self.assertIsNotNone(state)
        self.assertFalse(state["pending"])
        with self.captureOnCommitCallbacks(execute=True):
            continue_owner_sleep(self.player, sleep_id=state["sleep_id"], expected_generation=state["generation"])
        self.assertGreater(get_world_clock().tick, clock_before)
        self.assertEqual(read_camp_operation(self.player)["result"], data)
        self.assertEqual({fact.events[0].id for fact in self.facts}, {event_id})
        self.assertIsNotNone(read_sleep_receipt(tired))

    @covers_requirement("wilderness-camping::camp-results-describe-committed-recovery-once")
    def test_dream_defers_and_departure_finalizes_once(self):
        from server import dream_service
        from world.narrative.dream_surface import associated_session
        from world.rules.sleep_receipt import read_camp_operation

        slow = self._companion("慢醒同伴", reserve=36000)
        write_fatigue_state(self.player, 300000, SleepPosture.AWAKE)
        tick = self._at(10, 10)
        entered = self._camp(dream=True, operation_id="camp-dream")["data"]
        self.assertEqual(entered["phase"], "dream")
        self.assertEqual(entered["timing"]["elapsed_seconds"], 0)
        self.assertEqual(get_world_clock().tick, tick)
        self.assertEqual(self.facts, [])
        self.assertIsNotNone(associated_session(self.player))
        rows = self._rows(entered)
        self.assertEqual(rows[str(slow.pk)]["reserve_after"], rows[str(slow.pk)]["reserve_before"])

        # Reconnect while the dream is open: nothing advances.
        dream_service.resume_owner_sleep_continuation(self.player)
        self.assertEqual(get_world_clock().tick, tick)
        # A new camp waits while this camp's dream is open; nothing is cut off.
        from world.rules.time_skip import SleepRefused

        with self.assertRaises(SleepRefused) as caught:
            self._camp(mode="until-dawn", operation_id="camp-other")
        self.assertEqual(caught.exception.code, "camp_pending")
        self.assertEqual(read_camp_operation(self.player)["camp_id"], "camp-dream")
        # Departure: the owner continuation, then the slower companion.
        state = dream_service.dream_state(self.player)
        with self.captureOnCommitCallbacks(execute=True):
            dream_service.act(self.player, "awaken", session_id=state["session_id"], revision=state["revision"])
        meta = read_camp_operation(self.player)
        self.assertIsNotNone(meta["result"])
        self.assertEqual(meta["result"]["phase"], "complete")
        self.assertEqual(get_world_clock().tick, tick + 27000)
        self.assertEqual(meta["result"]["timing"]["elapsed_seconds"], 27000)
        self.assertEqual(len(self.facts), 1)
        dream_service.resume_owner_sleep_continuation(self.player)
        self.assertEqual(len(self.facts), 1)
        # A replay of the dream camp's request now returns the settled result.
        replay = self._camp(dream=True, operation_id="camp-dream")["data"]
        self.assertEqual(replay, meta["result"])
        self.assertEqual(get_world_clock().tick, tick + 27000)

    @covers_requirement("wilderness-camping::camp-results-describe-committed-recovery-once")
    def test_recovery_across_process_loss(self):
        from world.rules.camping import _commit_entry, camp_metadata, reconcile_camp
        from world.rules.clock import ScheduledEvent, register_event_source
        from world.rules.sleep_receipt import MODE_RECOVERY, read_camp_operation
        from world.rules.time_skip import SleepEntry, continue_sleep

        tired = self._companion("疲憊同伴", reserve=180000)
        tick = self._at(11, 10)
        due = tick + 600
        register_event_source(
            "caravan_arrivals",
            lambda begin, end: [ScheduledEvent("synthetic_due", due, {})] if begin < due <= end else [],
        )
        # The entry committed, then the process stopped before continuing.
        with self.captureOnCommitCallbacks(execute=True):
            _commit_entry(
                self.player, scope="party", mode=MODE_RECOVERY, seconds=None, answer="decline",
                operation_id="camp-loss", camp=camp_metadata(camp_id="camp-loss", mode=MODE_RECOVERY, dream=False),
            )
        # One interval committed (with its due event) before a second loss.
        with self.captureOnCommitCallbacks(execute=True):
            continue_sleep(
                self.player,
                SleepEntry(operation_id="camp-loss:0", member=tired, requested_seconds=0, handoff_offered=False),
                operation_id="camp-loss:0",
            )
        progress = read_camp_operation(self.player)["progress"]
        self.assertEqual(progress["interval_index"], 1)
        self.assertEqual([event["kind"] for event in progress["events"]], ["synthetic_due"])
        self.assertEqual(self.facts, [])
        # Reconnect reconciliation finishes the remainder from durable progress.
        with self.captureOnCommitCallbacks(execute=True):
            result = reconcile_camp(self.player)
        self.assertEqual(result["phase"], "complete")
        self.assertEqual(result["timing"]["elapsed_seconds"], 15000)
        self.assertEqual(get_world_clock().tick, tick + 15000)
        self.assertEqual([event["kind"] for event in result["events"]], ["synthetic_due"])
        self.assertEqual(len(self.facts), 1)
        # A loss before publication: the stored fact is redelivered unchanged.
        event_id = self.facts[0].events[0].id
        with self.captureOnCommitCallbacks(execute=True):
            from world.rules.camping import finalize_camp

            self.assertEqual(finalize_camp(self.player), result)
        self.assertEqual({fact.events[0].id for fact in self.facts}, {event_id})
        self.assertEqual(get_world_clock().tick, tick + 15000)
