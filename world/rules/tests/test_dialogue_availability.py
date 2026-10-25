"""Behavior test: authored-dialogue availability projection and refresh.

Covers ``authored-dialogue-availability`` against a synthetic table:

- ``project_topics`` is the single disclosure view: hidden topics are absent,
  locked topics expose only ID/keyword/label/lock/canonical hint/descriptor,
  open topics expose descriptors only, and no projected row, panel choice,
  affordance descriptor or text answer contains any scene sentinel.
- A locked selection delivers the authored refusal with zero gameplay effect
  and no formal body; a topic that loses eligibility after a committed
  equipment change refuses (locked) or behaves as unknown (hidden).
- ``refresh_dialogue_availability`` fans the fresh panel out after commit,
  targets the currently acting body under possession, preserves the already
  delivered scene wording, and schedules nothing when the owning transaction
  rolls back.
- The text ``talk`` surface resolves its topics through the same rows.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from evennia.server.serversession import ServerSession
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from commands.talk import CmdsTalk
from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.components import ScriptedDialogue
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from web.webclient.presentation import watchers
from web.webclient.presentation.affordances import (
    _scripted_entries,
    _scripted_keyword_descriptors,
)
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.coordinator import PresentationCoordinator
from web.webclient.presentation.registry import build_production_registry
from world.lore.dialogue.conditions import Carries, RaceIs
from world.lore.dialogue.conditions import QuestIs
from world.lore.dialogue.shape import AuthoredDialogue, AuthoredTopic, SceneVariant
from world.lore.scenes import Scene, Speech
from world.quests.catalog import register_catalog
from world.quests.runtime import QuestRecord, QuestState, to_storage
from world.rules.dialogue import (
    TopicNotFoundError,
    clear_dialogue_session,
    live_dialogue_session,
    select_authored_topic,
)
from world.rules.dialogue_conditions import condition_hint
from world.rules.dialogue_availability import (
    TOPIC_LOCKED,
    TOPIC_OPEN,
    availability_context,
    project_topics,
    refresh_dialogue_availability,
)
from world.rules.affinity_config import get_config
from world.rules.dialogue_references import static_dialogue_references
from world.rules.party import join_party
from world.rules.possession import enter_possession, release_possession
from world.tests.synthetic_data import SYNTH_ITEMS, SYNTH_RACES, synthetic_registries
from world.tests.synthetic_data.data_presets_quests import SYNTH_GUILD_ISSUER_KEY

_TABLE_KEY = "t_availability_keeper"
_OPEN_TOPIC = f"{_TABLE_KEY}.open"
_LOCKED_TOPIC = f"{_TABLE_KEY}.locked"
_HIDDEN_TOPIC = f"{_TABLE_KEY}.hidden"
_CHAINED_TOPIC = f"{_TABLE_KEY}.chained"
_VARIED_TOPIC = f"{_TABLE_KEY}.varied"
_QUEST_TOPIC = f"{_TABLE_KEY}.quest"

_OPEN_KEYWORD = "合成公開"
_LOCKED_KEYWORD = "合成鎖定"
_HIDDEN_KEYWORD = "合成隱藏"
_CHAINED_KEYWORD = "合成接續"
_VARIED_KEYWORD = "合成變體"
_QUEST_KEYWORD = "合成委託"

_QUEST_KEY = "t_ember_cull"

_RACE_KEY = next(iter(SYNTH_RACES))
_OTHER_RACE_KEY = next(key for key in SYNTH_RACES if key != _RACE_KEY)
_ITEM_KEY = SYNTH_ITEMS["t_ember_spray"].key

#: One sentinel per authored body. No pre-selection payload may contain any of
#: them; only the selected scene (or the selected refusal) may.
_SENTINEL_OPEN = "SENTINEL-OPEN-BODY"
_SENTINEL_LOCKED_FORMAL = "SENTINEL-LOCKED-FORMAL"
_SENTINEL_LOCKED_REFUSAL = "SENTINEL-LOCKED-REFUSAL"
_SENTINEL_HIDDEN = "SENTINEL-HIDDEN-BODY"
_SENTINEL_CHAIN = "SENTINEL-CHAIN-BODY"
_SENTINEL_VARIANT = "SENTINEL-VARIANT-BODY"
_SENTINEL_FALLBACK = "SENTINEL-VARIED-FALLBACK"
_SENTINEL_PRIVATE = "SENTINEL-PRIVATE-VARIANT"
_SENTINEL_QUEST_FORMAL = "SENTINEL-QUEST-FORMAL"
_SENTINEL_QUEST_REFUSAL = "SENTINEL-QUEST-REFUSAL"
_ALL_SENTINELS = (
    _SENTINEL_OPEN,
    _SENTINEL_LOCKED_FORMAL,
    _SENTINEL_LOCKED_REFUSAL,
    _SENTINEL_HIDDEN,
    _SENTINEL_CHAIN,
    _SENTINEL_VARIANT,
    _SENTINEL_FALLBACK,
    _SENTINEL_PRIVATE,
    _SENTINEL_QUEST_FORMAL,
    _SENTINEL_QUEST_REFUSAL,
)

CALENDAR = SimpleNamespace(
    year=1,
    season_index=0,
    season_name="春季",
    day_in_season=3,
    hour=12,
    minute=0,
    second=0,
)


def _scene(scene_id: str, host_text: str) -> Scene:
    return Scene(
        scene_id=scene_id,
        revision="r1",
        lines=(
            Speech(speaker="actor", text="合成問句。"),
            Speech(speaker="host", text=host_text),
        ),
    )


def _dialogue() -> AuthoredDialogue:
    return AuthoredDialogue(
        greeting="合成櫃檯後的人抬眼：「有話直說。」",
        topics=(
            AuthoredTopic(
                topic_id=_OPEN_TOPIC,
                keyword=_OPEN_KEYWORD,
                label="合成公開",
                fallback=_scene("t_availability_open", _SENTINEL_OPEN),
            ),
            AuthoredTopic(
                topic_id=_LOCKED_TOPIC,
                keyword=_LOCKED_KEYWORD,
                label="合成鎖定",
                fallback=_scene("t_availability_locked_formal", _SENTINEL_LOCKED_FORMAL),
                requires=Carries(item_key=_ITEM_KEY),
                unavailable="locked",
                refusal=_scene("t_availability_locked_refusal", _SENTINEL_LOCKED_REFUSAL),
            ),
            AuthoredTopic(
                topic_id=_HIDDEN_TOPIC,
                keyword=_HIDDEN_KEYWORD,
                label="合成隱藏",
                fallback=_scene("t_availability_hidden", _SENTINEL_HIDDEN),
                requires=RaceIs(race_key=_OTHER_RACE_KEY),
                unavailable="hidden",
            ),
            AuthoredTopic(
                topic_id=_CHAINED_TOPIC,
                keyword=_CHAINED_KEYWORD,
                label="合成接續",
                fallback=_scene("t_availability_chain", _SENTINEL_CHAIN),
                predecessors=(_OPEN_TOPIC,),
                disclosure="pure_chain",
            ),
            AuthoredTopic(
                topic_id=_VARIED_TOPIC,
                keyword=_VARIED_KEYWORD,
                label="合成變體",
                fallback=_scene("t_availability_varied_fallback", _SENTINEL_FALLBACK),
                variants=(
                    SceneVariant(
                        variant_id="carries_item",
                        priority=10,
                        when=Carries(item_key=_ITEM_KEY),
                        scene=_scene("t_availability_varied_variant", _SENTINEL_VARIANT),
                    ),
                    SceneVariant(
                        variant_id="private",
                        priority=5,
                        when=RaceIs(race_key=_OTHER_RACE_KEY),
                        scene=_scene("t_availability_varied_private", _SENTINEL_PRIVATE),
                    ),
                ),
            ),
            AuthoredTopic(
                topic_id=_QUEST_TOPIC,
                keyword=_QUEST_KEYWORD,
                label="合成委託",
                fallback=_scene("t_availability_quest_formal", _SENTINEL_QUEST_FORMAL),
                requires=QuestIs(definition_key=_QUEST_KEY, state="completed"),
                unavailable="locked",
                refusal=_scene("t_availability_quest_refusal", _SENTINEL_QUEST_REFUSAL),
            ),
        ),
    )


def _completed_quest_record(quest_id: str) -> dict:
    """One strict storage dict for the owner's completed quest log."""
    return to_storage(
        QuestRecord(
            quest_id=quest_id,
            definition_key=_QUEST_KEY,
            issuer_key=SYNTH_GUILD_ISSUER_KEY,
            state=QuestState.COMPLETED,
            stage_index=0,
            stage_progress=0,
            deadline_tick=None,
            accepted_tick=0,
            stage_room_id=None,
            objective_target_ids=(),
            protected_entity_ids=(),
            failure_reason=None,
            invalidated_reason=None,
        )
    )


def _strings(value):
    """Every string inside a nested JSON-safe payload."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, (list, tuple, set, frozenset)):
        for item in value:
            yield from _strings(item)


def _body_sentinels(payload) -> list[str]:
    return [
        text
        for text in _strings(payload)
        if any(sentinel in text for sentinel in _ALL_SENTINELS)
    ]


class DialogueAvailabilityTests(EvenniaTest):
    """Projection, selection refusal, committed-state recheck and refresh."""

    @property
    def sessionhandler(self):
        import evennia

        return evennia.SESSION_HANDLER

    def setUp(self) -> None:
        super().setUp()
        # The affinity rulebook's cap breaks resolve their quest keys.
        register_catalog()
        # Resolve the cached rulebook against the shipped quest catalog before
        # the synthetic quest scope replaces it, exactly like the runtime.
        get_config()
        self.scope = synthetic_registries(
            "races",
            "items",
            "quest_definitions",
            "dialogue",
            extra={"dialogue": {_TABLE_KEY: _dialogue()}},
        )
        self.scope.__enter__()
        self.addCleanup(self.scope.__exit__, None, None, None)
        watchers.clear_watchers()
        self.addCleanup(watchers.clear_watchers)

        self.room = create_object(Room, key="合成可用性廳")
        self.player = create_object(PlayerCharacter, key="合成可用性玩家")
        self.player.race = _RACE_KEY
        self.player.apply_race_baseline()
        self.player.db.inventory = []
        self.player.location = self.room
        self.host = create_object(NPC, key="合成可用性店主", location=self.room)
        self.host.components.add(
            ScriptedDialogue.create(self.host, dialogue_key=_TABLE_KEY)
        )
        self.registry = build_production_registry()

    def tearDown(self) -> None:
        clear_dialogue_session(self.player)
        if self.player.db.possession:
            release_possession(self.player, reason="handback")
        super().tearDown()

    # -- helpers ---------------------------------------------------------

    def _context(self):
        return availability_context(self.player, self.host)

    def _rows(self, *, context_id=None):
        return {
            row.topic_id: row
            for row in project_topics(self._context(), context_id=context_id)
        }

    def _select(self, topic_id: str, *, selection_id="sel-avail", context_id=None):
        return select_authored_topic(
            self.player,
            self.host,
            topic_id,
            selection_id=selection_id,
            expected_context_id=context_id,
        )

    def _register_watcher(self, puppet):
        real = ServerSession()
        real.init_session("webclient/websocket", ("localhost", 9999), self.sessionhandler)
        real.sessid = 947
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
        return real, coordinator, recorded

    # -- projection ------------------------------------------------------

    @covers_requirement(
        "authored-dialogue-selection::text-and-browser-resolve-the-same-authored-topic"
    )
    def test_projection_is_the_only_disclosure_view(self):
        rows = self._rows()
        self.assertEqual(
            set(rows),
            {_OPEN_TOPIC, _LOCKED_TOPIC, _VARIED_TOPIC, _QUEST_TOPIC},
        )
        self.assertEqual(rows[_OPEN_TOPIC].availability, TOPIC_OPEN)
        self.assertIsNone(rows[_OPEN_TOPIC].requirement_hint)
        self.assertEqual(rows[_VARIED_TOPIC].availability, TOPIC_OPEN)
        self.assertEqual(rows[_QUEST_TOPIC].availability, TOPIC_LOCKED)

        locked = rows[_LOCKED_TOPIC]
        self.assertEqual(locked.availability, TOPIC_LOCKED)
        # The canonical hint is the SAME declaration render, and it names the
        # requirement's canonical label, never a body or a numeric value.
        declaration = next(
            topic for topic in _dialogue().topics if topic.topic_id == _LOCKED_TOPIC
        )
        self.assertEqual(
            locked.requirement_hint,
            condition_hint(declaration.requires, self._context()),
        )
        self.assertIn(
            static_dialogue_references().label("item", _ITEM_KEY),
            locked.requirement_hint,
        )
        self.assertEqual(locked.keyword, _LOCKED_KEYWORD)
        self.assertEqual(locked.label, "合成鎖定")
        self.assertEqual(
            locked.descriptor,
            {
                "npc_id": int(self.host.pk),
                "topic_id": _LOCKED_TOPIC,
                "context_id": None,
            },
        )
        # Recursive sentinel absence over the whole projection, including the
        # locked row's hint and descriptor.
        self.assertEqual(
            _body_sentinels([row.__dict__ for row in rows.values()]), []
        )

    @covers_requirement(
        "authored-dialogue-conditions::combination-hints-and-complete-scene-variants-share-declarations"
    )
    def test_hidden_and_predecessor_topics_are_absent(self):
        rows = self._rows()
        self.assertNotIn(_HIDDEN_TOPIC, rows)
        self.assertNotIn(_CHAINED_TOPIC, rows)
        # An explicit hidden ID behaves exactly like an unknown one.
        with self.assertRaises(TopicNotFoundError):
            self._select(_HIDDEN_TOPIC)
        with self.assertRaises(TopicNotFoundError):
            self._select(_CHAINED_TOPIC)
        self.assertIsNone(self.player.db.dialogue_session)

    @covers_requirement("exploration-affordances::affordance-params-are-validator-normalized")
    def test_affordance_and_panel_carry_descriptors_only(self):
        entries = [view.as_dict() for view in _scripted_entries(self.host, actor=self.player)]
        self.assertEqual(
            [entry["params"]["topic_id"] for entry in entries],
            [_OPEN_TOPIC, _LOCKED_TOPIC, _VARIED_TOPIC, _QUEST_TOPIC],
        )
        for entry in entries:
            self.assertEqual(set(entry["params"]), {"npc_id", "topic_id", "context_id"})

        choices = _scripted_keyword_descriptors(
            self.host, actor=self.player, context_id=None
        )
        self.assertEqual(
            [(choice["topic_id"], choice["availability"]) for choice in choices],
            [
                (_OPEN_TOPIC, TOPIC_OPEN),
                (_LOCKED_TOPIC, TOPIC_LOCKED),
                (_VARIED_TOPIC, TOPIC_OPEN),
                (_QUEST_TOPIC, TOPIC_LOCKED),
            ],
        )
        locked_choice = choices[1]
        self.assertEqual(
            set(locked_choice),
            {
                "topic_id",
                "keyword_id",
                "label",
                "availability",
                "requirement_hint",
                "unread",
                "predecessors",
                "action_payload",
            },
        )
        self.assertIsInstance(locked_choice["requirement_hint"], str)
        self.assertEqual(
            _body_sentinels({"entries": entries, "choices": choices}), []
        )

    # -- selection -------------------------------------------------------

    @covers_requirement(
        "authored-dialogue-selection::authored-selection-delivers-complete-scenes-atomically"
    )
    def test_locked_selection_plays_the_refusal_with_zero_effects(self):
        affinity_before = self.host.relations.affinity_for(self.player)
        delivery = self._select(_LOCKED_TOPIC)
        self.assertEqual(delivery.kind, "refusal")
        self.assertEqual(delivery.scene_id, "t_availability_locked_refusal")
        texts = [line.text for line in delivery.lines]
        self.assertIn(_SENTINEL_LOCKED_REFUSAL, texts)
        self.assertNotIn(_SENTINEL_LOCKED_FORMAL, texts)
        self.assertEqual(self.host.relations.affinity_for(self.player), affinity_before)
        self.assertEqual(list(self.player.db.inventory), [])

        # The refusal is recorded for playback/dedup but is not a completion.
        session = live_dialogue_session(self.player)
        self.assertIsNotNone(session)
        self.assertEqual(session.delivery.kind, "refusal")
        self.assertEqual(session.completion_receipts, ())
        receipt = session.selection_receipts[-1]
        self.assertEqual(receipt["topic_id"], _LOCKED_TOPIC)

        # A duplicate transport retry returns the same delivery, no new effect.
        replay = self._select(
            _LOCKED_TOPIC,
            selection_id="sel-avail",
            context_id=session.context_id,
        )
        self.assertEqual(replay.delivery_id, delivery.delivery_id)
        self.assertEqual(self.host.relations.affinity_for(self.player), affinity_before)

    @covers_requirement(
        "authored-dialogue-conditions::combination-hints-and-complete-scene-variants-share-declarations"
    )
    def test_committed_equipment_change_invalidates_a_listed_choice(self):
        self.player.db.inventory = [_ITEM_KEY]
        self.player.race = _OTHER_RACE_KEY
        self.player.apply_race_baseline()
        rows = self._rows()
        self.assertEqual(rows[_LOCKED_TOPIC].availability, TOPIC_OPEN)
        # Under the other race the race-guarded topic is openly listed.
        self.assertIn(_HIDDEN_TOPIC, rows)

        # Committed canonical change: the carried item is gone.
        affinity_before = self.host.relations.affinity_for(self.player)
        self.player.db.inventory = []
        stale_delivery = self._select(_LOCKED_TOPIC)
        self.assertEqual(stale_delivery.kind, "refusal")
        self.assertNotIn(
            _SENTINEL_LOCKED_FORMAL, [line.text for line in stale_delivery.lines]
        )
        self.assertEqual(self.host.relations.affinity_for(self.player), affinity_before)
        self.assertEqual(list(self.player.db.inventory), [])

        # A topic that was open by race is now hidden, i.e. unknown.
        clear_dialogue_session(self.player)
        self.player.race = _RACE_KEY
        self.player.apply_race_baseline()
        self.assertNotIn(_HIDDEN_TOPIC, self._rows())

    @covers_requirement(
        "authored-dialogue-conditions::combination-hints-and-complete-scene-variants-share-declarations"
    )
    def test_delivered_wording_survives_an_availability_refresh(self):
        self.player.db.inventory = [_ITEM_KEY]
        delivery = self._select(_VARIED_TOPIC, selection_id="sel-varied")
        self.assertEqual(delivery.scene_id, "t_availability_varied_variant")
        session = live_dialogue_session(self.player)
        self.assertIsNotNone(session)

        real, _coordinator, recorded = self._register_watcher(self.player)
        # Committed change: the carried item is gone, so the delivered variant
        # no longer matches and the locked topic falls back to its refusal.
        self.player.db.inventory = []

        with self.captureOnCommitCallbacks(execute=True):
            refresh_dialogue_availability(self.player, cause="equipment")

        self.assertIs(watchers.watchers_for(self.player)[0][0], real)
        updates = [call["ui_update"][0][0] for call in recorded if "ui_update" in call]
        self.assertTrue(updates, "refresh must fan the current panel out")
        panel = updates[-1]["panels"]["dialogue"]
        self.assertIs(panel["available"], True)
        # The already delivered scene keeps its authored wording...
        self.assertEqual(panel["delivery"]["delivery_id"], delivery.delivery_id)
        self.assertEqual(panel["delivery"]["scene_id"], "t_availability_varied_variant")
        self.assertEqual(
            [line["text"] for line in panel["delivery"]["lines"]],
            [line.text for line in delivery.lines],
        )
        # ...while the choices are re-projected from current canonical state.
        choices = {choice["topic_id"]: choice for choice in panel["choices"]}
        self.assertEqual(choices[_LOCKED_TOPIC]["availability"], TOPIC_LOCKED)
        self.assertIsInstance(choices[_LOCKED_TOPIC]["requirement_hint"], str)
        self.assertNotIn(_HIDDEN_TOPIC, choices)
        self.assertNotIn(_CHAINED_TOPIC, choices)
        # Only the retained delivery may carry authored prose; the projection
        # fields never do.
        self.assertIn(
            _SENTINEL_VARIANT, [line["text"] for line in panel["delivery"]["lines"]]
        )
        self.assertEqual(
            _body_sentinels(
                {
                    "choices": panel["choices"],
                    "host": panel["host"],
                    "actor": panel["actor"],
                }
            ),
            [],
        )
        self.assertEqual(session.delivery.scene_id, "t_availability_varied_variant")

    @covers_requirement(
        "authored-dialogue-conditions::quest-predicates-distinguish-lifecycle-and-reward-claims"
    )
    def test_committed_quest_state_opens_and_recloses_the_same_topic(self):
        self.assertEqual(self._rows()[_QUEST_TOPIC].availability, TOPIC_LOCKED)

        # Committed owner progression: one completed quest record.
        self.player.db.quest_log = [_completed_quest_record("q-avail")]
        self.assertEqual(self._rows()[_QUEST_TOPIC].availability, TOPIC_OPEN)
        delivery = self._select(_QUEST_TOPIC, selection_id="sel-quest")
        self.assertEqual(delivery.kind, "formal")
        self.assertEqual(delivery.scene_id, "t_availability_quest_formal")
        self.assertIn(_SENTINEL_QUEST_FORMAL, [line.text for line in delivery.lines])
        self.assertEqual(self.player.db.guild_reward_claims, None)

        # Committed reversal: the record is gone before the next selection.
        session = live_dialogue_session(self.player)
        self.player.db.quest_log = []
        refusal = self._select(
            _QUEST_TOPIC,
            selection_id="sel-quest-2",
            context_id=session.context_id,
        )
        self.assertEqual(refusal.kind, "refusal")
        self.assertEqual(refusal.scene_id, "t_availability_quest_refusal")
        self.assertNotIn(
            _SENTINEL_QUEST_FORMAL, [line.text for line in refusal.lines]
        )
        self.assertEqual(self.player.db.quest_log, [])

    @covers_requirement("webclient-dialogue-session::the-dialogue-session-is-deterministic-core-only-character-state")
    def test_refresh_is_rollback_safe(self):
        from django.db import transaction

        real, _coordinator, recorded = self._register_watcher(self.player)
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            try:
                with transaction.atomic():
                    refresh_dialogue_availability(self.player, cause="quest")
                    raise RuntimeError("owning write rolled back")
            except RuntimeError:
                pass
        self.assertEqual(list(callbacks), [])
        self.assertFalse(
            [call for call in recorded if "ui_update" in call],
            "a rolled-back write must not fan availability out",
        )
        self.assertIsNotNone(real)

    @covers_requirement("authored-dialogue-conditions::progression-conditions-resolve-the-owner-and-host-relationship")
    def test_refresh_targets_the_currently_acting_body_under_possession(self):
        companion = create_object(NPC, key="合成附身同伴", location=self.room)
        join_party(companion, self.player)
        enter_possession(self.player, companion)
        self.addCleanup(release_possession, self.player, companion, "handback")

        with patch(
            "web.webclient.presentation.dialogue_push.push_dialogue_update"
        ) as push:
            with self.captureOnCommitCallbacks(execute=True):
                refresh_dialogue_availability(self.player, cause="control")
        push.assert_called_once_with(companion)

    # -- text surface ----------------------------------------------------

    def _run_talk(self, args: str) -> str:
        messages: list[str] = []
        with patch.object(self.player, "msg", side_effect=messages.append):
            command = CmdsTalk()
            command.caller = self.player
            command.args = args
            command.func()
        return "\n".join(messages)

    @covers_requirement("scripted-dialogue::scripted-dialogue-hosts-answer-authored-talk-lines")
    def test_text_listing_uses_the_projection(self):
        hidden = self._run_talk(f"{self.host.key} {_HIDDEN_KEYWORD}")
        self.assertEqual(_body_sentinels(hidden), [])
        self.assertNotIn(_SENTINEL_HIDDEN, hidden)
        self.assertIsNone(live_dialogue_session(self.player))

        affinity_before = self.host.relations.affinity_for(self.player)
        locked = self._run_talk(f"{self.host.key} {_LOCKED_KEYWORD}")
        self.assertIn(_SENTINEL_LOCKED_REFUSAL, locked)
        self.assertNotIn(_SENTINEL_LOCKED_FORMAL, locked)
        self.assertEqual(self.host.relations.affinity_for(self.player), affinity_before)

        opened = self._run_talk(f"{self.host.key} {_OPEN_KEYWORD}")
        self.assertIn(_SENTINEL_OPEN, opened)


if __name__ == "__main__":
    import unittest

    unittest.main()
