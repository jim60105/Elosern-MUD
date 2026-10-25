"""Behavior test: authored-dialogue progression condition evaluation and hints.

Covers the ``authored-dialogue-progression-conditions`` slice against the shared
synthetic kit: guild rank qualification reads the owning player's canonical
registration and rank order, quest qualification distinguishes the six authored
lifecycle/claim states, host affinity reads the conversation host's relationship
toward the owner, hints render canonical labels without private numbers, and
real selection delivers a qualified scene, a hidden refusal or an effect-free
locked refusal without ever writing owner progression state.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.components import ScriptedDialogue
from typeclasses.npcs import LLMNPC, NPC
from typeclasses.rooms import Room
from world.lore.dialogue.conditions import (
    AffinityAtLeast,
    All,
    Any as AnyCondition,
    DialogueReferences,
    GuildRankAtLeast,
    QuestIs,
    RaceIs,
    validate_condition,
)
from world.lore.dialogue.shape import AuthoredDialogue, AuthoredTopic, SceneVariant
from world.lore.guild import GuildRank
from world.lore.scenes import Scene, Speech
from world.quests.catalog import register_catalog
from world.quests.runtime import (
    INVALIDATED_OBSOLETE_OUTCOME,
    OBSOLETE_OUTCOME_MESSAGE,
    QuestRecord,
    QuestState,
    to_storage,
)
from world.rules.affinity import seed_affinity
from world.rules.affinity_config import get_config
from world.rules.dialogue import (
    TopicNotFoundError,
    clear_dialogue_session,
    live_dialogue_session,
    select_authored_topic,
)
from world.rules.dialogue_conditions import (
    DialogueConditionError,
    condition_hint,
    evaluate_condition,
)
from world.rules.dialogue_references import (
    permitted_quest_definition,
    static_dialogue_references,
)
from world.rules.guild import REGISTRATION_TRAIT_KEYS
from world.rules.party import join_party
from world.rules.possession import enter_possession, release_possession
from world.tests.synthetic_data import SYNTH_RACES, synthetic_registries
from world.tests.synthetic_data.data_presets_quests import (
    SYNTH_GUILD_BRANCH_KEY,
    SYNTH_GUILD_ISSUER_KEY,
    SYNTH_QUESTS,
)

_RACE_KEY = next(iter(SYNTH_RACES))
_OTHER_RACE_KEY = next(key for key in SYNTH_RACES if key != _RACE_KEY)
_QUEST_KEY = "t_ember_cull"
_OTHER_QUEST_KEY = "t_tarn_messenger"

#: Ranks whose alphabetic order disagrees with their canonical ``order``, so a
#: string comparison would answer the opposite way for both controls.
_RANK_BASE = "t_zeta"
_RANK_HIGH = "t_alpha"
_RANKS = {
    _RANK_BASE: GuildRank(
        _RANK_BASE, 1, 50, 400, "Synthetic base-rank tasks.", "t_synth_bronze_badge"
    ),
    _RANK_HIGH: GuildRank(
        _RANK_HIGH, 2, 400, 4_000, "Synthetic high-rank tasks.", "t_synth_silver_badge"
    ),
}

_TABLE_KEY = "t_progression_keeper"
_RANK_TOPIC = f"{_TABLE_KEY}.rank"
_QUEST_TOPIC = f"{_TABLE_KEY}.quest"
_AFFINITY_TOPIC = f"{_TABLE_KEY}.affinity"
_MIXED_TOPIC = f"{_TABLE_KEY}.mixed"
_ANY_TOPIC = f"{_TABLE_KEY}.either"
_LOCKED_TOPIC = f"{_TABLE_KEY}.locked"
_STALE_TOPIC = f"{_TABLE_KEY}.stale"


def _scene(scene_id: str, host_text: str) -> Scene:
    return Scene(
        scene_id=scene_id,
        revision="r1",
        lines=(
            Speech(speaker="actor", text="合成進度問句。"),
            Speech(speaker="host", text=host_text),
        ),
    )


def _authored_dialogue(affinity_stage: str) -> AuthoredDialogue:
    return AuthoredDialogue(
        greeting="合成進度店主抬眼：「有事就問。」",
        topics=(
            AuthoredTopic(
                topic_id=_RANK_TOPIC,
                keyword="合成階級",
                label="合成階級",
                fallback=_scene("t_progression_rank_fallback", "合成階級通用答覆。"),
                requires=GuildRankAtLeast(rank_key=_RANK_HIGH),
                unavailable="hidden",
            ),
            AuthoredTopic(
                topic_id=_QUEST_TOPIC,
                keyword="合成委託",
                label="合成委託",
                fallback=_scene("t_progression_quest_fallback", "合成委託通用答覆。"),
                requires=QuestIs(definition_key=_QUEST_KEY, state="completed"),
                unavailable="hidden",
            ),
            AuthoredTopic(
                topic_id=_AFFINITY_TOPIC,
                keyword="合成情誼",
                label="合成情誼",
                fallback=_scene("t_progression_affinity_fallback", "合成情誼通用答覆。"),
                requires=AffinityAtLeast(stage_key=affinity_stage),
                unavailable="hidden",
            ),
            AuthoredTopic(
                topic_id=_MIXED_TOPIC,
                keyword="合成雙證",
                label="合成雙證",
                fallback=_scene("t_progression_mixed_fallback", "合成雙證通用答覆。"),
                requires=All(
                    (
                        RaceIs(race_key=_RACE_KEY),
                        GuildRankAtLeast(rank_key=_RANK_HIGH),
                    )
                ),
                unavailable="hidden",
            ),
            AuthoredTopic(
                topic_id=_ANY_TOPIC,
                keyword="合成其一",
                label="合成其一",
                fallback=_scene("t_progression_any_fallback", "合成其一通用答覆。"),
                requires=AnyCondition(
                    (
                        GuildRankAtLeast(rank_key=_RANK_HIGH),
                        RaceIs(race_key=_OTHER_RACE_KEY),
                    )
                ),
                unavailable="hidden",
            ),
            AuthoredTopic(
                topic_id=_LOCKED_TOPIC,
                keyword="合成保留",
                label="合成保留",
                fallback=_scene("t_progression_locked_fallback", "合成保留答覆。"),
                requires=QuestIs(definition_key=_QUEST_KEY, state="completed"),
                unavailable="locked",
                refusal=_scene("t_progression_locked_refusal", "合成婉拒答覆。"),
            ),
            AuthoredTopic(
                topic_id=_STALE_TOPIC,
                keyword="合成過期",
                label="合成過期",
                fallback=_scene("t_progression_stale_fallback", "合成過期答覆。"),
                variants=(
                    SceneVariant(
                        variant_id="completed",
                        priority=10,
                        when=QuestIs(definition_key=_QUEST_KEY, state="completed"),
                        scene=_scene("t_progression_stale_variant", "合成完成答覆。"),
                    ),
                ),
            ),
        ),
    )


def _record(
    definition_key: str,
    state: QuestState,
    quest_id: str,
    *,
    stage_progress: int = 0,
) -> dict:
    """Build one strict storage dict for the owner's quest log."""
    return to_storage(
        QuestRecord(
            quest_id=quest_id,
            definition_key=definition_key,
            issuer_key=SYNTH_GUILD_ISSUER_KEY,
            state=state,
            stage_index=0,
            stage_progress=stage_progress,
            deadline_tick=None,
            accepted_tick=0,
            stage_room_id=None,
            objective_target_ids=(),
            protected_entity_ids=(),
            failure_reason=(
                "synthetic deadline" if state is QuestState.FAILED else None
            ),
            invalidated_reason=(
                {
                    "code": INVALIDATED_OBSOLETE_OUTCOME,
                    "message": OBSOLETE_OUTCOME_MESSAGE,
                }
                if state is QuestState.INVALIDATED
                else None
            ),
        )
    )


class DialogueProgressionConditionTests(EvenniaTest):
    """Evaluator, hint, reference and selection behavior on synthetic data."""

    def setUp(self) -> None:
        super().setUp()
        # The affinity rulebook's cap breaks resolve their quest keys through the
        # registered definitions, exactly as the runtime acceptance does.
        register_catalog()
        self.stages = get_config().stages
        self.scope = synthetic_registries(
            "races",
            "items",
            "skills",
            "guild_ranks",
            "quest_definitions",
            "dialogue",
            extra={
                "guild_ranks": _RANKS,
                "dialogue": {_TABLE_KEY: _authored_dialogue(self.stages[2].id)},
            },
        )
        self.scope.__enter__()
        self.addCleanup(self.scope.__exit__, None, None, None)

        self.room1 = create_object(Room, key="合成進度廳")
        for character in (self.char1, self.char2):
            character.location = self.room1
            character.race = _RACE_KEY
            character.apply_race_baseline()
            character.db.inventory = []

        self.host = create_object(NPC, key="合成進度店主", location=self.room1)
        self.host.components.add(
            ScriptedDialogue.create(self.host, dialogue_key=_TABLE_KEY)
        )
        self.companion: LLMNPC | None = None

    def tearDown(self) -> None:
        clear_dialogue_session(self.char1)
        if self.companion is not None:
            clear_dialogue_session(self.companion)
            if self.char1.db.possession:
                release_possession(self.char1, npc=self.companion, reason="handback")
        super().tearDown()

    # -- helpers ---------------------------------------------------------

    def _context(self, *, actor=None, owner=None, host=None) -> SimpleNamespace:
        return SimpleNamespace(
            actor=self.char1 if actor is None else actor,
            owner=self.char1 if owner is None else owner,
            host=self.host if host is None else host,
            source_identity=None,
        )

    def _register(self, character, rank_key: str) -> None:
        character.db.guild_registration = {
            "branch_key": SYNTH_GUILD_BRANCH_KEY,
            "registered_tick": 0,
            "displayed_stats": {key: 1 for key in REGISTRATION_TRAIT_KEYS},
        }
        character.attributes.add("guild_rank", rank_key)

    def _select(self, actor, topic_id: str, *, selection_id="sel-1", expected=None):
        return select_authored_topic(
            actor,
            self.host,
            topic_id,
            selection_id=selection_id,
            expected_context_id=expected,
        )

    def _progression_state(self) -> str:
        return json.dumps(
            {
                "registration": self.char1.db.guild_registration,
                "rank": self.char1.attributes.get("guild_rank"),
                "rank_materialized": self.char1.attributes.has("guild_rank"),
                "quest_log": self.char1.db.quest_log,
                "claims": self.char1.db.guild_reward_claims,
                "relations": self.host.db.relations_data,
                "session": self.char1.db.dialogue_session,
            },
            sort_keys=True,
            default=str,
        )

    # -- guild rank ------------------------------------------------------

    @covers_requirement(
        "authored-dialogue-conditions::physical-conditions-use-the-acting-body-and-canonical-readers"
    )
    def test_guild_rank_reads_the_owner_and_the_canonical_order(self):
        condition = GuildRankAtLeast(rank_key=_RANK_HIGH)
        self._register(self.char1, _RANK_BASE)
        self._register(self.char2, _RANK_HIGH)
        # The acting body holds the higher rank; the owning player does not.
        self.assertFalse(
            evaluate_condition(condition, self._context(actor=self.char2))
        )
        # Alphabetic comparison would accept "t_zeta" over "t_alpha"; the
        # canonical order rejects it.
        self.assertFalse(evaluate_condition(condition, self._context()))

        self.char1.attributes.add("guild_rank", _RANK_HIGH)
        self.assertTrue(evaluate_condition(condition, self._context()))
        # Alphabetic comparison would reject "t_alpha" under "t_zeta".
        self.assertTrue(
            evaluate_condition(
                GuildRankAtLeast(rank_key=_RANK_BASE), self._context()
            )
        )

    @covers_requirement(
        "authored-dialogue-conditions::physical-conditions-use-the-acting-body-and-canonical-readers"
    )
    def test_missing_rank_or_registration_fails_closed(self):
        condition = GuildRankAtLeast(rank_key=_RANK_HIGH)
        self.char1.attributes.add("guild_rank", _RANK_HIGH)
        with patch("world.rules.dialogue_conditions.log_warn") as log_warn:
            # Registration is missing even though the rank is present.
            self.assertFalse(evaluate_condition(condition, self._context()))
        log_warn.assert_not_called()

        # A registered owner whose rank attribute was never stored stays
        # unqualified, and the read never materializes the attribute.
        self._register(self.char2, _RANK_HIGH)
        self.char2.attributes.remove("guild_rank")
        authority = SimpleNamespace(
            actor=self.char2, owner=self.char2, host=self.host, source_identity=None
        )
        self.assertFalse(evaluate_condition(condition, authority))
        self.assertFalse(self.char2.attributes.has("guild_rank"))

    @covers_requirement(
        "authored-dialogue-conditions::physical-conditions-use-the-acting-body-and-canonical-readers"
    )
    def test_corrupt_registration_and_unknown_rank_emit_one_integrity_event(self):
        condition = GuildRankAtLeast(rank_key=_RANK_HIGH)
        self.char1.db.guild_registration = {"garbage": True}
        with patch("world.rules.dialogue_conditions.log_warn") as log_warn:
            self.assertFalse(evaluate_condition(condition, self._context()))
        self.assertEqual(log_warn.call_count, 1)
        self.assertEqual(
            log_warn.call_args.kwargs["context"]["reason"],
            "owner_guild_rank_unresolved",
        )

        self.char1.db.guild_registration = {
            "branch_key": SYNTH_GUILD_BRANCH_KEY,
            "registered_tick": 0,
            "displayed_stats": {key: 1 for key in REGISTRATION_TRAIT_KEYS},
        }
        self.char1.attributes.add("guild_rank", "t_unknown_rank")
        with patch("world.rules.dialogue_conditions.log_warn") as log_warn:
            self.assertFalse(evaluate_condition(condition, self._context()))
        self.assertEqual(
            log_warn.call_args.kwargs["context"]["reason"],
            "owner_guild_rank_unresolved",
        )

    # -- quest lifecycle -------------------------------------------------

    @covers_requirement(
        "authored-dialogue-conditions::physical-conditions-use-the-acting-body-and-canonical-readers"
    )
    def test_quest_states_distinguish_lifecycle_and_claim_receipts(self):
        def state_condition(state: str) -> QuestIs:
            return QuestIs(definition_key=_QUEST_KEY, state=state)

        # Absence is the only not-accepted truth.
        self.assertTrue(evaluate_condition(state_condition("not_accepted"), self._context()))
        self.assertFalse(evaluate_condition(state_condition("in_progress"), self._context()))

        self.char1.db.quest_log = [
            _record(_QUEST_KEY, QuestState.IN_PROGRESS, "q-live")
        ]
        self.assertTrue(evaluate_condition(state_condition("in_progress"), self._context()))
        self.assertFalse(evaluate_condition(state_condition("not_accepted"), self._context()))
        self.assertFalse(evaluate_condition(state_condition("completed"), self._context()))

        self.char1.db.quest_log = [
            _record(_QUEST_KEY, QuestState.COMPLETED, "q-done")
        ]
        self.assertTrue(evaluate_condition(state_condition("completed"), self._context()))
        self.assertFalse(
            evaluate_condition(state_condition("reward_claimed"), self._context())
        )
        # Reading acknowledgement never grants the claim.
        self.assertEqual(list(self.char1.db.guild_reward_claims or []), [])

        self.char1.db.guild_reward_claims = ["q-done"]
        self.assertTrue(evaluate_condition(state_condition("reward_claimed"), self._context()))
        self.assertTrue(evaluate_condition(state_condition("completed"), self._context()))

        self.char1.db.quest_log = [
            _record(_QUEST_KEY, QuestState.FAILED, "q-failed")
        ]
        self.assertTrue(evaluate_condition(state_condition("failed"), self._context()))
        self.assertFalse(evaluate_condition(state_condition("completed"), self._context()))

        self.char1.db.quest_log = [
            _record(_QUEST_KEY, QuestState.INVALIDATED, "q-invalid")
        ]
        self.assertTrue(
            evaluate_condition(state_condition("invalidated"), self._context())
        )
        self.assertFalse(evaluate_condition(state_condition("failed"), self._context()))

    @covers_requirement(
        "authored-dialogue-conditions::physical-conditions-use-the-acting-body-and-canonical-readers"
    )
    def test_repeatable_records_match_existentially_and_ignore_unrelated_claims(self):
        self.char1.db.quest_log = [
            _record(_QUEST_KEY, QuestState.FAILED, "q-repeat-failed"),
            _record(_QUEST_KEY, QuestState.IN_PROGRESS, "q-repeat-live"),
            _record(_OTHER_QUEST_KEY, QuestState.COMPLETED, "q-other-done"),
        ]
        self.char1.db.guild_reward_claims = ["q-other-done"]

        def state_condition(state: str) -> QuestIs:
            return QuestIs(definition_key=_QUEST_KEY, state=state)

        self.assertTrue(evaluate_condition(state_condition("in_progress"), self._context()))
        self.assertTrue(evaluate_condition(state_condition("failed"), self._context()))
        self.assertFalse(evaluate_condition(state_condition("completed"), self._context()))
        self.assertFalse(
            evaluate_condition(state_condition("reward_claimed"), self._context())
        )
        self.assertFalse(evaluate_condition(state_condition("not_accepted"), self._context()))

    @covers_requirement(
        "authored-dialogue-conditions::physical-conditions-use-the-acting-body-and-canonical-readers"
    )
    def test_malformed_quest_state_fails_closed_and_dominates_an_any_sibling(self):
        disqualifying = AnyCondition(
            (
                QuestIs(definition_key=_QUEST_KEY, state="not_accepted"),
                RaceIs(race_key=_RACE_KEY),
            )
        )
        for corrupt in (0, {"q": 1}, 7):
            with self.subTest(corrupt=corrupt):
                self.char1.db.quest_log = corrupt
                with patch("world.rules.dialogue_conditions.log_warn") as log_warn:
                    self.assertFalse(
                        evaluate_condition(
                            QuestIs(definition_key=_QUEST_KEY, state="not_accepted"),
                            self._context(),
                        )
                    )
                self.assertEqual(
                    log_warn.call_args.kwargs["context"]["reason"],
                    "owner_quest_log_malformed",
                )
                # The matching race branch must not rescue the corrupt tree.
                with patch("world.rules.dialogue_conditions.log_warn"):
                    self.assertFalse(evaluate_condition(disqualifying, self._context()))

    @covers_requirement(
        "authored-dialogue-conditions::physical-conditions-use-the-acting-body-and-canonical-readers"
    )
    def test_corrupt_reward_claims_fail_closed(self):
        self.char1.db.quest_log = [
            _record(_QUEST_KEY, QuestState.COMPLETED, "q-done")
        ]
        for corrupt in ("q-done", {"q-done": 1}, 3):
            with self.subTest(corrupt=corrupt):
                self.char1.db.guild_reward_claims = corrupt
                with patch("world.rules.dialogue_conditions.log_warn") as log_warn:
                    self.assertFalse(
                        evaluate_condition(
                            QuestIs(
                                definition_key=_QUEST_KEY, state="reward_claimed"
                            ),
                            self._context(),
                        )
                    )
                self.assertEqual(
                    log_warn.call_args.kwargs["context"]["reason"],
                    "owner_reward_claims_malformed",
                )

    @covers_requirement(
        "authored-dialogue-conditions::physical-conditions-use-the-acting-body-and-canonical-readers"
    )
    def test_unpermitted_quest_definition_fails_closed(self):
        with patch("world.rules.dialogue_conditions.log_warn") as log_warn:
            self.assertFalse(
                evaluate_condition(
                    QuestIs(definition_key="t_not_a_quest", state="not_accepted"),
                    self._context(),
                )
            )
        self.assertEqual(
            log_warn.call_args.kwargs["context"]["reason"],
            "quest_definition_unpermitted",
        )

    # -- host affinity ---------------------------------------------------

    @covers_requirement(
        "authored-dialogue-conditions::physical-conditions-use-the-acting-body-and-canonical-readers"
    )
    def test_affinity_reads_the_host_relationship_toward_the_owner_only(self):
        stage = self.stages[2]
        condition = AffinityAtLeast(stage_key=stage.id)
        seed_affinity(self.host, self.char1, stage.floor)
        self.assertTrue(evaluate_condition(condition, self._context()))

        # The actor holds a high relation while the owning player has none.
        self.host.db.relations_data = {}
        seed_affinity(self.host, self.char2, self.stages[-2].floor)
        self.assertFalse(
            evaluate_condition(condition, self._context(actor=self.char2))
        )

        # One point below the canonical stage floor fails; the boundary itself
        # passes.
        self.host.db.relations_data = {}
        seed_affinity(self.host, self.char1, stage.floor - 1)
        self.assertFalse(evaluate_condition(condition, self._context()))

    @covers_requirement(
        "authored-dialogue-conditions::physical-conditions-use-the-acting-body-and-canonical-readers"
    )
    def test_unknown_stage_or_missing_relationship_fails_closed(self):
        with patch("world.rules.dialogue_conditions.log_warn") as log_warn:
            self.assertFalse(
                evaluate_condition(
                    AffinityAtLeast(stage_key="t_unknown_stage"), self._context()
                )
            )
        self.assertEqual(
            log_warn.call_args.kwargs["context"]["reason"],
            "owner_affinity_unresolved",
        )

        hostless = SimpleNamespace(
            actor=self.char1, owner=self.char1, host=None, source_identity=None
        )
        with patch("world.rules.dialogue_conditions.log_warn"):
            self.assertFalse(
                evaluate_condition(
                    AffinityAtLeast(stage_key=self.stages[0].id), hostless
                )
            )

    # -- hints -----------------------------------------------------------

    @covers_requirement(
        "authored-dialogue-conditions::combination-hints-and-complete-scene-variants-share-declarations"
    )
    def test_hints_use_canonical_labels_without_private_values(self):
        rank_hint = condition_hint(
            GuildRankAtLeast(rank_key=_RANK_HIGH), self._context()
        )
        self.assertEqual(rank_hint, f"需要公會階級至少為{_RANKS[_RANK_HIGH].display_name_zh}")

        completed_hint = condition_hint(
            QuestIs(definition_key=_QUEST_KEY, state="completed"), self._context()
        )
        self.assertIn(SYNTH_QUESTS[_QUEST_KEY].display_name, completed_hint)
        self.assertIn("已完成", completed_hint)
        absent_hint = condition_hint(
            QuestIs(definition_key=_QUEST_KEY, state="not_accepted"), self._context()
        )
        self.assertIn("尚未接取", absent_hint)

        stage = self.stages[2]
        seed_affinity(self.host, self.char1, 50)
        affinity_hint = condition_hint(
            AffinityAtLeast(stage_key=stage.id), self._context()
        )
        self.assertIn(stage.name, affinity_hint)
        self.assertNotIn("50", affinity_hint)
        self.assertNotIn(str(stage.floor), affinity_hint)

    @covers_requirement(
        "authored-dialogue-conditions::combination-hints-and-complete-scene-variants-share-declarations"
    )
    def test_hint_for_an_unpermitted_label_raises(self):
        with self.assertRaises(DialogueConditionError):
            condition_hint(AffinityAtLeast(stage_key="t_unknown_stage"), self._context())
        with self.assertRaises(DialogueConditionError):
            condition_hint(
                GuildRankAtLeast(rank_key="t_unknown_rank"), self._context()
            )
        with self.assertRaises(DialogueConditionError):
            condition_hint(
                QuestIs(definition_key="t_not_a_quest", state="completed"),
                self._context(),
            )

    # -- read-only discipline --------------------------------------------

    @covers_requirement(
        "authored-dialogue-conditions::physical-conditions-use-the-acting-body-and-canonical-readers"
    )
    def test_evaluation_and_hints_never_write_owner_or_host_state(self):
        self._register(self.char1, _RANK_HIGH)
        self.char1.db.quest_log = [
            _record(_QUEST_KEY, QuestState.COMPLETED, "q-done")
        ]
        self.char1.db.guild_reward_claims = ["q-done"]
        seed_affinity(self.host, self.char1, self.stages[2].floor)
        before = self._progression_state()

        context = self._context()
        conditions = (
            GuildRankAtLeast(rank_key=_RANK_HIGH),
            QuestIs(definition_key=_QUEST_KEY, state="in_progress"),
            QuestIs(definition_key=_QUEST_KEY, state="reward_claimed"),
            AffinityAtLeast(stage_key=self.stages[2].id),
        )
        for condition in conditions:
            evaluate_condition(condition, context)
            condition_hint(condition, context)

        self.assertEqual(self._progression_state(), before)

    # -- reference catalog and publication -------------------------------

    @covers_requirement(
        "authored-dialogue-conditions::generated-physical-references-retain-canonical-and-package-scope"
    )
    def test_reference_catalog_exposes_the_progression_families(self):
        references = static_dialogue_references()
        self.assertLessEqual(frozenset(_RANKS), references.keys_for("guild_rank"))
        for key, row in _RANKS.items():
            self.assertEqual(references.label("guild_rank", key), row.display_name_zh)
        self.assertIn(_QUEST_KEY, references.keys_for("quest"))
        self.assertEqual(
            references.label("quest", _QUEST_KEY),
            SYNTH_QUESTS[_QUEST_KEY].display_name,
        )
        self.assertTrue(permitted_quest_definition(_QUEST_KEY))
        self.assertFalse(permitted_quest_definition("t_not_a_quest"))
        self.assertEqual(
            references.keys_for("affinity_stage"),
            frozenset(stage.id for stage in self.stages),
        )
        for stage in self.stages:
            self.assertEqual(references.label("affinity_stage", stage.id), stage.name)

    @covers_requirement(
        "authored-dialogue-conditions::generated-physical-references-retain-canonical-and-package-scope"
    )
    def test_publication_rejects_unknown_and_foreign_progression_keys(self):
        references = static_dialogue_references()
        validate_condition(GuildRankAtLeast(rank_key=_RANK_HIGH), references)
        validate_condition(
            QuestIs(definition_key=_QUEST_KEY, state="reward_claimed"), references
        )
        validate_condition(
            AffinityAtLeast(stage_key=self.stages[2].id), references
        )

        for invalid in (
            GuildRankAtLeast(rank_key="t_unknown_rank"),
            QuestIs(definition_key="t_not_a_quest", state="completed"),
            QuestIs(definition_key=_QUEST_KEY, state="active"),
            AffinityAtLeast(stage_key="t_unknown_stage"),
        ):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    validate_condition(invalid, references)

        # A package definition is permitted only through its own package scope.
        packaged = QuestIs(definition_key="t_package_quest", state="completed")
        with self.assertRaises(ValueError):
            validate_condition(packaged, references)
        validate_condition(
            packaged, references, package_quests=frozenset({"t_package_quest"})
        )
        # An empty catalog family fails closed for every progression family.
        empty = DialogueReferences.empty()
        for invalid in (
            GuildRankAtLeast(rank_key=_RANK_HIGH),
            QuestIs(definition_key=_QUEST_KEY, state="completed"),
            AffinityAtLeast(stage_key=self.stages[2].id),
        ):
            with self.subTest(family=type(invalid).__name__):
                with self.assertRaises(ValueError):
                    validate_condition(invalid, empty)

    # -- real selection --------------------------------------------------

    @covers_requirement(
        "authored-dialogue-conditions::combination-hints-and-complete-scene-variants-share-declarations"
    )
    def test_rank_qualified_topic_opens_only_for_the_qualifying_owner(self):
        self._register(self.char1, _RANK_HIGH)
        delivery = self._select(self.char1, _RANK_TOPIC)
        self.assertEqual(delivery.kind, "formal")
        self.assertEqual(delivery.scene_id, "t_progression_rank_fallback")

        self._register(self.char2, _RANK_BASE)
        with self.assertRaises(TopicNotFoundError):
            self._select(self.char2, _RANK_TOPIC, selection_id="sel-2")
        self.assertIsNone(self.char2.db.dialogue_session)

    @covers_requirement(
        "authored-dialogue-conditions::physical-conditions-use-the-acting-body-and-canonical-readers"
    )
    def test_possessed_actor_rank_cannot_substitute_for_the_owner(self):
        self.companion = create_object(
            LLMNPC, key="合成繼承者", location=self.room1
        )
        self.companion.race = _RACE_KEY
        self.companion.apply_race_baseline()
        self.companion.db.inventory = []
        self._register(self.companion, _RANK_HIGH)
        join_party(self.companion, self.char1)
        enter_possession(self.char1, self.companion)

        # The possessed body is registered at the qualifying rank while the
        # commanding owner is unregistered: the qualification must fail.
        with self.assertRaises(TopicNotFoundError):
            self._select(self.companion, _RANK_TOPIC, selection_id="sel-possessed")
        self.assertIsNone(self.companion.db.dialogue_session)
        self.assertFalse(self.host.relations.has_record(self.char1))

        self._register(self.char1, _RANK_HIGH)
        delivery = self._select(
            self.companion, _RANK_TOPIC, selection_id="sel-possessed-2"
        )
        self.assertEqual(delivery.kind, "formal")
        self.assertEqual(delivery.owner_id, int(self.char1.pk))

    @covers_requirement(
        "authored-dialogue-conditions::combination-hints-and-complete-scene-variants-share-declarations"
    )
    def test_mixed_physical_and_progression_scenes_select_on_owner_state(self):
        self._register(self.char1, _RANK_HIGH)
        delivery = self._select(self.char1, _MIXED_TOPIC)
        self.assertEqual(delivery.kind, "formal")
        self.assertEqual(delivery.scene_id, "t_progression_mixed_fallback")

        self.char1.db.guild_registration = None
        with self.assertRaises(TopicNotFoundError):
            self._select(
                self.char1,
                _MIXED_TOPIC,
                selection_id="sel-mixed-2",
                expected=live_dialogue_session(self.char1).context_id,
            )

        # The disjunction still qualifies through the physical (race) branch.
        self.char1.race = _OTHER_RACE_KEY
        self.char1.apply_race_baseline()
        delivery = self._select(
            self.char1,
            _ANY_TOPIC,
            selection_id="sel-any",
            expected=live_dialogue_session(self.char1).context_id,
        )
        self.assertEqual(delivery.kind, "formal")

    @covers_requirement(
        "authored-dialogue-conditions::combination-hints-and-complete-scene-variants-share-declarations"
    )
    def test_locked_quest_refusal_applies_no_affinity_or_quest_effect(self):
        self.char1.db.quest_log = [
            _record(_QUEST_KEY, QuestState.IN_PROGRESS, "q-live")
        ]
        affinity_before = self.host.relations.affinity_for(self.char1)
        log_before = json.dumps(
            self.char1.db.quest_log, sort_keys=True, default=str
        )
        delivery = self._select(self.char1, _LOCKED_TOPIC)
        self.assertEqual(delivery.kind, "refusal")
        self.assertEqual(delivery.scene_id, "t_progression_locked_refusal")
        self.assertEqual(self.host.relations.affinity_for(self.char1), affinity_before)
        self.assertEqual(
            json.dumps(self.char1.db.quest_log, sort_keys=True, default=str),
            log_before,
        )
        self.assertEqual(list(self.char1.db.guild_reward_claims or []), [])

        # Once the quest is complete the same topic becomes formal and only then
        # grants the ordinary talk affinity.
        self.char1.db.quest_log = [
            _record(_QUEST_KEY, QuestState.COMPLETED, "q-live")
        ]
        session = live_dialogue_session(self.char1)
        formal = self._select(
            self.char1,
            _LOCKED_TOPIC,
            selection_id="sel-locked-formal",
            expected=session.context_id,
        )
        self.assertEqual(formal.kind, "formal")
        self.assertEqual(self.host.relations.affinity_for(self.char1), affinity_before + 1)

    @covers_requirement(
        "authored-dialogue-conditions::combination-hints-and-complete-scene-variants-share-declarations"
    )
    def test_stale_changed_state_refuses_a_fresh_selection_without_effects(self):
        self.char1.db.quest_log = [
            _record(_QUEST_KEY, QuestState.COMPLETED, "q-done")
        ]
        delivery = self._select(self.char1, _QUEST_TOPIC, selection_id="sel-stale")
        self.assertEqual(delivery.kind, "formal")
        self.assertEqual(delivery.scene_id, "t_progression_quest_fallback")
        session = live_dialogue_session(self.char1)
        affinity_after = self.host.relations.affinity_for(self.char1)

        # A committed state change falsifies the requirement afterwards.
        self.char1.db.quest_log = [
            _record(_QUEST_KEY, QuestState.FAILED, "q-done")
        ]
        log_before = json.dumps(
            self.char1.db.quest_log, sort_keys=True, default=str
        )
        claims_before = json.dumps(
            self.char1.db.guild_reward_claims, sort_keys=True, default=str
        )

        # The committed replay keeps its delivered scene and grants nothing new.
        replay = self._select(
            self.char1,
            _QUEST_TOPIC,
            selection_id="sel-stale",
            expected=session.context_id,
        )
        self.assertEqual(replay.delivery_id, delivery.delivery_id)
        self.assertEqual(replay.scene_id, "t_progression_quest_fallback")
        self.assertEqual(self.host.relations.affinity_for(self.char1), affinity_after)
        self.assertEqual(
            json.dumps(self.char1.db.quest_log, sort_keys=True, default=str),
            log_before,
        )

        # A fresh selection re-evaluates current state and refuses.
        with self.assertRaises(TopicNotFoundError):
            self._select(
                self.char1,
                _QUEST_TOPIC,
                selection_id="sel-stale-fresh",
                expected=session.context_id,
            )
        self.assertEqual(self.host.relations.affinity_for(self.char1), affinity_after)
        self.assertEqual(
            json.dumps(self.char1.db.quest_log, sort_keys=True, default=str),
            log_before,
        )
        self.assertEqual(
            json.dumps(
                self.char1.db.guild_reward_claims, sort_keys=True, default=str
            ),
            claims_before,
        )
