"""Behavior tests for the talk command's dialogue turn-in and authored-topic surface.

The ``回報`` keyword on a ``guild_staff`` dialogue host is an action keyword:
``talk <npc> 回報 <quest_id>`` routes to ``dialogue_turn_in`` (the deterministic
guild service), while ``talk <npc> 回報`` stays on the dialogue surface and
lists reportable quests or falls through to the authored ``回報`` topic. Every
other keyword resolves through the source-neutral authored runtime
(``resolve_dialogue_context`` + ``resolve_dialogue_source``) and delivers the
matched topic through ``select_authored_topic``.

The positive paths run against the real hosts and the real migrated snapshot
(``world.lore.dialogue.content``); only the guild service boundary
(``dialogue_turn_in``) and the injected failure are mocked.
"""

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from commands.talk import CmdsTalk
from typeclasses.components import GuildStaff, ScriptedDialogue
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.lore.scenes import Speech
from world.quests.catalog import register_catalog
from world.rules.dialogue import (
    GUILD_STAFF_DIALOGUE_KEY,
    GUILD_STAFF_TURNIN_KEYWORD,
    NO_UNDERSTANDING_LINE,
    clear_dialogue_session,
    live_dialogue_session,
)
from world.rules.dialogue_context import resolve_dialogue_context
from world.rules.dialogue_sources import resolve_dialogue_source
from world.rules.guild import (
    GuildDataError,
    GuildServiceError,
    RewardClaimError,
)
from world.tests.synthetic_data import SYNTH_ITEMS

from tools.spec_traceability import covers_requirement

_NO_RESPONSE = "對方沒有理會你。"


class TalkTurnInBranchTests(EvenniaCommandTestMixin, EvenniaTest):
    def setUp(self):
        super().setUp()
        register_catalog()
        self.hall = create_object(Room, key="大廳")
        self.char1.location = self.hall
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self.staff = create_object(NPC, key="公會職員", location=self.hall)
        # Both authored capabilities declare their place binding, exactly as the
        # shared capability assembly writes it for shipped hosts: the guild
        # service gate (and the P-era associated-service gate on the dialogue
        # component) fails closed on an unbound component.
        staff_component = GuildStaff.create(self.staff, service_id="staff")
        staff_component.service_binding = "place"
        staff_component.anchor_room_id = self.hall.pk
        self.staff.components.add(staff_component)
        dialogue_component = ScriptedDialogue.create(
            self.staff, dialogue_key=GUILD_STAFF_DIALOGUE_KEY
        )
        dialogue_component.service_binding = "place"
        dialogue_component.anchor_room_id = self.hall.pk
        self.staff.components.add(dialogue_component)

    def tearDown(self):
        clear_dialogue_session(self.char1)
        super().tearDown()

    def _authored_topic(self, keyword, host=None):
        """The migrated snapshot's topic for ``keyword`` on ``host``."""
        source = resolve_dialogue_source(
            resolve_dialogue_context(self.char1, host or self.staff)
        )
        self.assertIsNotNone(source, f"no authored source for {keyword}")
        topic = next(
            (item for item in source.dialogue.topics if item.keyword == keyword), None
        )
        self.assertIsNotNone(topic, f"no authored topic for {keyword}")
        return topic

    def _rendered(self, host, topic):
        """The command's attributed rendering of one authored topic scene."""
        rendered = []
        for line in topic.fallback.lines:
            if isinstance(line, Speech):
                if line.speaker == "actor":
                    rendered.append(f"你說：{line.text}")
                else:
                    rendered.append(f"{host.key}說：{line.text}")
            else:
                rendered.append(line.text)
        return "\n".join(rendered)

    def test_turnin_with_quest_id_on_guild_staff_calls_the_service(self):
        with patch(
            "commands.talk.dialogue_turn_in",
            return_value={
                "quest_id": "quest-1",
                "copper": 50,
                "merit": 25,
                "items": [SYNTH_ITEMS["t_ember_spray"].key],
            },
        ) as turnin, patch("commands.talk.select_authored_topic") as delivery:
            output = self.call(
                CmdsTalk(), f"公會職員 {GUILD_STAFF_TURNIN_KEYWORD} quest-1"
            )
        turnin.assert_called_once_with(self.char1, self.staff, "quest-1")
        delivery.assert_not_called()
        self.assertIn("你回報了任務 quest-1", output)
        # The service branch settles through the guild API, not an authored topic.
        self.assertIsNone(live_dialogue_session(self.char1))

    def test_turnin_maps_reward_and_data_errors(self):
        for error in (RewardClaimError("already_claimed"), GuildDataError("bad")):
            with patch("commands.talk.dialogue_turn_in", side_effect=error):
                output = self.call(
                    CmdsTalk(), f"公會職員 {GUILD_STAFF_TURNIN_KEYWORD} quest-1"
                )
            self.assertIn("無法回報任務", output)

    def test_turnin_keyword_without_quest_id_flows_through_talk_writer(self):
        topic = self._authored_topic(GUILD_STAFF_TURNIN_KEYWORD)
        with patch("commands.talk.dialogue_turn_in") as turnin:
            output = self.call(CmdsTalk(), f"公會職員 {GUILD_STAFF_TURNIN_KEYWORD}")
        turnin.assert_not_called()
        # An unregistered caller has nothing reportable, so the keyword falls
        # through to the authored 回報 topic and delivers its complete scene.
        self.assertEqual(output, self._rendered(self.staff, topic))
        session = live_dialogue_session(self.char1)
        self.assertIsNotNone(session)
        self.assertEqual(session.kind, "scene")
        self.assertEqual(session.delivery.topic_id, topic.topic_id)

    def test_turnin_keyword_on_non_guild_host_is_a_plain_keyword(self):
        guard = create_object(NPC, key="南門守衛", location=self.hall)
        guard.components.add(
            ScriptedDialogue.create(guard, dialogue_key="some_other_table")
        )
        for args in (
            f"南門守衛 {GUILD_STAFF_TURNIN_KEYWORD}",
            f"南門守衛 {GUILD_STAFF_TURNIN_KEYWORD} quest-1",
        ):
            with patch("commands.talk.dialogue_turn_in") as turnin, patch(
                "commands.talk.select_authored_topic"
            ) as delivery:
                output = self.call(CmdsTalk(), args)
            turnin.assert_not_called()
            delivery.assert_not_called()
            self.assertEqual(output, _NO_RESPONSE)

    def test_turnin_keyword_on_staff_table_without_staff_component_is_plain(self):
        # A non-staff NPC reusing the guild_staff table (e.g. a bard) must not
        # enter the turn-in branch: the full keyword stays an unknown keyword.
        bard = create_object(NPC, key="吟遊詩人", location=self.hall)
        bard.components.add(
            ScriptedDialogue.create(bard, dialogue_key=GUILD_STAFF_DIALOGUE_KEY)
        )
        with patch("commands.talk.dialogue_turn_in") as turnin, patch(
            "commands.talk.select_authored_topic"
        ) as delivery:
            output = self.call(
                CmdsTalk(), f"吟遊詩人 {GUILD_STAFF_TURNIN_KEYWORD} quest-1"
            )
        turnin.assert_not_called()
        delivery.assert_not_called()
        self.assertEqual(output, f"{bard.key}說：{NO_UNDERSTANDING_LINE}")
        # An unknown keyword writes no session and no topic receipt.
        self.assertIsNone(live_dialogue_session(self.char1))

    def test_host_resolution_failure_renders_the_standard_rejection_line(self):
        with patch(
            "commands.talk.dialogue_turn_in", side_effect=GuildServiceError("multiple")
        ):
            output = self.call(
                CmdsTalk(), f"公會職員 {GUILD_STAFF_TURNIN_KEYWORD} quest-1"
            )
        self.assertEqual(output, "這裡沒有公會服務人員。")

    def test_talk_writer_errors_on_turnin_keyword_are_reported(self):
        # The 回報 listing reads the caller's persisted guild data; a malformed
        # record is reported as the standard turn-in rejection, never a crash
        # or a silent no-response.
        with patch(
            "commands.talk.reportable_quest_summary",
            side_effect=RewardClaimError("malformed_claims"),
        ):
            output = self.call(CmdsTalk(), f"公會職員 {GUILD_STAFF_TURNIN_KEYWORD}")
        self.assertIn("無法回報任務：malformed_claims", output)

    @covers_requirement(
        "authored-dialogue-selection::text-and-browser-resolve-the-same-authored-topic"
    )
    def test_other_keywords_are_untouched(self):
        topic = self._authored_topic("公會")
        with patch("commands.talk.dialogue_turn_in") as turnin:
            output = self.call(CmdsTalk(), "公會職員 公會")
        turnin.assert_not_called()
        self.assertEqual(output, self._rendered(self.staff, topic))
        session = live_dialogue_session(self.char1)
        self.assertIsNotNone(session)
        self.assertEqual(session.kind, "scene")
        self.assertEqual(session.delivery.topic_id, topic.topic_id)
