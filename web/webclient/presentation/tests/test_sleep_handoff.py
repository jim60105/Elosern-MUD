"""Sleep-control panel presenter: the exact bounded browser view."""

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.npcs import NPC
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.registry import (
    PanelUnavailableError,
    build_production_registry,
)
from web.webclient.presentation.sleep_handoff import (
    SLEEP_HANDOFF_SCHEMA_VERSION,
    sleep_handoff_presenter,
    validate_sleep_handoff,
)
from world.rules.fatigue import SleepPosture, write_fatigue_state
from world.rules.party import join_party
from world.rules.possession import enter_possession, release_possession
from world.rules.time_skip import enter_sleep


class SleepHandoffPresenterTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        from world.quests.catalog import register_catalog

        register_catalog()
        self.player = self.char1
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        self.player.save()
        write_fatigue_state(self.player, 180000, SleepPosture.AWAKE)
        self.companion = create_object(NPC, key="同伴", location=self.room1)
        self.companion.race = "human"
        self.companion.apply_race_baseline()
        join_party(self.companion, self.player)
        write_fatigue_state(self.companion, 180000, SleepPosture.AWAKE)
        self.registry = build_production_registry()

    def _payload(self, actor=None):
        actor = actor or self.player
        return sleep_handoff_presenter(
            PresentationContext(actor=actor, protocol_version=1)
        )

    @covers_requirement(
        "companion-possession-core::sleep-driven-handoff-is-contextual-and-requires-confirmation"
    )
    def test_owner_sleep_publishes_the_complete_available_payload(self):
        enter_sleep(self.player, mode="duration", seconds=600)
        payload = self._payload()
        self.assertEqual(payload["schema_version"], SLEEP_HANDOFF_SCHEMA_VERSION)
        self.assertTrue(payload["available"])
        self.assertEqual(payload["owner_id"], int(self.player.pk))
        self.assertEqual(
            [row["identity"] for row in payload["selection"]["rows"]],
            [int(self.companion.pk)],
        )
        self.assertEqual(payload["party"]["label"], "全員一起睡眠")
        self.assertTrue(payload["owner_sleep"]["dream_pending"])
        self.assertEqual(
            payload["controlled_sleep"]["sleep_id"],
            payload["owner_sleep"]["sleep_id"],
        )
        self.assertEqual(validate_sleep_handoff(payload), payload)

    @covers_requirement(
        "companion-possession-transition::released-control-preserves-owner-physiology-and-rederives-the-view"
    )
    def test_possessed_companion_is_the_controlled_body_and_release_changes_view(self):
        enter_sleep(self.player, mode="duration", seconds=600)
        enter_possession(self.player, self.companion)
        enter_sleep(self.companion, mode="duration", seconds=100)
        payload = self._payload(self.companion)
        self.assertEqual(payload["controlled_body_id"], int(self.companion.pk))
        self.assertIsNone(payload["owner_sleep"])
        release_possession(self.player, npc=self.companion, reason="handback")
        released = self._payload()
        self.assertIsNotNone(released["owner_sleep"])
        self.assertTrue(released["owner_sleep"]["dream_pending"])

    @covers_requirement(
        "dream-sleep-surface::optional-collaboration-follows-one-accepted-sleep-result"
    )
    def test_awake_or_unowned_bodies_publish_unavailable(self):
        with self.assertRaises(PanelUnavailableError):
            self._payload()
        other = create_object(NPC, key="自由 NPC", location=self.room1)
        with self.assertRaises(PanelUnavailableError):
            self._payload(other)
