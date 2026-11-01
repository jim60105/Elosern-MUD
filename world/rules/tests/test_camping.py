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
