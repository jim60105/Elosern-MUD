"""One landmark rite settles world time, sexual state and the record atomically."""

from __future__ import annotations

from unittest.mock import patch

from evennia.utils.create import create_object

from tools.spec_traceability import covers_requirement
from typeclasses.npcs import NPC
from world.lore.rites import uninstall
from world.rules.clock import get_world_clock
from world.rules.fatigue import SleepPosture, write_fatigue_state
from world.rules.landmark_rite_record import RECORD_ATTR, read_record
from world.rules.landmark_rites import (
    eligible_performers,
    perform_rite,
    preflight,
    rite_site_for,
)
from world.rules.possession import enter_possession
from world.rules.skip_safety import SkipRejectReason
from world.rules.tests.rite_fixtures import (
    ARCHETYPE_KEY,
    DISTRICT_KEY,
    DISTRICT_NAME,
    LANDMARK_NAME,
    SHARED,
    SHARED_EXPOSURE,
    SHARED_SECONDS,
    SHARED_SHAME,
    SNAPSHOT,
    SOLO,
    SOLO_EXPOSURE,
    SOLO_SECONDS,
    SOLO_SHAME,
    RiteSettlementFixture,
)


class RiteSiteTests(RiteSettlementFixture):
    @covers_requirement(
        "landmark-rite-settlement::a-rite-is-available-exactly-on-a-rite-landmark-s-node"
    )
    def test_the_site_names_the_district_landmark_and_archetype(self):
        site = rite_site_for(self.player)
        self.assertIsNotNone(site)
        self.assertEqual(site.district_key, DISTRICT_KEY)
        self.assertEqual(site.district_name, DISTRICT_NAME)
        self.assertEqual(site.landmark_name, LANDMARK_NAME)
        self.assertIs(site.archetype, SNAPSHOT.archetypes[ARCHETYPE_KEY])

    @covers_requirement(
        "landmark-rite-settlement::a-rite-is-available-exactly-on-a-rite-landmark-s-node",
        "landmark-rite-settlement::every-refusal-leaves-no-rite-write",
    )
    def test_a_neighbouring_node_has_no_rite_site_and_no_landmark_refusal(self):
        self.player.location = self.source
        self.assertIsNone(rite_site_for(self.player))
        self.refused("rite_no_landmark", lambda: self.perform(self.player, "solo"))

    @covers_requirement(
        "landmark-rite-settlement::a-rite-is-available-exactly-on-a-rite-landmark-s-node",
        "landmark-rite-settlement::every-refusal-leaves-no-rite-write",
    )
    def test_no_installed_rite_content_has_no_rite_site(self):
        uninstall()
        self.assertIsNone(rite_site_for(self.player))
        self.refused("rite_no_landmark", lambda: self.perform(self.player, "solo"))

    @covers_requirement(
        "landmark-rite-settlement::a-rite-is-available-exactly-on-a-rite-landmark-s-node"
    )
    def test_a_plain_interior_room_never_builds_the_landmark_node_table(self):
        self.player.location = self.room1
        with patch(
            "world.lore.map_districts.landmark_node_ids",
            side_effect=AssertionError("the landmark node table was built"),
        ):
            self.assertIsNone(rite_site_for(self.player))

    def test_preflight_reads_the_clock_without_creating_it(self):
        with patch(
            "world.rules.clock.get_world_clock",
            side_effect=AssertionError("preflight created the world clock"),
        ):
            plan = preflight(self.player, "solo")
        self.assertEqual(plan.option.key, "solo")


class RiteCommitTests(RiteSettlementFixture):
    @covers_requirement(
        "landmark-rite-settlement::one-rite-settles-as-a-single-atomic-unit",
        "landmark-rite-settlement::rite-outcomes-are-logged-as-structured-events",
    )
    def test_a_committed_rite_settles_time_sexual_state_and_the_record(self):
        tick_before = get_world_clock().tick
        with patch("world.rules.landmark_rites.log_info") as info:
            result = self.perform(self.player, "solo")

        self.assertEqual(get_world_clock().tick - tick_before, SOLO_SECONDS)
        self.assertEqual(result.tick, tick_before + SOLO_SECONDS)
        self.assertEqual(self.record(), read_record(self.player))
        entry = read_record(self.player)["completed"][DISTRICT_KEY]
        self.assertEqual(
            (entry["count"], entry["first_tick"], entry["last_tick"]),
            (1, result.tick, result.tick),
        )
        self.assertEqual(
            entry["options"]["solo"], {"count": 1, "last_tick": result.tick}
        )
        self.assertEqual(self.player.sexual.climax_today, 1)
        self.assertEqual(self.player.sexual.climax_phase.level, "餘韻")
        self.assertEqual(self.player.sexual.shame.value, SOLO_SHAME)
        self.assertEqual(self.player.sexual.exposure.value, SOLO_EXPOSURE)
        self.assertTrue(result.first_completion)
        self.assertTrue(result.climax)
        self.assertIs(result.scene, SOLO.self_scene)
        self.assertEqual(result.elapsed_seconds, SOLO_SECONDS)
        self.assertEqual(info.call_count, 1)
        self.assertEqual(info.call_args.args[0], "landmark_rite_committed")
        self.assertEqual(
            info.call_args.kwargs["context"],
            {
                "char": self.player.pk,
                "district": DISTRICT_KEY,
                "archetype": ARCHETYPE_KEY,
                "option": "solo",
                "body": self.player.pk,
                "seconds": SOLO_SECONDS,
                "elapsed": SOLO_SECONDS,
                "climax": True,
            },
        )

    @covers_requirement(
        "landmark-rite-record::the-rite-record-counts-completions-per-district-and-per-option"
    )
    def test_a_repeated_rite_updates_the_counts_only(self):
        first = self.perform(self.player, "solo")
        second = self.perform(self.player, "solo")
        entry = self.record()["completed"][DISTRICT_KEY]
        self.assertEqual(entry["count"], 2)
        self.assertEqual(entry["first_tick"], first.tick)
        self.assertEqual(entry["last_tick"], second.tick)
        self.assertEqual(entry["options"]["solo"]["count"], 2)
        self.assertEqual(entry["options"]["solo"]["last_tick"], second.tick)
        self.assertTrue(first.first_completion)
        self.assertFalse(second.first_completion)

    @covers_requirement(
        "landmark-rite-settlement::the-acting-body-and-the-record-owner-are-distinct-roles",
        "landmark-rite-settlement::rite-outcomes-are-logged-as-structured-events",
    )
    def test_a_companion_body_settles_its_own_sexual_state(self):
        player_state = self.sexual_state(self.player)
        with patch("world.rules.landmark_rites.log_info") as info:
            result = self.perform(self.player, "shared", member_id=self.companion.id)
        self.assertEqual(self.sexual_state(self.player), player_state)
        self.assertEqual(self.companion.sexual.climax_today, 1)
        self.assertEqual(self.companion.sexual.shame.value, SHARED_SHAME)
        self.assertEqual(self.companion.sexual.exposure.value, SHARED_EXPOSURE)
        self.assertEqual(result.plan.perspective, "watch")
        self.assertIs(result.scene, SHARED.watch_scene)
        self.assertFalse(self.companion.attributes.has(RECORD_ATTR))
        self.assertEqual(
            self.record()["completed"][DISTRICT_KEY]["options"]["shared"]["count"], 1
        )
        context = info.call_args.kwargs["context"]
        self.assertEqual(info.call_args.args[0], "landmark_rite_committed")
        self.assertEqual(context["char"], self.player.pk)
        self.assertEqual(context["body"], self.companion.pk)

    @covers_requirement(
        "landmark-rite-settlement::the-acting-body-and-the-record-owner-are-distinct-roles"
    )
    def test_a_companion_rite_writes_no_sexual_state_to_the_owner(self):
        # The owner sits in afterglow, the one state ordinary time settlement
        # may damp while a companion performs. The rite itself must add no
        # climax, shame step or exposure step to the owner's body.
        self.player.sexual.climax_phase.value = "餘韻"
        self.player.sexual.shame.value = 0
        self.player.sexual.exposure.value = 0
        climax_before = self.player.sexual.climax_today

        result = self.perform(self.player, "shared", member_id=self.companion.id)

        self.assertEqual(result.plan.perspective, "watch")
        self.assertEqual(self.player.sexual.climax_today, climax_before)
        self.assertEqual(self.player.sexual.shame.value, 0)
        self.assertEqual(self.player.sexual.exposure.value, 0)
        self.assertEqual(self.companion.sexual.shame.value, SHARED_SHAME)
        self.assertEqual(self.companion.sexual.exposure.value, SHARED_EXPOSURE)

    @covers_requirement("landmark-rite-record::undeclared-keys-survive-a-write")
    def test_a_rite_preserves_retired_record_entries(self):
        retired = {
            "first_tick": 5,
            "last_tick": 5,
            "count": 1,
            "options": {"t_retired_option": {"count": 1, "last_tick": 5}},
        }
        self.player.attributes.add(
            RECORD_ATTR,
            {"schema_version": 1, "completed": {"t_retired_district": retired}},
        )

        self.perform(self.player, "solo")

        record = read_record(self.player)
        self.assertEqual(record["completed"]["t_retired_district"], retired)
        self.assertEqual(record["completed"][DISTRICT_KEY]["count"], 1)

    @covers_requirement(
        "landmark-rite-settlement::the-acting-body-and-the-record-owner-are-distinct-roles",
        "landmark-rite-settlement::every-refusal-leaves-no-rite-write",
    )
    def test_a_possessed_companion_delivers_the_watch_scene(self):
        enter_possession(self.player, self.companion)
        with patch("world.rules.landmark_rites.log_info") as info:
            result = self.perform(self.companion, "shared")
        self.assertEqual(result.plan.perspective, "watch")
        self.assertIs(result.scene, SHARED.watch_scene)
        self.assertEqual(self.companion.sexual.climax_today, 1)
        self.assertEqual(self.player.sexual.climax_today, 0)
        self.assertIn(DISTRICT_KEY, self.record()["completed"])
        self.assertFalse(self.companion.attributes.has(RECORD_ATTR))
        context = info.call_args.kwargs["context"]
        self.assertEqual(info.call_args.args[0], "landmark_rite_committed")
        self.assertEqual(context["char"], self.player.pk)
        self.assertEqual(context["body"], self.companion.pk)
        self.refused(
            "rite_no_watch_scene",
            lambda: self.perform(self.companion, "solo"),
            actor=self.companion,
            char=self.player.pk,
            district=DISTRICT_KEY,
        )


class RiteRefusalTests(RiteSettlementFixture):
    @covers_requirement(
        "landmark-rite-settlement::every-refusal-leaves-no-rite-write",
        "landmark-rite-settlement::rite-outcomes-are-logged-as-structured-events",
    )
    def test_an_unknown_option_is_refused(self):
        self.refused("rite_unknown_option", lambda: self.perform(self.player, "t_none"))

    @covers_requirement(
        "landmark-rite-settlement::the-acting-body-and-the-record-owner-are-distinct-roles",
        "landmark-rite-settlement::every-refusal-leaves-no-rite-write",
    )
    def test_an_absent_member_is_refused(self):
        absent = self._companion("測試遠伴", location=self.end)
        self.refused(
            "rite_member_unavailable",
            lambda: self.perform(self.player, "shared", member_id=absent.id),
        )

    @covers_requirement(
        "landmark-rite-settlement::the-acting-body-and-the-record-owner-are-distinct-roles",
        "landmark-rite-settlement::every-refusal-leaves-no-rite-write",
    )
    def test_a_sleeping_member_is_refused(self):
        write_fatigue_state(self.companion, 360000, SleepPosture.VOLUNTARY)
        self.refused(
            "rite_member_unavailable",
            lambda: self.perform(self.player, "shared", member_id=self.companion.id),
        )

    @covers_requirement(
        "landmark-rite-settlement::the-acting-body-and-the-record-owner-are-distinct-roles",
        "landmark-rite-settlement::every-refusal-leaves-no-rite-write",
    )
    def test_a_knocked_out_or_unrelated_member_is_refused(self):
        knocked_out = self._companion("測試倒地")
        knocked_out.traits.hp.current = 0
        unrelated = create_object(NPC, key="測試路人", location=self.player.location)
        for member in (knocked_out, unrelated):
            with self.subTest(member=member.key):
                self.refused(
                    "rite_member_unavailable",
                    lambda member=member: self.perform(
                        self.player, "shared", member_id=member.id
                    ),
                )

    @covers_requirement(
        "landmark-rite-settlement::the-acting-body-and-the-record-owner-are-distinct-roles",
        "landmark-rite-settlement::every-refusal-leaves-no-rite-write",
    )
    def test_a_solo_only_option_refuses_a_companion(self):
        self.refused(
            "rite_no_watch_scene",
            lambda: self.perform(self.player, "solo", member_id=self.companion.id),
        )

    @covers_requirement(
        "landmark-rite-settlement::every-refusal-leaves-no-rite-write"
    )
    def test_an_unavailable_body_is_refused(self):
        with patch("world.rules.fatigue.sleep_blocks_actions", return_value=True):
            self.refused("rite_unavailable", lambda: self.perform(self.player, "solo"))

    @covers_requirement(
        "landmark-rite-settlement::every-refusal-leaves-no-rite-write"
    )
    def test_a_body_away_from_its_owner_is_refused(self):
        # There is no remote rite: the record owner and the acting body must
        # stand in the same place.
        enter_possession(self.player, self.companion)
        self.companion.location = self.end
        self.refused(
            "rite_unavailable",
            lambda: self.perform(self.companion, "shared"),
            actor=self.companion,
            char=self.player.pk,
            district=DISTRICT_KEY,
        )

    @covers_requirement(
        "landmark-rite-settlement::every-refusal-leaves-no-rite-write"
    )
    def test_an_unsafe_place_is_refused(self):
        with (
            patch(
                "world.rules.time_skip.admit_contact_before_action", return_value=None
            ),
            patch(
                "world.rules.skip_safety.evaluate_skip_safety",
                return_value=SkipRejectReason.HOSTILE_PRESENT,
            ),
        ):
            self.refused("rite_unsafe", lambda: self.perform(self.player, "solo"))

    @covers_requirement(
        "landmark-rite-settlement::every-refusal-leaves-no-rite-write"
    )
    def test_a_truncated_interval_is_refused(self):
        with patch(
            "world.rules.mental_time.planned_seconds",
            return_value=SOLO_SECONDS - 1,
        ):
            self.refused("rite_interrupted", lambda: self.perform(self.player, "solo"))

    @covers_requirement(
        "landmark-rite-settlement::every-refusal-leaves-no-rite-write",
        "landmark-rite-settlement::one-rite-settles-as-a-single-atomic-unit",
    )
    def test_an_interval_that_cannot_elapse_rolls_the_advance_back(self):
        # The preflight prediction admits the full duration and the advance
        # itself settles only a shorter one: the post-advance guard is the only
        # refusal that has to undo time and sexual state it already wrote.
        with patch(
            "world.rules.time_skip.planned_seconds", return_value=SOLO_SECONDS - 60
        ):
            self.refused("rite_interrupted", lambda: self.perform(self.player, "solo"))

    @covers_requirement(
        "landmark-rite-settlement::every-refusal-leaves-no-rite-write",
        "landmark-rite-settlement::rite-outcomes-are-logged-as-structured-events",
    )
    def test_a_post_preflight_refusal_names_the_owner_not_the_body(self):
        # The resolved plan carries both roles: the refused event must still
        # name the record owner, not the companion that would have performed.
        with patch(
            "world.rules.time_skip.planned_seconds", return_value=SHARED_SECONDS - 60
        ):
            self.refused(
                "rite_interrupted",
                lambda: self.perform(
                    self.player, "shared", member_id=self.companion.id
                ),
                actor=self.companion,
                char=self.player.pk,
                district=DISTRICT_KEY,
            )

    @covers_requirement(
        "landmark-rite-settlement::every-refusal-leaves-no-rite-write"
    )
    def test_an_unreadable_site_still_reports_the_refusal(self):
        # The refusal code is already determined when the diagnostic identity
        # re-read runs: a broken site read may drop the district, never the code.
        with patch(
            "world.rules.landmark_rites.rite_site_for",
            side_effect=[None, RuntimeError("site unreadable")],
        ):
            self.refused(
                "rite_no_landmark",
                lambda: self.perform(self.player, "solo"),
                char=self.player.pk,
                district="",
            )

    @covers_requirement(
        "landmark-rite-settlement::every-refusal-leaves-no-rite-write",
        "landmark-rite-settlement::rite-outcomes-are-logged-as-structured-events",
    )
    def test_a_corrupt_record_is_refused_and_left_untouched(self):
        corrupt = {"schema_version": 1, "completed": {DISTRICT_KEY: "not a mapping"}}
        self.player.attributes.add(RECORD_ATTR, corrupt)
        with patch("world.rules.landmark_rites.log_warn") as warning:
            self.refused("rite_record_corrupt", lambda: self.perform(self.player, "solo"))
        self.assertEqual(warning.call_count, 1)
        self.assertEqual(warning.call_args.args[0], "landmark_rite_record_corrupt")
        self.assertEqual(
            warning.call_args.kwargs["context"],
            {"char": self.player.pk, "district": DISTRICT_KEY},
        )
        self.assertEqual(self.record(), corrupt)


class RiteRollbackTests(RiteSettlementFixture):
    @covers_requirement(
        "landmark-rite-settlement::one-rite-settles-as-a-single-atomic-unit",
        "landmark-rite-settlement::rite-outcomes-are-logged-as-structured-events",
    )
    def test_a_failed_record_write_rolls_the_whole_rite_back(self):
        tick_before = get_world_clock().tick
        state_before = self.sexual_state(self.player)
        with patch("world.rules.landmark_rites.log_info") as info:
            with patch(
                "world.rules.landmark_rites.write_record",
                side_effect=RuntimeError("record write failed"),
            ):
                with self.assertRaises(RuntimeError):
                    self.perform(self.player, "solo")
        self.assertEqual(get_world_clock().tick, tick_before)
        self.assertEqual(self.sexual_state(self.player), state_before)
        self.assertIsNone(self.record())
        self.assertEqual(info.call_count, 0)

    @covers_requirement(
        "landmark-rite-settlement::one-rite-settles-as-a-single-atomic-unit",
        "landmark-rite-settlement::the-acting-body-and-the-record-owner-are-distinct-roles",
    )
    def test_a_failed_companion_rite_rolls_both_bodies_back(self):
        # The record owner and the acting body differ here: a restore that
        # covered only one of them would still pass the single-body test.
        tick_before = get_world_clock().tick
        player_before = self.sexual_state(self.player)
        companion_before = self.sexual_state(self.companion)
        with patch(
            "world.rules.landmark_rites.write_record",
            side_effect=RuntimeError("record write failed"),
        ):
            with self.assertRaises(RuntimeError):
                self.perform(self.player, "shared", member_id=self.companion.id)
        self.assertEqual(get_world_clock().tick, tick_before)
        self.assertEqual(self.sexual_state(self.player), player_before)
        self.assertEqual(self.sexual_state(self.companion), companion_before)
        self.assertIsNone(self.record())

    @covers_requirement(
        "landmark-rite-settlement::a-repeated-request-identity-settles-once"
    )
    def test_a_retry_after_a_rolled_back_attempt_commits_once(self):
        tick_start = get_world_clock().tick
        with patch(
            "world.rules.landmark_rites.write_record",
            side_effect=RuntimeError("record write failed"),
        ):
            with self.assertRaises(RuntimeError):
                self.perform(self.player, "solo", operation_id="t_rite_retry")
        self.assertEqual(get_world_clock().tick, tick_start)
        self.perform(self.player, "solo", operation_id="t_rite_retry")
        self.assertEqual(get_world_clock().tick - tick_start, SOLO_SECONDS)
        self.assertEqual(self.record()["completed"][DISTRICT_KEY]["count"], 1)


class RiteReplayTests(RiteSettlementFixture):
    @covers_requirement(
        "landmark-rite-settlement::a-repeated-request-identity-settles-once"
    )
    def test_a_duplicate_request_identity_settles_once(self):
        tick_before = get_world_clock().tick
        with patch("world.rules.landmark_rites.log_info") as info:
            first = self.perform(self.player, "solo", operation_id="t_rite_duplicate")
            second = self.perform(self.player, "solo", operation_id="t_rite_duplicate")
        self.assertIs(first, second)
        self.assertEqual(get_world_clock().tick - tick_before, SOLO_SECONDS)
        self.assertEqual(self.record()["completed"][DISTRICT_KEY]["count"], 1)
        self.assertEqual(info.call_count, 1)
        self.assertEqual(info.call_args.args[0], "landmark_rite_committed")

    @covers_requirement(
        "landmark-rite-settlement::a-repeated-request-identity-settles-once"
    )
    def test_a_request_identity_is_scoped_to_the_acting_body(self):
        first = self.perform(self.player, "solo", operation_id="t_rite_shared_id")
        self.char2.race = "human"
        self.char2.apply_race_baseline()
        self.char2.location = self.landmark
        second = self.perform(self.char2, "solo", operation_id="t_rite_shared_id")
        self.assertIsNot(first, second)
        self.assertIs(second.plan.owner, self.char2)
        self.assertEqual(
            read_record(self.char2)["completed"][DISTRICT_KEY]["count"], 1
        )


class EligiblePerformerTests(RiteSettlementFixture):
    @covers_requirement(
        "landmark-rite-settlement::the-acting-body-and-the-record-owner-are-distinct-roles"
    )
    def test_the_actor_leads_and_unavailable_members_are_excluded(self):
        sleeping = self._companion("測試沉睡")
        write_fatigue_state(sleeping, 360000, SleepPosture.VOLUNTARY)
        absent = self._companion("測試遠伴", location=self.end)
        performers = eligible_performers(self.player)
        self.assertEqual(performers, (self.player, self.companion))
        self.assertNotIn(sleeping, performers)
        self.assertNotIn(absent, performers)

    @covers_requirement(
        "landmark-rite-settlement::the-acting-body-and-the-record-owner-are-distinct-roles"
    )
    def test_the_acting_body_leads_when_it_is_a_companion(self):
        enter_possession(self.player, self.companion)
        performers = eligible_performers(self.companion)
        self.assertIs(performers[0], self.companion)
        self.assertIn(self.player, performers)

    @covers_requirement(
        "landmark-rite-settlement::the-acting-body-and-the-record-owner-are-distinct-roles"
    )
    def test_a_preflight_plan_names_owner_and_body(self):
        plan = preflight(self.player, "shared", member_id=self.companion.id)
        self.assertIs(plan.owner, self.player)
        self.assertIs(plan.body, self.companion)
        self.assertEqual(plan.perspective, "watch")
        self.assertIs(plan.option, SHARED)