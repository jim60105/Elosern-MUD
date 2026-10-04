"""Synthetic behavior tests for private drafts and confirmed request versions.

Everything here is deterministic and offline: synthetic actors, synthetic
provenance rows, no model or image service. Delta-only requirement ids land at
archive sync, so substantive tests are annotated against the existing canonical
main ids they establish.
"""

from __future__ import annotations

import json
import types
from unittest.mock import patch

from django.test import override_settings
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement

from world.ai.profiles import LAYER_NAMES, default_profiles
from world.narrative.authoring import (
    REASON_MESSAGES,
    AuthoringAccessError,
    AuthoringError,
    DirectionValidationError,
    collaborator_creative_brief,
    confirm_draft,
    draft_is_confirmed,
    get_draft,
    get_request,
    latest_confirmed_request,
    list_drafts,
    list_requests,
    save_draft,
    submission_key_for,
    validate_direction,
)
from world.narrative.events import record_narrative_event
from world.narrative.memory import get_owner_memories
from world.narrative.models import (
    AuthoringDraft,
    CreativeRequest,
    MemoryRecord,
    NarrativeEvent,
    ProjectionProgress,
)
from world.narrative.recall import fast_recall
from world.narrative.threads import create_thread, resolve_thread
from world.rules.clock import get_world_clock


def new_story_direction(**overrides):
    """A complete, valid new-story direction; overrides replace whole fields."""
    direction = {
        "summary": "合成夢境方向：在無名港尋找失落的鐘聲。",
        "themes": ["合成主題"],
        "atmosphere": ["合成氛圍"],
        "participants": [],
        "emphasis": ["合成重點"],
        "exclusions": ["合成排除"],
        "kind": "new_story",
        "thread_id": None,
        "effects": [],
        "revisions": [],
    }
    direction.update(overrides)
    return direction


class DreamAuthoringTestCase(EvenniaTest):
    """Shared synthetic actors, a fixed clock, and helper builders."""

    def setUp(self):
        super().setUp()
        self.owner = create_object(
            "typeclasses.characters.PlayerCharacter",
            key="Synthetic authoring owner",
            location=self.room1,
        )
        self.other = create_object(
            "typeclasses.characters.PlayerCharacter", key="Synthetic other owner"
        )
        self.npc = create_object("typeclasses.npcs.NPC", key="Synthetic authoring npc")
        self.clock = get_world_clock()
        self.clock._persist(100)
        self.clock.tick = 100

    @property
    def owner_id(self) -> str:
        return str(self.owner.pk)

    @property
    def other_id(self) -> str:
        return str(self.other.pk)

    def owner_thread(self, thread_id: str, **overrides):
        kwargs = dict(
            thread_id=thread_id,
            origin=f"event:synthetic:authoring:{thread_id}:origin",
            participants=[self.owner_id],
            tick=100,
        )
        kwargs.update(overrides)
        return create_thread(**kwargs)

    def committed_event(self, ref: str, tick: int = 100):
        return record_narrative_event(
            source_id=ref,
            event_type="encounter_protection",
            content={"encounter_outcome": "victory"},
            participants=[self.owner_id],
            tick=tick,
            visibility="public",
        )[0]

    def character_attribute_snapshot(self):
        return sorted(
            (attribute.db_key, repr(attribute.value))
            for attribute in self.owner.attributes.all()
        )


class DreamAuthoringPrivacyTests(DreamAuthoringTestCase):
    """Private authoring data never becomes cognition or a character effect."""

    @covers_requirement("narrative-memory::cognition-is-owner-scoped-and-provenance-preserving")
    def test_draft_and_request_stay_private_and_produce_no_cognition(self):
        before = self.character_attribute_snapshot()
        direction = new_story_direction()
        draft = save_draft(owner_id=self.owner_id, direction=direction, tick=100)
        request = confirm_draft(draft_id=draft.draft_id, owner_id=self.owner_id, tick=101)

        # No narrative fact, projection work, or memory row is created.
        self.assertEqual(NarrativeEvent.objects.count(), 0)
        self.assertEqual(ProjectionProgress.objects.count(), 0)
        self.assertEqual(MemoryRecord.objects.count(), 0)

        # Retrieval after the private discussion is empty for every owner.
        self.assertEqual(
            get_owner_memories(owner_id=self.owner_id, requester_id=self.owner_id), []
        )
        recalled = fast_recall(owner_id=self.owner_id, requester_id=self.owner_id, query=direction["summary"])
        self.assertEqual(recalled.all_selected, ())
        self.assertEqual(
            get_owner_memories(owner_id=self.other_id, requester_id=self.other_id), []
        )

        # No clue, item, quest progress, stat, skill, buff, or codex change.
        self.assertEqual(self.character_attribute_snapshot(), before)

        # Authoring rows are readable by their owner only.
        self.assertEqual(get_draft(draft.draft_id, self.owner_id).pk, draft.pk)
        self.assertEqual(get_request(request.submission_key, self.owner_id).pk, request.pk)
        with self.assertRaises(AuthoringAccessError):
            get_draft(draft.draft_id, self.other_id)
        with self.assertRaises(AuthoringAccessError):
            get_request(request.submission_key, self.other_id)
        self.assertEqual(list_drafts(self.other_id), [])
        self.assertEqual(list_requests(self.other_id), [])


class DreamAuthoringDraftTests(DreamAuthoringTestCase):
    """Drafts are owner-scoped, content-preserving, and end at confirmation."""

    def test_save_is_idempotent_and_content_changes_advance_the_version(self):
        direction = new_story_direction()
        first = save_draft(
            owner_id=self.owner_id, direction=direction, tick=100, draft_id="draft_replay_01"
        )
        replay = save_draft(
            owner_id=self.owner_id, direction=direction, tick=999, draft_id="draft_replay_01"
        )
        self.assertEqual(first.pk, replay.pk)
        self.assertEqual(replay.revision, 1)
        self.assertEqual(replay.created_tick, 100)

        revised = save_draft(
            owner_id=self.owner_id,
            direction={**direction, "summary": "合成夢境方向：改寫後的推進。"},
            tick=101,
            draft_id="draft_replay_01",
        )
        self.assertEqual(revised.revision, 2)
        self.assertEqual(revised.direction["summary"], "合成夢境方向：改寫後的推進。")
        self.assertFalse(draft_is_confirmed(revised))

        with self.assertRaises(AuthoringAccessError):
            save_draft(
                owner_id=self.other_id, direction=direction, draft_id="draft_replay_01"
            )

    def test_editing_a_confirmed_version_returns_it_to_unconfirmed(self):
        draft = save_draft(owner_id=self.owner_id, direction=new_story_direction(), tick=100)
        request = confirm_draft(draft_id=draft.draft_id, owner_id=self.owner_id, tick=100)
        self.assertTrue(draft_is_confirmed(get_draft(draft.draft_id, self.owner_id)))

        edited = save_draft(
            owner_id=self.owner_id,
            direction={**new_story_direction(), "emphasis": ["合成新的重點"]},
            tick=102,
            draft_id=draft.draft_id,
        )
        self.assertEqual(edited.revision, 2)
        self.assertFalse(draft_is_confirmed(edited))
        # The confirmed version remains durable and immutable.
        self.assertEqual([row.pk for row in list_requests(self.owner_id)], [request.pk])
        self.assertEqual(
            CreativeRequest.objects.get(pk=request.pk).version, request.version
        )

    def test_drafts_are_durable_and_identity_is_immutable(self):
        draft = save_draft(
            owner_id=self.owner_id, direction=new_story_direction(), tick=100, draft_id="draft_durable_01"
        )
        with self.assertRaises(ValueError):
            draft.owner_id = self.other_id
            draft.save()
        with self.assertRaises(ValueError):
            draft.delete()
        with self.assertRaises(ValueError):
            AuthoringDraft.objects.filter(pk=draft.pk).delete()
        with self.assertRaises(ValueError):
            AuthoringDraft.objects.filter(pk=draft.pk).update(revision=99)

    def test_draft_content_must_be_bounded_plain_json(self):
        with self.assertRaises(AuthoringError):
            save_draft(owner_id=self.owner_id, direction=["not", "an", "object"])
        with self.assertRaises(AuthoringError):
            save_draft(
                owner_id=self.owner_id,
                direction={**new_story_direction(), "summary": {1, 2}},
            )
        with self.assertRaises(AuthoringError):
            save_draft(
                owner_id=self.owner_id,
                direction={**new_story_direction(), "summary": "x" * 70000},
            )
        with self.assertRaises(AuthoringError):
            save_draft(
                owner_id=self.owner_id,
                direction=new_story_direction(),
                sources=[{"kind": "session"}],
            )
        self.assertEqual(AuthoringDraft.objects.count(), 0)


class DreamAuthoringValidationTests(DreamAuthoringTestCase):
    """Deterministic validation returns concrete reasons and never substitutes."""

    def _reason_codes(self, direction):
        result = validate_direction(direction, owner_id=self.owner_id)
        self.assertFalse(result.valid)
        return result.reason_codes

    def test_committed_history_rewrite_is_rejected_with_a_concrete_reason(self):
        thread = self.owner_thread("thread_authoring_history")
        committed = self.committed_event("synthetic:authoring:committed:1")
        direction = new_story_direction(
            kind="thread_direction",
            thread_id=thread.thread_id,
            revisions=[{"aspect": "history", "ref": committed.source_id}],
        )
        draft = save_draft(owner_id=self.owner_id, direction=direction, tick=100)

        with self.assertRaises(DirectionValidationError) as caught:
            confirm_draft(draft_id=draft.draft_id, owner_id=self.owner_id, tick=101)
        self.assertEqual(caught.exception.reason_codes, ("committed_history_rewrite",))
        self.assertEqual(
            caught.exception.reasons[0].message, REASON_MESSAGES["committed_history_rewrite"]
        )

        # The incompatible draft survives unchanged and unconfirmed.
        self.assertEqual(
            CreativeRequest.objects.count(), 0
        )
        stored = get_draft(draft.draft_id, self.owner_id)
        self.assertEqual(stored.direction, draft.direction)
        self.assertEqual(stored.revision, 1)
        self.assertFalse(draft_is_confirmed(stored))

    def test_personality_and_outcome_rewrites_are_rejected(self):
        thread = self.owner_thread("thread_authoring_aspects")
        codes = self._reason_codes(
            new_story_direction(
                kind="thread_direction",
                thread_id=thread.thread_id,
                revisions=[
                    {"aspect": "personality", "ref": self.owner_id},
                    {"aspect": "outcome", "ref": "synthetic:authoring:outcome"},
                ],
            )
        )
        self.assertEqual(
            codes, ("deterministic_outcome_rewrite", "established_personality_rewrite")
        )

    def test_history_reference_must_exist(self):
        codes = self._reason_codes(
            new_story_direction(
                revisions=[{"aspect": "history", "ref": "synthetic:authoring:absent"}]
            )
        )
        self.assertEqual(codes, ("unknown_reference",))

    def test_effects_are_unauthorized(self):
        codes = self._reason_codes(
            new_story_direction(effects=["clue", "skill"])
        )
        self.assertEqual(codes, ("unauthorized_effects",))

    def test_thread_direction_requires_an_owned_non_terminal_thread(self):
        self.assertEqual(
            self._reason_codes(
                new_story_direction(kind="thread_direction", thread_id="thread_absent")
            ),
            ("unknown_thread",),
        )

        foreign = create_thread(
            thread_id="thread_authoring_foreign",
            origin="event:synthetic:authoring:foreign:origin",
            participants=[self.other_id],
            visible_to=[self.other_id],
            tick=100,
        )
        self.assertEqual(
            self._reason_codes(
                new_story_direction(kind="thread_direction", thread_id=foreign.thread_id)
            ),
            ("inaccessible_thread",),
        )

        resolved = self.owner_thread("thread_authoring_resolved")
        resolve_thread(thread_id=resolved.thread_id, reason="synthetic completion", tick=101)
        self.assertEqual(
            self._reason_codes(
                new_story_direction(kind="thread_direction", thread_id=resolved.thread_id)
            ),
            ("terminal_thread",),
        )

    def test_structural_rejections_are_concrete(self):
        self.assertEqual(self._reason_codes({}), ("malformed_direction",))
        self.assertEqual(
            self._reason_codes(new_story_direction(kind="rewrite_everything")),
            ("unknown_direction_kind",),
        )
        self.assertEqual(
            self._reason_codes(new_story_direction(thread_id="thread_any")),
            ("unexpected_thread",),
        )
        self.assertEqual(
            self._reason_codes(new_story_direction(participants=["same", "same"])),
            ("malformed_participants",),
        )
        self.assertEqual(
            self._reason_codes({**new_story_direction(), "unknown_field": 1}),
            ("malformed_direction",),
        )
        self.assertEqual(
            self._reason_codes(new_story_direction(participants=[""])),
            ("malformed_participants",),
        )

    def test_validation_is_deterministic_and_normalizes_references(self):
        thread = self.owner_thread("thread_authoring_canonical")
        direction = new_story_direction(
            kind="thread_direction",
            thread_id=f"  {thread.thread_id}  ",
            participants=[" 1 ", "2"],
            themes=[" 合成主題 "],
        )
        first = validate_direction(direction, owner_id=self.owner_id)
        second = validate_direction(direction, owner_id=self.owner_id)
        self.assertTrue(first.valid)
        self.assertEqual(first.reasons, second.reasons)
        self.assertEqual(first.direction["thread_id"], thread.thread_id)
        self.assertEqual(first.direction["participants"], ["1", "2"])
        self.assertEqual(first.direction["themes"], ["合成主題"])


class DreamAuthoringConfirmationTests(DreamAuthoringTestCase):
    """Confirmation submits exactly one durable request version per version."""

    @covers_requirement("narrative-memory::cognition-is-owner-scoped-and-provenance-preserving")
    def test_unrelated_new_story_is_eligible_only_after_confirmation(self):
        direction = new_story_direction(
            summary="合成夢境方向：與過往經驗無關的全新篇章。",
            participants=["1001", "1002"],
        )
        draft = save_draft(owner_id=self.owner_id, direction=direction, tick=100)
        # Draft preservation schedules no work.
        self.assertEqual(CreativeRequest.objects.count(), 0)
        self.assertFalse(draft_is_confirmed(get_draft(draft.draft_id, self.owner_id)))
        self.assertTrue(validate_direction(direction, owner_id=self.owner_id).valid)

        request = confirm_draft(draft_id=draft.draft_id, owner_id=self.owner_id, tick=100)
        self.assertEqual(request.version, 1)
        self.assertEqual(request.validation_status, "valid")
        self.assertEqual(request.submitted_tick, 100)
        self.assertEqual(request.direction, validate_direction(direction, owner_id=self.owner_id).direction)
        self.assertTrue(draft_is_confirmed(get_draft(draft.draft_id, self.owner_id)))

    def test_duplicate_confirmation_across_reconnect_submits_once(self):
        draft = save_draft(
            owner_id=self.owner_id, direction=new_story_direction(), tick=100, draft_id="draft_reconnect_01"
        )
        first = confirm_draft(draft_id=draft.draft_id, owner_id=self.owner_id, tick=100)
        # Reconnect: a fresh handle re-confirms the same valid version.
        again = confirm_draft(draft_id="draft_reconnect_01", owner_id=self.owner_id, tick=500)
        self.assertEqual(first.pk, again.pk)
        self.assertEqual(again.submitted_tick, 100)
        self.assertEqual(
            CreativeRequest.objects.filter(owner_id=self.owner_id).count(), 1
        )
        self.assertEqual(
            again.submission_key, submission_key_for("draft_reconnect_01", 1)
        )

    def test_new_version_after_edit_keeps_the_original_immutable(self):
        draft = save_draft(owner_id=self.owner_id, direction=new_story_direction(), tick=100)
        first = confirm_draft(draft_id=draft.draft_id, owner_id=self.owner_id, tick=100)
        save_draft(
            owner_id=self.owner_id,
            direction={**new_story_direction(), "summary": "合成夢境方向：第二版。"},
            tick=101,
            draft_id=draft.draft_id,
        )
        second = confirm_draft(draft_id=draft.draft_id, owner_id=self.owner_id, tick=102)
        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(second.version, 2)
        self.assertEqual(
            sorted(
                CreativeRequest.objects.filter(owner_id=self.owner_id).values_list("version", flat=True)
            ),
            [1, 2],
        )
        with self.assertRaises(ValueError):
            first.save()
        with self.assertRaises(ValueError):
            CreativeRequest.objects.filter(pk=first.pk).update(submitted_tick=999)
        with self.assertRaises(ValueError):
            CreativeRequest.objects.filter(pk=first.pk).delete()
        with self.assertRaises(ValueError):
            first.delete()

    def test_confirmation_is_offline_and_opens_no_transport(self):
        import world.narrative.authoring as authoring_module

        disabled = default_profiles()
        for layer in LAYER_NAMES:
            disabled[layer]["enabled"] = False
        draft = save_draft(owner_id=self.owner_id, direction=new_story_direction(), tick=100)
        with (
            override_settings(LLM_PROFILES=disabled),
            patch("socket.socket", side_effect=AssertionError("no transport")),
        ):
            request = confirm_draft(draft_id=draft.draft_id, owner_id=self.owner_id, tick=100)
        self.assertEqual(request.validation_status, "valid")

        # The authoring boundary is generation-free by construction.
        bound_modules = {
            value.__name__
            for value in vars(authoring_module).values()
            if isinstance(value, types.ModuleType)
        }
        self.assertEqual(
            sorted(name for name in bound_modules if name.startswith("world.ai")), []
        )

    def test_confirmed_snapshot_cannot_be_altered_by_later_caller_mutation(self):
        direction = new_story_direction()
        expected_summary = direction["summary"]
        draft = save_draft(owner_id=self.owner_id, direction=direction, tick=100)
        request = confirm_draft(draft_id=draft.draft_id, owner_id=self.owner_id, tick=100)
        direction["summary"] = "caller mutation after confirmation"
        del direction["themes"]
        stored = CreativeRequest.objects.get(pk=request.pk)
        self.assertEqual(stored.direction["summary"], expected_summary)
        self.assertEqual(stored.direction["themes"], ["合成主題"])


class DreamAuthoringObservabilityTests(DreamAuthoringTestCase):
    """Boundary events carry identifiers, counts and codes only."""

    @covers_requirement("observability-logging::facade-is-the-sole-game-code-log-entry-point")
    def test_boundary_events_never_carry_direction_prose(self):
        import world.narrative.authoring as authoring_module

        info_calls: list[tuple[str, dict]] = []
        warn_calls: list[tuple[str, dict]] = []

        def capture_info(event, *, context=None, exc=None):
            info_calls.append((event, dict(context or {})))

        def capture_warn(event, *, context=None, exc=None):
            warn_calls.append((event, dict(context or {})))

        summary = "不應寫入日誌的合成方向摘要。"
        draft_id = "draft_logging_01"
        with (
            patch.object(authoring_module, "log_info", side_effect=capture_info),
            patch.object(authoring_module, "log_warn", side_effect=capture_warn),
            self.captureOnCommitCallbacks(execute=True),
        ):
            save_draft(
                owner_id=self.owner_id,
                direction=new_story_direction(summary=summary),
                tick=100,
                draft_id=draft_id,
            )
            confirm_draft(draft_id=draft_id, owner_id=self.owner_id, tick=100)
            save_draft(
                owner_id=self.owner_id,
                direction=new_story_direction(
                    summary=summary,
                    revisions=[{"aspect": "outcome", "ref": "synthetic:authoring:outcome"}],
                ),
                tick=101,
                draft_id=draft_id,
            )
            with self.assertRaises(DirectionValidationError):
                confirm_draft(draft_id=draft_id, owner_id=self.owner_id, tick=102)

        self.assertEqual(
            [event for event, _ in info_calls],
            [
                "narrative_authoring_draft_saved",
                "narrative_authoring_request_submitted",
                "narrative_authoring_draft_edited",
            ],
        )
        self.assertEqual(warn_calls[0][0], "narrative_authoring_validation_rejected")
        self.assertEqual(warn_calls[0][1]["reasons"], ["deterministic_outcome_rewrite"])
        for _event, context in (*info_calls, *warn_calls):
            serialized = json.dumps(context, ensure_ascii=False)
            self.assertNotIn(summary, serialized)
            self.assertNotIn(REASON_MESSAGES["deterministic_outcome_rewrite"], serialized)


class DreamAuthoringReadModelTests(DreamAuthoringTestCase):
    """Confirmed-version reads are owner-scoped and spoiler-filtered."""

    def test_latest_confirmed_request_has_a_deterministic_tie_break(self):
        self.assertIsNone(latest_confirmed_request(self.owner_id))
        first_draft = save_draft(
            owner_id=self.owner_id, direction=new_story_direction(), tick=100, draft_id="draft_a"
        )
        confirm_draft(draft_id=first_draft.draft_id, owner_id=self.owner_id, tick=100)
        second_draft = save_draft(
            owner_id=self.owner_id, direction=new_story_direction(), tick=100, draft_id="draft_b"
        )
        confirm_draft(draft_id=second_draft.draft_id, owner_id=self.owner_id, tick=100)
        latest = latest_confirmed_request(self.owner_id)
        self.assertEqual(latest.submission_key, submission_key_for("draft_b", 1))
        self.assertIsNone(latest_confirmed_request(self.other_id))

    def test_collaborator_brief_exposes_preferences_only(self):
        self.assertIsNone(collaborator_creative_brief(self.owner_id))
        direction = new_story_direction(
            themes=["合成主題一"], atmosphere=["合成氛圍"], exclusions=["合成排除"],
            participants=["1001"],
        )
        draft = save_draft(
            owner_id=self.owner_id,
            direction=direction,
            sources=[{"kind": "session", "ref": "synthetic-session-1"}],
            tick=100,
        )
        confirm_draft(draft_id=draft.draft_id, owner_id=self.owner_id, tick=100)
        brief = collaborator_creative_brief(self.owner_id)
        self.assertEqual(brief.owner_id, self.owner_id)
        self.assertEqual(brief.summary, direction["summary"])
        self.assertEqual(brief.themes, ("合成主題一",))
        self.assertEqual(brief.atmosphere, ("合成氛圍",))
        self.assertEqual(brief.exclusions, ("合成排除",))
        self.assertEqual(brief.participants, ("1001",))
        self.assertFalse(hasattr(brief, "sources"))
        self.assertFalse(hasattr(brief, "direction"))
        # A later unconfirmed edit does not displace the explicitly confirmed version.
        save_draft(
            owner_id=self.owner_id,
            direction={**direction, "summary": "合成夢境方向：未確認的修改。"},
            tick=101,
            draft_id=draft.draft_id,
        )
        self.assertEqual(collaborator_creative_brief(self.owner_id).summary, direction["summary"])

    def test_confirmed_request_rows_are_durable_and_immutable(self):
        draft = save_draft(owner_id=self.owner_id, direction=new_story_direction(), tick=100)
        request = confirm_draft(draft_id=draft.draft_id, owner_id=self.owner_id, tick=100)
        self.assertEqual(
            CreativeRequest.objects.filter(submission_key=request.submission_key).count(), 1
        )
        # PROTECT plus the delete guard means a draft with requests cannot vanish.
        with self.assertRaises(ValueError):
            draft.delete()
        with self.assertRaises(ValueError):
            CreativeRequest.objects.bulk_update([request], ["submitted_tick"])
