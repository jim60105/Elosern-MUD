"""Behavior test: committed lifecycle-source dialogue availability refresh.

Covers ``authored-dialogue-refresh-lifecycle`` against the shared synthetic kit.
Each exact source-matrix writer is exercised through its real deterministic
entry point with no WebClient action context:

- guild registration/rank promotion (``register_adventurer``,
  ``settle_exam_outcome``), every quest lifecycle state
  (``apply_quest_log_delta``), reward claims (``write_reward_claims``), host
  affinity (``seed_affinity``/``apply_affinity_change``), companion membership
  (``_write_binding``/``purge_npc_memberships``), companion presence
  (``at_post_move``/``at_object_delete``), the world clock
  (``WorldClock.advance``) and possession control
  (``enter_possession``/``release_possession``).
- Every refresh is registered on the owning transaction: an outer rollback
  publishes nothing, a write with no session creates no conversation, and the
  callback re-resolves the final committed state.
- A world-time commit reaches an idle owner independent of the initiating
  action's entity scope, and a non-boundary advance schedules nothing.
- A departed or deleted companion relocks an unrelated host's conversation,
  while the delivered scene and saved reading survive ordinary refreshes.
- Control entry retires the old acting body's session and release republishes
  the new body's view without copying the obsolete possessed scene.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from django.db import transaction
from evennia.objects.models import ObjectDB
from evennia.server.serversession import ServerSession
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.components import GuildStaff, ScriptedDialogue
from typeclasses.npcs import LLMNPC, NPC
from typeclasses.rooms import AnchorRoom, Room
from web.webclient.presentation import watchers
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.coordinator import PresentationCoordinator
from web.webclient.presentation.registry import build_production_registry
from world.lore.dialogue.conditions import (
    AffinityAtLeast,
    CompanionPresent,
    GuildRankAtLeast,
    QuestIs,
    TimePeriod,
)
from world.lore.dialogue.shape import AuthoredDialogue, AuthoredTopic
from world.lore.guild import GuildRank
from world.lore.scenes import Scene, Speech
from world.narrative.dialogue_reading import (
    completed_topic_ids,
    record_completion,
)
from world.quests.catalog import register_catalog
from world.quests.compile.compiler import compile_blueprint_core
from world.quests.encounter_activation import activate_scene_encounter
from world.quests.encounters import publish_scene_package
from world.quests.runtime import (
    INVALIDATED_OBSOLETE_OUTCOME,
    OBSOLETE_OUTCOME_MESSAGE,
    QuestRecord,
    QuestState,
)
from world.quests.story_dialogue import transition_story_dialogue
from world.quests.tests._compile_helpers import _anchor_key
from world.quests.tests._fixtures import RegistryIsolationMixin, register_catalog_once
from world.quests.tests._scene_package_fixtures import (
    LONG_PROSE,
    dialogue as package_dialogue,
    package as package_payload,
)
from world.quests.transitions import apply_quest_log_delta
from world.rules.affinity import AffinitySource, apply_affinity_change, seed_affinity
from world.rules.affinity_config import get_config
from world.rules.clock import AdvanceSource, get_world_clock
from world.rules.dialogue import (
    clear_dialogue_session,
    greeting_for,
    live_dialogue_session,
    open_or_refresh_dialogue,
    select_authored_topic,
)
from world.rules.dialogue_availability import (
    TOPIC_OPEN,
    affected_dialogue_owners,
    queue_dialogue_refresh,
    session_bearing_dialogue_bodies,
    session_bearing_dialogue_owners,
)
from world.rules.dialogue_context import host_dialogue_binding
from world.rules.dialogue_references import static_dialogue_references
from world.rules.guild import register_adventurer, write_reward_claims
from world.rules.guild_exams import (
    ExamState,
    GuildExamRecord,
    settle_exam_outcome,
    to_storage as exam_to_storage,
)
from world.rules.party import join_party, leave_party
from world.rules.possession import enter_possession, release_possession
from world.tests.synthetic_data import SYNTH_RACES, synthetic_registries
from world.tests.synthetic_data.data_presets_quests import (
    SYNTH_GUILD_BRANCH_KEY,
    SYNTH_GUILD_ISSUER_KEY,
)
_RACE_KEY = next(iter(SYNTH_RACES))
_QUEST_KEY = "t_ember_cull"
_OPEN_RANK = "F"
_PROMOTED_RANK = "t_silver"
_RANKS = {
    _OPEN_RANK: GuildRank(
        _OPEN_RANK, 1, 50, 400, "Synthetic starting rank.", "t_synth_first_hunt"
    ),
    _PROMOTED_RANK: GuildRank(
        _PROMOTED_RANK,
        2,
        400,
        4_000,
        "Synthetic promoted rank.",
        "t_synth_lodging_friend",
    ),
}

_TABLE_KEY = "t_lifecycle_keeper"
_OPEN_TOPIC = f"{_TABLE_KEY}.open"
_RANK_TOPIC = f"{_TABLE_KEY}.rank"
_PROMOTED_TOPIC = f"{_TABLE_KEY}.promoted"
_QUEST_TOPIC = f"{_TABLE_KEY}.quest"
_AFFINITY_TOPIC = f"{_TABLE_KEY}.affinity"
_COMPANION_TOPIC = f"{_TABLE_KEY}.companion"
_TIME_TOPIC = f"{_TABLE_KEY}.time"

_SENTINEL_DELIVERED = "SENTINEL-LIFECYCLE-DELIVERED"

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
            Speech(speaker="actor", text="合成生命週期問句。"),
            Speech(speaker="host", text=host_text),
        ),
    )


def _dialogue(*, profile_key: str, stage_key: str) -> AuthoredDialogue:
    """One table with a synthetic topic per wired lifecycle source."""
    return AuthoredDialogue(
        greeting="合成生命週期店主抬眼：「有事就問。」",
        topics=(
            AuthoredTopic(
                topic_id=_OPEN_TOPIC,
                keyword="合成開場",
                label="合成開場",
                fallback=_scene("t_lifecycle_open", _SENTINEL_DELIVERED),
            ),
            AuthoredTopic(
                topic_id=_RANK_TOPIC,
                keyword="合成入會",
                label="合成入會",
                fallback=_scene("t_lifecycle_rank", "合成入會答覆。"),
                requires=GuildRankAtLeast(rank_key=_OPEN_RANK),
                unavailable="hidden",
            ),
            AuthoredTopic(
                topic_id=_PROMOTED_TOPIC,
                keyword="合成晉升",
                label="合成晉升",
                fallback=_scene("t_lifecycle_promoted", "合成晉升答覆。"),
                requires=GuildRankAtLeast(rank_key=_PROMOTED_RANK),
                unavailable="hidden",
            ),
            AuthoredTopic(
                topic_id=_QUEST_TOPIC,
                keyword="合成委託",
                label="合成委託",
                fallback=_scene("t_lifecycle_quest", "合成委託答覆。"),
                requires=QuestIs(definition_key=_QUEST_KEY, state="in_progress"),
                unavailable="hidden",
            ),
            AuthoredTopic(
                topic_id=_AFFINITY_TOPIC,
                keyword="合成情誼",
                label="合成情誼",
                fallback=_scene("t_lifecycle_affinity", "合成情誼答覆。"),
                requires=AffinityAtLeast(stage_key=stage_key),
                unavailable="hidden",
            ),
            AuthoredTopic(
                topic_id=_COMPANION_TOPIC,
                keyword="合成同行",
                label="合成同行",
                fallback=_scene("t_lifecycle_companion", "合成同行答覆。"),
                requires=CompanionPresent(source_kind="profile", source_key=profile_key),
                unavailable="hidden",
            ),
            AuthoredTopic(
                topic_id=_TIME_TOPIC,
                keyword="合成時刻",
                label="合成時刻",
                fallback=_scene("t_lifecycle_time", "合成時刻答覆。"),
                requires=TimePeriod(start_daypart="dawn", end_daypart="noon"),
                unavailable="hidden",
            ),
        ),
    )


def _quest_record(
    state: QuestState, quest_id: str = "t_lifecycle_quest:1"
) -> QuestRecord:
    return QuestRecord(
        quest_id=quest_id,
        definition_key=_QUEST_KEY,
        issuer_key=SYNTH_GUILD_ISSUER_KEY,
        state=state,
        stage_index=0,
        stage_progress=0,
        deadline_tick=None,
        accepted_tick=0,
        stage_room_id=None,
        objective_target_ids=(),
        protected_entity_ids=(),
        failure_reason="synthetic deadline" if state is QuestState.FAILED else None,
        invalidated_reason=(
            {
                "code": INVALIDATED_OBSOLETE_OUTCOME,
                "message": OBSOLETE_OUTCOME_MESSAGE,
            }
            if state is QuestState.INVALIDATED
            else None
        ),
    )


def _exam_record(exam_id: str, *, character_id: int, target_rank: str) -> dict:
    return exam_to_storage(
        GuildExamRecord(
            exam_id=exam_id,
            character_id=character_id,
            target_rank=target_rank,
            requested_by="synthetic examiner",
            opponent_id=character_id,
            session_id=f"session-{exam_id}",
            state=ExamState.ACTIVE,
            terminal_reason=None,
        )
    )


class _WatcherMixin:
    """Register real cached webclient sessions and read their pushed panels."""

    _sessid = 700

    def _register_watcher(self, puppet):
        real = ServerSession()
        real.init_session(
            "webclient/websocket", ("localhost", 9999), self.sessionhandler
        )
        self._sessid += 1
        real.sessid = self._sessid
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

    @property
    def sessionhandler(self):
        import evennia

        return evennia.SESSION_HANDLER

    @staticmethod
    def _panels(recorded: list[dict]) -> list[dict]:
        panels = []
        for call in recorded:
            message = call.get("ui_snapshot") or call.get("ui_update")
            if message:
                panels.append(message[0][0]["panels"])
        return panels

    def _dialogue_panel(self, recorded: list[dict]) -> dict:
        panels = self._panels(recorded)
        self.assertTrue(panels, "the committed refresh must fan a panel out")
        return panels[-1]["dialogue"]

    def _choices(self, recorded: list[dict]) -> dict[str, dict]:
        dialogue = self._dialogue_panel(recorded)
        if not dialogue.get("available"):
            return {}
        return {choice["topic_id"]: choice for choice in dialogue["choices"]}


class DialogueRefreshLifecycleTests(_WatcherMixin, EvenniaTest):
    """The committed owner, membership, world-time and control writers."""

    def setUp(self) -> None:
        super().setUp()
        register_catalog()
        self.stages = get_config().stages
        self.profile_key = next(
            iter(static_dialogue_references().keys_for("profile"))
        )
        self.scope = synthetic_registries(
            "races",
            "guild_ranks",
            "guild_branches",
            "titles",
            "quest_definitions",
            "dialogue",
            extra={
                "guild_ranks": _RANKS,
                "dialogue": {
                    _TABLE_KEY: _dialogue(
                        profile_key=self.profile_key,
                        stage_key=self.stages[2].id,
                    )
                },
            },
        )
        self.scope.__enter__()
        self.addCleanup(self.scope.__exit__, None, None, None)
        watchers.clear_watchers()
        self.addCleanup(watchers.clear_watchers)

        self.room = create_object(Room, key="合成生命週期廳")
        self.player = create_object(PlayerCharacter, key="合成生命週期玩家")
        self.player.race = _RACE_KEY
        self.player.apply_race_baseline()
        self.player.db.inventory = []
        self.player.location = self.room
        self.host = create_object(NPC, key="合成生命週期店主", location=self.room)
        self.host.components.add(
            ScriptedDialogue.create(self.host, dialogue_key=_TABLE_KEY)
        )
        self.host.components.add(
            GuildStaff.create(
                self.host, service_id="staff", branch_key=SYNTH_GUILD_BRANCH_KEY
            )
        )
        self.registry = build_production_registry()
        self.companions: list[Any] = []

    def tearDown(self) -> None:
        if self.player.db.possession:
            release_possession(self.player, reason="handback")
        clear_dialogue_session(self.player)
        for companion in self.companions:
            if getattr(companion, "pk", None):
                clear_dialogue_session(companion)
        super().tearDown()

    # -- helpers ---------------------------------------------------------

    def _open_line_session(self) -> None:
        open_or_refresh_dialogue(self.player, self.host, "合成招呼。")

    def _deliver_open_topic(self):
        session = live_dialogue_session(self.player)
        return select_authored_topic(
            self.player,
            self.host,
            _OPEN_TOPIC,
            selection_id="sel-lifecycle-open",
            expected_context_id=None if session is None else session.context_id,
        )

    def _companion(self) -> LLMNPC:
        companion = create_object(
            LLMNPC, key="合成生命週期同行者", location=self.room
        )
        companion.race = _RACE_KEY
        companion.apply_race_baseline()
        companion.db.inventory = []
        companion.db.npc_persona_meta = {
            "persona_version": 1,
            "provenance": {"kind": "profile", "profile": self.profile_key},
        }
        join_party(companion, self.player)
        self.companions.append(companion)
        return companion

    # -- guild registration and rank -------------------------------------

    @covers_requirement(
        "authored-dialogue-availability::"
        "physical-condition-mutations-refresh-live-dialogue-after-commit"
    )
    def test_registration_and_rank_promotion_refresh_independently(self):
        self._open_line_session()
        _real, recorded = self._register_watcher(self.player)
        self.assertNotIn(_RANK_TOPIC, self._choices(recorded))

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            register_adventurer(self.player, staff=self.host)
        self.assertGreaterEqual(len(list(callbacks)), 1)
        self.assertEqual(
            self._choices(recorded)[_RANK_TOPIC]["availability"], TOPIC_OPEN
        )
        self.assertNotIn(_PROMOTED_TOPIC, self._choices(recorded))

        # A failed promotion writes no rank and schedules no refresh.
        self.player.db.guild_exams = [
            _exam_record(
                "exam-failed",
                character_id=self.player.pk,
                target_rank=_PROMOTED_RANK,
            )
        ]
        with self.captureOnCommitCallbacks(execute=True) as failed_callbacks:
            settle_exam_outcome(
                self.player,
                SimpleNamespace(mode="guild_exam", exam_id="exam-failed"),
                None,
                "exam_failed",
            )
        self.assertEqual(list(failed_callbacks), [])
        self.assertNotIn(_PROMOTED_TOPIC, self._choices(recorded))

        self.player.db.guild_exams = [
            _exam_record(
                "exam-passed",
                character_id=self.player.pk,
                target_rank=_PROMOTED_RANK,
            )
        ]
        with self.captureOnCommitCallbacks(execute=True) as passed_callbacks:
            settle_exam_outcome(
                self.player,
                SimpleNamespace(mode="guild_exam", exam_id="exam-passed"),
                None,
                "exam_passed",
            )
        self.assertGreaterEqual(len(list(passed_callbacks)), 1)
        self.assertEqual(self.player.guild_rank, _PROMOTED_RANK)
        self.assertEqual(
            self._choices(recorded)[_PROMOTED_TOPIC]["availability"], TOPIC_OPEN
        )

    @covers_requirement(
        "authored-dialogue-availability::"
        "physical-condition-mutations-refresh-live-dialogue-after-commit"
    )
    def test_reward_claim_writer_refreshes_after_commit(self):
        delivery = None
        self._open_line_session()
        delivery = self._deliver_open_topic()
        _real, recorded = self._register_watcher(self.player)

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            write_reward_claims(self.player, ["t_lifecycle_quest:1"])
        self.assertGreaterEqual(len(list(callbacks)), 1)
        self.assertEqual(self.player.db.guild_reward_claims, ["t_lifecycle_quest:1"])
        # Ordinary eligibility refresh never rewrites the delivered scene.
        panel = self._dialogue_panel(recorded)
        self.assertEqual(panel["delivery"]["delivery_id"], delivery.delivery_id)

    # -- quest lifecycle -------------------------------------------------

    @covers_requirement(
        "authored-dialogue-availability::"
        "physical-condition-mutations-refresh-live-dialogue-after-commit"
    )
    def test_quest_lifecycle_states_refresh_without_a_completion_observer(self):
        self._open_line_session()
        _real, recorded = self._register_watcher(self.player)
        self.assertNotIn(_QUEST_TOPIC, self._choices(recorded))

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            with transaction.atomic():
                apply_quest_log_delta(
                    self.player, [_quest_record(QuestState.IN_PROGRESS)]
                )
        self.assertGreaterEqual(len(list(callbacks)), 1)
        self.assertEqual(
            self._choices(recorded)[_QUEST_TOPIC]["availability"], TOPIC_OPEN
        )

        with self.captureOnCommitCallbacks(execute=True):
            with transaction.atomic():
                apply_quest_log_delta(
                    self.player, [_quest_record(QuestState.FAILED)]
                )
        self.assertNotIn(_QUEST_TOPIC, self._choices(recorded))

        with self.captureOnCommitCallbacks(execute=True):
            with transaction.atomic():
                apply_quest_log_delta(self.player, [])
        self.assertNotIn(_QUEST_TOPIC, self._choices(recorded))

    @covers_requirement(
        "authored-dialogue-availability::"
        "physical-condition-mutations-refresh-live-dialogue-after-commit"
    )
    def test_outer_rollback_and_no_session_writes_publish_nothing(self):
        other = create_object(PlayerCharacter, key="合成無對話玩家")
        other.race = _RACE_KEY
        other.apply_race_baseline()
        other.db.inventory = []
        other.location = self.room
        self.assertIsNone(live_dialogue_session(other))

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            try:
                with transaction.atomic():
                    apply_quest_log_delta(
                        other, [_quest_record(QuestState.IN_PROGRESS)]
                    )
                    queue_dialogue_refresh(
                        affected_dialogue_owners(other), cause="quest_state"
                    )
                    raise RuntimeError("owning operation rolled back")
            except RuntimeError:
                pass
        self.assertEqual(list(callbacks), [])
        self.assertIsNone(live_dialogue_session(other))
        self.assertEqual(tuple(watchers.watchers_for(other)), ())

        # A committed no-session write is a silent success: it creates no
        # conversation, watcher or panel.
        with self.captureOnCommitCallbacks(execute=True):
            with transaction.atomic():
                apply_quest_log_delta(
                    other, [_quest_record(QuestState.IN_PROGRESS)]
                )
        self.assertIsNone(live_dialogue_session(other))
        self.assertEqual(tuple(watchers.watchers_for(other)), ())

    # -- affinity --------------------------------------------------------

    @covers_requirement(
        "authored-dialogue-availability::"
        "physical-condition-mutations-refresh-live-dialogue-after-commit"
    )
    def test_affinity_seed_and_change_refresh_the_other_connection(self):
        stage_floor = self.stages[2].floor
        # The formal selection itself grants the +1 talk affinity, so seed one
        # below the threshold minus that grant to keep the topic hidden.
        seed_affinity(self.host, self.player, stage_floor - 2)
        self.assertEqual(
            self.host.relations.affinity_for(self.player), stage_floor - 2
        )
        self._open_line_session()
        delivery = self._deliver_open_topic()
        self.assertEqual(
            self.host.relations.affinity_for(self.player), stage_floor - 1
        )
        _real, recorded = self._register_watcher(self.player)
        self.assertNotIn(_AFFINITY_TOPIC, self._choices(recorded))

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            outcome = apply_affinity_change(
                self.host, self.player, AffinitySource.GUILD, 1
            )
        self.assertTrue(outcome.applied)
        self.assertGreaterEqual(len(list(callbacks)), 1)
        self.assertEqual(
            self._choices(recorded)[_AFFINITY_TOPIC]["availability"], TOPIC_OPEN
        )
        self.assertEqual(
            self._dialogue_panel(recorded)["delivery"]["delivery_id"],
            delivery.delivery_id,
        )

    def test_affinity_seed_is_a_source_on_its_own(self):
        self._open_line_session()
        _real, recorded = self._register_watcher(self.player)
        self.assertNotIn(_AFFINITY_TOPIC, self._choices(recorded))
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            seed_affinity(self.host, self.player, self.stages[2].floor)
        self.assertGreaterEqual(len(list(callbacks)), 1)
        self.assertEqual(
            self._choices(recorded)[_AFFINITY_TOPIC]["availability"], TOPIC_OPEN
        )

    # -- companion presence and membership -------------------------------

    @covers_requirement(
        "authored-dialogue-availability::"
        "physical-condition-mutations-refresh-live-dialogue-after-commit"
    )
    def test_companion_leave_and_return_refresh_another_host_conversation(self):
        companion = self._companion()
        self._open_line_session()
        _real, recorded = self._register_watcher(self.player)
        self.assertEqual(
            self._choices(recorded)[_COMPANION_TOPIC]["availability"], TOPIC_OPEN
        )

        far_room = create_object(Room, key="合成遠處")
        with self.captureOnCommitCallbacks(execute=True):
            companion.move_to(far_room, quiet=True)
        self.assertNotIn(_COMPANION_TOPIC, self._choices(recorded))
        # The host stayed present and the conversation survived the move.
        self.assertIsNotNone(live_dialogue_session(self.player))

        with self.captureOnCommitCallbacks(execute=True):
            companion.move_to(self.room, quiet=True)
        self.assertEqual(
            self._choices(recorded)[_COMPANION_TOPIC]["availability"], TOPIC_OPEN
        )

        with self.captureOnCommitCallbacks(execute=True):
            leave_party(companion, self.player, reason="test")
        self.assertNotIn(_COMPANION_TOPIC, self._choices(recorded))
        with self.captureOnCommitCallbacks(execute=True):
            join_party(companion, self.player)
        self.assertEqual(
            self._choices(recorded)[_COMPANION_TOPIC]["availability"], TOPIC_OPEN
        )

    @covers_requirement(
        "authored-dialogue-availability::"
        "physical-condition-mutations-refresh-live-dialogue-after-commit"
    )
    def test_companion_deletion_refreshes_the_prior_owner_and_keeps_reading(self):
        companion = self._companion()
        self._open_line_session()
        delivery = self._deliver_open_topic()
        host_key = host_dialogue_binding(self.host)[0]
        record_completion(self.player, host_key=host_key, topic_id=_OPEN_TOPIC)
        self.assertEqual(completed_topic_ids(self.player, host_key), (_OPEN_TOPIC,))
        _real, recorded = self._register_watcher(self.player)
        self.assertEqual(
            self._choices(recorded)[_COMPANION_TOPIC]["availability"], TOPIC_OPEN
        )
        self.assertEqual(
            self._dialogue_panel(recorded)["delivery"]["delivery_id"],
            delivery.delivery_id,
        )

        companion_pk = int(companion.pk)
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            companion.delete()
        self.assertGreaterEqual(len(list(callbacks)), 1)
        self.assertNotIn(_COMPANION_TOPIC, self._choices(recorded))
        self.assertEqual(completed_topic_ids(self.player, host_key), (_OPEN_TOPIC,))
        self.assertFalse(ObjectDB.objects.filter(pk=companion_pk).exists())

    # -- world time ------------------------------------------------------

    @covers_requirement(
        "authored-dialogue-availability::"
        "physical-condition-mutations-refresh-live-dialogue-after-commit"
    )
    def test_daypart_boundary_reaches_an_idle_owner_outside_the_action(self):
        self._open_line_session()
        _real, recorded = self._register_watcher(self.player)
        self.assertNotIn(_TIME_TOPIC, self._choices(recorded))
        self.assertEqual(get_world_clock().tick, 0)

        # An advance inside the current midnight region schedules nothing.
        with patch("world.rules.clock._run_stages", return_value=[]), patch(
            "world.rules.dialogue_availability.queue_dialogue_refresh"
        ) as queued:
            get_world_clock().advance(600, AdvanceSource.SKIP, [])
        queued.assert_not_called()

        # The owner is NOT in the action's entity scope; the dawn boundary
        # still reaches its live conversation.
        with patch("world.rules.clock._run_stages", return_value=[]):
            with self.captureOnCommitCallbacks(execute=True):
                get_world_clock().advance(6 * 3600, AdvanceSource.SKIP, [])
        self.assertEqual(get_world_clock().calendar.hour, 6)
        self.assertEqual(
            self._choices(recorded)[_TIME_TOPIC]["availability"], TOPIC_OPEN
        )

    def test_session_owner_discovery_returns_only_live_sessions(self):
        self.assertEqual(session_bearing_dialogue_bodies(), ())
        self._open_line_session()
        self.assertEqual(session_bearing_dialogue_bodies(), (self.player,))
        self.assertEqual(session_bearing_dialogue_owners(), (self.player,))

        # A corrupt stored value is not a live session and is skipped.
        self.player.db.dialogue_session = "garbage"
        self.assertEqual(session_bearing_dialogue_bodies(), ())

    # -- control ---------------------------------------------------------

    @covers_requirement(
        "authored-dialogue-availability::"
        "physical-condition-mutations-refresh-live-dialogue-after-commit"
    )
    def test_possession_release_republishes_the_new_body_without_copying_content(self):
        # A real account-backed player is required for lawful possession.
        player = self.char1
        player.location = self.room
        player.race = _RACE_KEY
        player.apply_race_baseline()
        player.db.inventory = []
        companion = create_object(
            LLMNPC, key="合成附身同行者", location=self.room
        )
        companion.race = _RACE_KEY
        companion.apply_race_baseline()
        companion.db.inventory = []
        join_party(companion, player)
        self.companions.append(companion)

        open_or_refresh_dialogue(player, self.host, "原本身體的台詞。")
        self.assertEqual(session_bearing_dialogue_owners(), (player,))
        with patch(
            "web.webclient.presentation.dialogue_push.push_dialogue_reading"
        ) as pushed:
            with self.captureOnCommitCallbacks(execute=True):
                enter_possession(player, companion)
            self.addCleanup(release_possession, player, companion, "handback")
            # The old body's session retires with the control change.
            self.assertIsNone(live_dialogue_session(player))
            self.assertEqual(session_bearing_dialogue_owners(), ())
            pushed.assert_called_with(player)

            # The possessed body opens its own lawful conversation.
            open_or_refresh_dialogue(companion, self.host, "被附身者的台詞。")
            self.assertIsNotNone(live_dialogue_session(companion))
            self.assertEqual(session_bearing_dialogue_owners(), (player,))
            pushed.reset_mock()

            with self.captureOnCommitCallbacks(execute=True):
                release_possession(player, companion, "handback")
            self.assertIsNone(live_dialogue_session(companion))
            self.assertIsNone(live_dialogue_session(player))
            pushed.assert_called_with(player)
            # The new body republishes its own empty conversation; the
            # obsolete possessed scene was retired, never copied back.
            self.assertIsNone(player.db.dialogue_session)


class DialogueRefreshPhaseTests(RegistryIsolationMixin, _WatcherMixin, EvenniaTest):
    """A committed generated-phase transition retires obsolete playback."""

    def setUp(self) -> None:
        super().setUp()
        self.player = create_object(PlayerCharacter, key="合成階段訪客")
        self.room = create_object(AnchorRoom, key="合成階段門")
        self.room.db.anchor_key = _anchor_key()
        self.player.move_to(self.room, quiet=True)
        register_catalog_once()
        payload = package_payload()
        self.definition_key = compile_blueprint_core(payload["quest"]).definition.key
        # Every conversable role needs a complete phase dialogue.
        payload["dialogue"] = [
            package_dialogue("mother"),
            package_dialogue("daughter"),
        ]
        self.published = publish_scene_package(payload, owner="tester")
        activate_scene_encounter(
            self.player, self.published.package_id, "south_gate", room=self.room, tick=5
        )
        activate_scene_encounter(
            self.player, self.published.package_id, "market", room=self.room, tick=5
        )
        from world.quests import scene_store

        binding = scene_store.get_role_binding(self.published.package_id, "mother")
        self.mother = ObjectDB.objects.filter(id=binding.npc_id).first()
        self.host_key = host_dialogue_binding(self.mother)[0]
        watchers.clear_watchers()
        self.addCleanup(watchers.clear_watchers)
        self.registry = build_production_registry()

    def tearDown(self) -> None:
        clear_dialogue_session(self.player)
        super().tearDown()

    @covers_requirement(
        "authored-dialogue-availability::"
        "physical-refresh-includes-generated-scene-contexts"
    )
    def test_phase_transition_refreshes_live_playback_and_keeps_reading(self):
        record_completion(
            self.player, host_key=self.host_key, topic_id="phase.saved"
        )
        open_or_refresh_dialogue(self.player, self.mother, greeting_for(self.mother))
        self.assertEqual(
            live_dialogue_session(self.player).line, f"{LONG_PROSE}searching"
        )
        _real, recorded = self._register_watcher(self.player)
        panels_before = len(self._panels(recorded))

        with self.captureOnCommitCallbacks(execute=True):
            transition_story_dialogue(
                self.published.package_id,
                "mother",
                expected_revision=0,
                provenance={"closure": True},
                tick=8,
            )

        session = live_dialogue_session(self.player)
        self.assertIsNotNone(session)
        self.assertEqual(session.line, f"{LONG_PROSE}everyday")
        self.assertGreater(len(self._panels(recorded)), panels_before)
        # Saved logical reading is narrative-owned and survives retirement.
        self.assertEqual(
            completed_topic_ids(self.player, self.host_key), ("phase.saved",)
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
