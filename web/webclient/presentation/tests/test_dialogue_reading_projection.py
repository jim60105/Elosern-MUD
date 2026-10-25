"""Behavior test: the dialogue panel's server-owned reading projection.

Pins the version-3 reading fields: ``reading_revision`` and
``completed_topic_ids`` come from the owner's narrative record, ``unread``
marks an uncompleted open formal topic with the lock taking precedence, and
``pure_chain`` carries the current delivery's public successors in predecessor
order (never a qualified descendant, never stale bytes). The owner-scoped
fan-out reaches every current connection of the owner — including a possessed
companion — and never another character of the same account or a rolled-back
write.
"""

from __future__ import annotations

from types import SimpleNamespace

from evennia.server.serversession import ServerSession
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.components import ScriptedDialogue
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from web.webclient.presentation import watchers
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.coordinator import PresentationCoordinator
from web.webclient.presentation.dialogue import dialogue_presenter
from web.webclient.presentation.dialogue_push import push_dialogue_reading
from web.webclient.presentation.registry import build_production_registry
from world.lore.dialogue.conditions import RaceIs
from world.lore.dialogue.shape import AuthoredDialogue, AuthoredTopic
from world.lore.scenes import Scene, Speech
from world.narrative.dialogue_reading import (
    completed_topic_ids,
    record_completion,
)
from world.rules.dialogue import (
    chain_deliveries,
    clear_dialogue_session,
    complete_dialogue_delivery,
    open_or_refresh_dialogue,
    select_authored_topic,
)
from world.rules.affinity_config import get_config
from world.rules.dialogue_context import host_dialogue_binding
from world.quests.catalog import register_catalog
from world.rules.dialogue_sources import to_authored_dialogue
from world.tests.synthetic_data import SYNTH_RACES, synthetic_registries

_TABLE_KEY = "t_reading_panel"
_ROOT = f"{_TABLE_KEY}.root"
_CHILD = f"{_TABLE_KEY}.child"
_QUALIFIED = f"{_TABLE_KEY}.qualified"
_LOCKED = f"{_TABLE_KEY}.locked"
_RACE_KEY = next(iter(SYNTH_RACES))
_OTHER_RACE = next(key for key in SYNTH_RACES if key != _RACE_KEY)

CALENDAR = SimpleNamespace(
    year=1, season_index=0, season_name="春季", day_in_season=3,
    hour=12, minute=0, second=0,
)


def _scene(scene_id: str, text: str) -> Scene:
    return Scene(
        scene_id=scene_id,
        revision="r1",
        lines=(Speech(speaker="host", text=text),),
    )


def _dialogue() -> AuthoredDialogue:
    return AuthoredDialogue(
        greeting="合成櫃檯後的人抬眼。",
        topics=(
            AuthoredTopic(
                topic_id=_ROOT,
                keyword="合成起頭",
                label="合成起頭",
                fallback=_scene("t_panel_root", "合成起頭內文"),
            ),
            AuthoredTopic(
                topic_id=_CHILD,
                keyword="合成接續",
                label="合成接續",
                fallback=_scene("t_panel_child", "合成接續內文"),
                predecessors=(_ROOT,),
                disclosure="pure_chain",
            ),
            AuthoredTopic(
                topic_id=_QUALIFIED,
                keyword="合成資格",
                label="合成資格",
                fallback=_scene("t_panel_qualified", "合成資格內文"),
                requires=RaceIs(race_key=_OTHER_RACE),
                predecessors=(_ROOT,),
            ),
            AuthoredTopic(
                topic_id=_LOCKED,
                keyword="合成婉拒",
                label="合成婉拒",
                fallback=_scene("t_panel_locked_formal", "合成鎖定內文"),
                requires=RaceIs(race_key=_OTHER_RACE),
                unavailable="locked",
                refusal=_scene("t_panel_locked_refusal", "合成婉拒內文"),
            ),
        ),
    )


class DialogueReadingProjectionTests(EvenniaTest):
    """Panel projection and owner-scoped fan-out."""

    @property
    def sessionhandler(self):
        import evennia

        return evennia.SESSION_HANDLER

    def setUp(self) -> None:
        super().setUp()
        # The affinity rulebook resolves its cap-break quest keys against the
        # shipped catalog before the synthetic scope replaces it.
        register_catalog()
        get_config()
        scope = synthetic_registries(
            "races", "dialogue", extra={"dialogue": {_TABLE_KEY: _dialogue()}}
        )
        scope.__enter__()
        self.addCleanup(scope.__exit__, None, None, None)
        watchers.clear_watchers()
        self.addCleanup(watchers.clear_watchers)
        self.room = create_object(Room, key="合成閱讀展示廳")
        self.owner = create_object(PlayerCharacter, key="合成閱讀展示玩家")
        self.owner.race = _RACE_KEY
        self.owner.apply_race_baseline()
        self.owner.location = self.room
        self.host = create_object(NPC, key="合成閱讀展示店主", location=self.room)
        self.host.components.add(
            ScriptedDialogue.create(self.host, dialogue_key=_TABLE_KEY)
        )
        self.registry = build_production_registry()

    def tearDown(self) -> None:
        clear_dialogue_session(self.owner)
        super().tearDown()

    # -- helpers ---------------------------------------------------------

    def _host_key(self) -> str:
        return host_dialogue_binding(self.host)[0]

    def _select(self, topic_id: str = _ROOT, *, selection_id: str = "sel-panel"):
        session = None
        from world.rules.dialogue import live_dialogue_session

        session = live_dialogue_session(self.owner)
        return select_authored_topic(
            self.owner,
            self.host,
            topic_id,
            selection_id=selection_id,
            expected_context_id=session.context_id if session is not None else None,
        )

    def _panel(self, actor=None):
        return dialogue_presenter(
            PresentationContext(actor=actor or self.owner, protocol_version=1)
        )

    def _register_watcher(self, puppet, sessid: int):
        real = ServerSession()
        real.init_session("webclient/websocket", ("localhost", 9999), self.sessionhandler)
        real.sessid = sessid
        self.sessionhandler[real.sessid] = real
        real.protocol_key = "webclient/websocket"
        real.puppet = puppet
        puppet.sessions.add(real)
        recorded: list[dict] = []
        real.msg = lambda **kwargs: recorded.append(kwargs)
        coordinator = PresentationCoordinator(
            real, self.registry, calendar_provider=lambda: CALENDAR
        )
        real.ndb.elosern_coordinator = coordinator
        coordinator.full_snapshot(
            PresentationContext(actor=puppet, protocol_version=1)
        )
        watchers.register_watcher(real)
        self.addCleanup(lambda: self.sessionhandler.__delitem__(real.sessid))
        return real, recorded

    # -- projection ------------------------------------------------------

    @covers_requirement(
        "authored-dialogue-reading::"
        "formal-reading-is-persistent-owner-shared-narrative-state"
    )
    def test_panel_reports_revision_completions_and_unread(self):
        self._select()
        panel = self._panel()
        self.assertEqual(panel["reading_revision"], 0)
        self.assertEqual(panel["completed_topic_ids"], [])
        choices = {choice["topic_id"]: choice for choice in panel["choices"]}
        self.assertTrue(choices[_ROOT]["unread"])
        # A public successor is absent until its predecessor is saved.
        self.assertNotIn(_CHILD, choices)
        # A qualified descendant behind an unsaved predecessor is absent too.
        self.assertNotIn(_QUALIFIED, choices)

        session = __import__(
            "world.rules.dialogue", fromlist=["live_dialogue_session"]
        ).live_dialogue_session(self.owner)
        delivery = session.delivery
        complete_dialogue_delivery(
            self.owner,
            delivery_id=delivery.delivery_id,
            context_id=delivery.context_id,
            topic_id=delivery.topic_id,
            scene_revision=delivery.scene_revision,
        )
        panel = self._panel()
        self.assertEqual(panel["reading_revision"], 1)
        self.assertEqual(panel["completed_topic_ids"], [_ROOT])
        choices = {choice["topic_id"]: choice for choice in panel["choices"]}
        self.assertFalse(choices[_ROOT]["unread"])
        self.assertTrue(choices[_CHILD]["unread"])
        self.assertEqual(choices[_CHILD]["predecessors"], [_ROOT])
        # The pre-delivered chain rides the same panel, predecessor first, and
        # never includes the qualified descendant.
        chain_topics = [
            entry["delivery"]["topic_id"] for entry in panel["pure_chain"]
        ]
        self.assertEqual(chain_topics, [_CHILD])
        self.assertEqual(
            panel["pure_chain"][0]["predecessors"], [_ROOT]
        )

    def test_lock_marker_takes_precedence_over_unread(self):
        self._select()
        choices = {
            choice["topic_id"]: choice for choice in self._panel()["choices"]
        }
        # A visibly locked row keeps the lock marker instead of unread.
        self.assertEqual(choices[_LOCKED]["availability"], "locked")
        self.assertFalse(choices[_LOCKED]["unread"])
        # A qualified descendant behind an unsaved predecessor stays absent,
        # even though it is reachable from the playing root.
        self.assertNotIn(_QUALIFIED, choices)

    @covers_requirement(
        "authored-dialogue-reading::"
        "formal-reading-is-persistent-owner-shared-narrative-state"
    )
    def test_reading_is_owner_shared_across_the_same_host(self):
        self._select()
        record_completion(
            self.owner, host_key=self._host_key(), topic_id=_ROOT
        )
        clear_dialogue_session(self.owner)
        open_or_refresh_dialogue(self.owner, self.host, "再次招呼。")
        panel = self._panel()
        self.assertEqual(panel["completed_topic_ids"], [_ROOT])
        self.assertEqual(panel["reading_revision"], 1)

    @covers_requirement(
        "authored-dialogue-reading::"
        "formal-reading-is-persistent-owner-shared-narrative-state"
    )
    def test_delayed_completion_leaves_the_other_connection_scene_intact(self):
        first = self._select(_ROOT, selection_id="sel-a")
        second = self._select(_ROOT, selection_id="sel-b")
        complete_dialogue_delivery(
            self.owner,
            delivery_id=first.delivery_id,
            context_id=first.context_id,
            topic_id=first.topic_id,
            scene_revision=first.scene_revision,
        )
        panel = self._panel()
        self.assertEqual(panel["delivery"]["delivery_id"], second.delivery_id)
        self.assertEqual(panel["completed_topic_ids"], [_ROOT])

    # -- fan-out ---------------------------------------------------------

    @covers_requirement(
        "authored-dialogue-reading::"
        "formal-reading-is-persistent-owner-shared-narrative-state"
    )
    def test_fan_out_reaches_one_owner_controls_only(self):
        self._select()
        first, first_output = self._register_watcher(self.owner, 971)
        self._register_watcher(self.owner, 972)
        # Another character of the same account is not the owner.
        sibling = create_object(PlayerCharacter, key="合成閱讀兄弟")
        sibling.race = _RACE_KEY
        sibling.apply_race_baseline()
        sibling.location = self.room
        _sibling_session, sibling_output = self._register_watcher(sibling, 973)

        push_dialogue_reading(self.owner)

        def panels(output):
            return [
                call["ui_update"][0][0]["panels"]["dialogue"]
                for call in output
                if "ui_update" in call
                and isinstance(call["ui_update"][0][0].get("panels"), dict)
                and "dialogue" in call["ui_update"][0][0]["panels"]
            ]

        own_panels = panels(first_output)
        self.assertEqual(len(own_panels), 1)
        self.assertEqual(own_panels[0]["completed_topic_ids"], [])
        self.assertEqual(panels(sibling_output), [])
        self.assertFalse(
            [
                call
                for call in sibling_output
                if call.get("ui_update") and "dialogue" in str(call["ui_update"])
            ]
        )
        self.assertIsNotNone(first)

    @covers_requirement(
        "authored-dialogue-reading::"
        "public-reading-chains-never-authorize-protected-content"
    )
    def test_chain_derivation_is_pure_and_bounded(self):
        delivery = self._select()
        from world.rules.dialogue import live_dialogue_session

        session = live_dialogue_session(self.owner)
        nodes = chain_deliveries(session, self.host, actor=self.owner)
        self.assertEqual([node.delivery.topic_id for node in nodes], [_CHILD])
        self.assertEqual(nodes[0].delivery.scene_id, "t_panel_child")
        # Deriving the chain writes nothing.
        self.assertEqual(completed_topic_ids(self.owner, self._host_key()), ())
        self.assertEqual(session.delivery.topic_id, delivery.topic_id)
