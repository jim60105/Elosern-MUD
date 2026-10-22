"""Adult memories authorize fields per participant.

The two ADDED requirements of ``authorize-adult-deed-memory-projections``
("Visibility does not grant adult content knowledge" and "Adult memories
authorize fields per participant") have no canonical id until the delta syncs
at archive. These tests therefore annotate the closest current canonical
requirements: ``narrative-memory``'s owner-scoped cognition and restart-safe
projection, ``narrative-events``' adult-evidence boundary, and the title
capability's personally authorized deed eligibility.
"""

import json
from pathlib import Path
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.narrative import adult_projection, memory, recent_deeds
from world.narrative.adult_projection import (
    ADULT_MEMORY_CATEGORY,
    AdultProjectionError,
    build_adult_memory_content,
    project_adult_action_for_recipient,
)
from world.narrative.events import record_narrative_event
from world.narrative.memory import (
    get_owner_memories,
    process_pending_narrative_memory_projections,
    project_narrative_event_to_memories,
)
from world.narrative.models import MemoryRecord, NarrativeEvent, ProjectionProgress


ACTOR_GRANTS = [
    "actor",
    "act_key",
    "recipients",
    "resistance_verdict",
    "physical_effects",
    "own_state_transitions",
    "own_counter_changes",
    "actor_milestones",
]

RECIPIENT_GRANTS = [
    "target_own_outcome",
    "resistance_verdict",
    "effects_on_target",
    "target_state_transitions",
    "target_counter_changes",
    "target_milestones",
]


def adult_content(
    source_id: str,
    *,
    actor_pk: str,
    actor_name: str,
    recipient_pk: str,
    recipient_name: str,
    other_roll: int = 42,
    other_milestone: str = "virginity_loss",
    grants: dict[str, list[str]] | None = None,
) -> dict:
    """Behind one production-shaped mixed-knowability adult payload."""
    return {
        "action_source_id": source_id,
        "act_key": "caress",
        "act_name": "溫柔愛撫",
        "encounter_context": None,
        "actor": {"id": actor_pk, "name": actor_name, "role": "actor"},
        "recipients": [
            {"id": recipient_pk, "name": recipient_name, "role": "recipient"}
        ],
        "outcomes": {
            "transitions": [
                {
                    "target_id": actor_pk,
                    "target_name": actor_name,
                    "event": "actor_transition",
                },
                {
                    "target_id": recipient_pk,
                    "target_name": recipient_name,
                    "event": "recipient_transition",
                },
            ],
            "counters": [
                {
                    "target_id": actor_pk,
                    "target_name": actor_name,
                    "counter": "actor_counter",
                },
                {
                    "target_id": recipient_pk,
                    "target_name": recipient_name,
                    "counter": "recipient_counter",
                },
            ],
            "resistance": [
                {
                    "actor_id": actor_pk,
                    "target_id": recipient_pk,
                    "target_name": recipient_name,
                    "resisted": False,
                    "auto_comply": True,
                    "roll": other_roll,
                }
            ],
            "effects": [
                {
                    "kind": "pleasure_gain",
                    "actor_id": actor_pk,
                    "target_id": recipient_pk,
                    "target_name": recipient_name,
                    "result": {"amount": 11},
                }
            ],
        },
        "milestones": [
            {
                "source_id": "ms:actor:1",
                "milestone_kind": "experience_type",
                "identifier": "actor_milestone",
                "entity_id": actor_pk,
            },
            {
                "source_id": "ms:recipient:1",
                "milestone_kind": "state_transition",
                "identifier": other_milestone,
                "entity_id": recipient_pk,
            },
        ],
        "visibility": "public",
        "privacy": {
            "private_experience": False,
            "consent_inferred": False,
            "willingness_inferred": False,
            "relationship_inferred": False,
            "public_notoriety": False,
        },
        "field_access": grants
        if grants is not None
        else {actor_pk: list(ACTOR_GRANTS), recipient_pk: list(RECIPIENT_GRANTS)},
    }


class AdultMemoryProjectionTests(EvenniaTestCase):
    """Adult cognition projection applies the shared per-recipient boundary."""

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="AdultRoom")
        self.player = create_object(PlayerCharacter, key="AdultActor", location=self.room)
        self.other = create_object(PlayerCharacter, key="AdultRecipient", location=self.room)
        self.bystander = create_object(NPC, key="AdultBystander", location=self.room)
        self.player_pk = str(self.player.pk)
        self.other_pk = str(self.other.pk)
        self.bystander_pk = str(self.bystander.pk)

    def _record(self, source_id: str, content: dict, *, tick: int = 100):
        event, progress, _ = record_narrative_event(
            source_id=source_id,
            event_type="adult_action",
            content=content,
            participants=[self.player_pk, self.other_pk],
            tick=tick,
            visibility=content.get("visibility", "public"),
        )
        return event, progress

    def _content(self, source_id: str, **overrides) -> dict:
        return adult_content(
            source_id,
            actor_pk=self.player_pk,
            actor_name=self.player.key,
            recipient_pk=self.other_pk,
            recipient_name=self.other.key,
            **overrides,
        )

    @covers_requirement(
        "narrative-memory::cognition-is-owner-scoped-and-provenance-preserving",
        "narrative-events::adult-evidence-does-not-invent-consent-or-public-standing",
    )
    def test_public_adult_event_hides_another_participants_private_history(self):
        """Scenario: Public adult event hides another participant's private history.

        WHEN an adult action is public because a third living entity is present
        THEN each participant's memory holds only knowable acts, roles and
        results, the third entity gains no memory, and no private milestone,
        roll, compliance reasoning or unknown counter is stored anywhere.
        """
        content = self._content("adult:public:1")
        event, _ = self._record("adult:public:1", content)
        self.assertEqual(event.visibility, "public")

        records = project_narrative_event_to_memories(event, projector_version=1)
        self.assertEqual(len(records), 2)
        by_owner = {record.owner_id: record for record in records}
        actor_record = by_owner[self.player_pk]
        recipient_record = by_owner[self.other_pk]

        actor_text = json.dumps(actor_record.content, ensure_ascii=False, sort_keys=True)
        self.assertIn("actor_milestone", actor_text)
        self.assertNotIn("virginity_loss", actor_text)
        self.assertNotIn('"roll"', actor_text)
        self.assertNotIn("auto_comply", actor_text)
        self.assertEqual(
            [row["counter"] for row in actor_record.content["outcomes"]["counters"]],
            ["actor_counter"],
        )
        self.assertEqual(
            [row["event"] for row in actor_record.content["outcomes"]["transitions"]],
            ["actor_transition"],
        )
        self.assertEqual(actor_record.content["role"], "actor")
        self.assertEqual(actor_record.content["summary"], "Adult act as actor: 溫柔愛撫")

        recipient_text = json.dumps(
            recipient_record.content, ensure_ascii=False, sort_keys=True
        )
        self.assertIn("virginity_loss", recipient_text)
        self.assertNotIn("actor_milestone", recipient_text)
        self.assertNotIn('"roll"', recipient_text)
        self.assertNotIn("auto_comply", recipient_text)
        self.assertEqual(
            [row["counter"] for row in recipient_record.content["outcomes"]["counters"]],
            ["recipient_counter"],
        )
        self.assertEqual(recipient_record.content["role"], "recipient")
        self.assertEqual(
            [row["id"] for row in recipient_record.content["recipients"]],
            [self.other_pk],
        )

        # The third living entity is present but is not a participant: presence
        # never grants participation or cognition.
        self.assertEqual(get_owner_memories(owner_id=self.bystander_pk), [])
        self.assertNotIn(self.bystander_pk, event.participants)

    @covers_requirement(
        "narrative-memory::cognition-is-owner-scoped-and-provenance-preserving"
    )
    def test_own_experience_retains_authorized_fields_and_provenance(self):
        """Scenario: Own experience remains available.

        WHEN the player is a participant and the affected fields are knowable
        THEN the authorized memory keeps those fields and source provenance
        without claiming consent, willingness or public recognition.
        """
        content = self._content("adult:own:1")
        event, _ = self._record("adult:own:1", content)
        records = project_narrative_event_to_memories(event, projector_version=1)
        actor_memory = next(r for r in records if r.owner_id == self.player_pk)

        self.assertEqual(actor_memory.category, ADULT_MEMORY_CATEGORY)
        self.assertEqual(actor_memory.source_id, "adult:own:1")
        self.assertEqual(actor_memory.projector_version, 1)
        self.assertEqual(actor_memory.content["action_source_id"], "adult:own:1")
        self.assertEqual(actor_memory.content["act_key"], "caress")
        self.assertEqual(actor_memory.content["actor"]["id"], self.player_pk)
        self.assertEqual(actor_memory.content["outcomes"]["effects"][0]["kind"], "pleasure_gain")
        self.assertEqual(
            actor_memory.content["privacy"],
            {
                "consent_inferred": False,
                "willingness_inferred": False,
                "relationship_inferred": False,
                "public_notoriety": False,
            },
        )
        summary = actor_memory.content["summary"]
        self.assertNotIn("consent", summary.lower())
        self.assertNotIn("witness", summary.lower())
        views = get_owner_memories(owner_id=self.player_pk)
        self.assertEqual([view.source_id for view in views], ["adult:own:1"])

    @covers_requirement(
        "narrative-memory::memory-projection-is-idempotent-and-restart-safe"
    )
    def test_replay_and_restart_reuse_the_source_once_per_authorized_owner(self):
        """Scenario: Memory projection reuses its source exactly once.

        WHEN committed adult projection is retried or resumes after a restart
        THEN the source and progress are reused once per authorized owner with
        no duplicate memory and no newly authorized private field.
        """
        content = self._content("adult:replay:1")
        self._record("adult:replay:1", content)

        self.assertEqual(process_pending_narrative_memory_projections(), 1)
        records = MemoryRecord.objects.filter(
            source_id="adult:replay:1", projector_version=1
        ).order_by("owner_id")
        self.assertEqual([r.owner_id for r in records], sorted([self.player_pk, self.other_pk]))
        before = {r.owner_id: dict(r.content) for r in records}

        self.assertEqual(process_pending_narrative_memory_projections(), 0)
        self.assertEqual(
            MemoryRecord.objects.filter(
                source_id="adult:replay:1", projector_version=1
            ).count(),
            2,
        )

        # A fresh occurrence with the same authorized facts is the only way the
        # content could change; the settled source itself never widens.
        progress = ProjectionProgress.objects.get(
            source_id="adult:replay:1", projector_version=1
        )
        self.assertEqual(progress.status, "completed")
        after = {
            r.owner_id: dict(r.content)
            for r in MemoryRecord.objects.filter(
                source_id="adult:replay:1", projector_version=1
            )
        }
        self.assertEqual(before, after)

    @covers_requirement(
        "narrative-memory::memory-projection-is-idempotent-and-restart-safe"
    )
    def test_failure_after_memory_creation_rolls_back_memory_and_progress(self):
        """Scenario: Memory projection reuses its source exactly once.

        WHEN the projection fails after the first owner's memory was created
        THEN memory, progress and evidence roll back together and a resumed
        projection creates exactly one memory per authorized owner.
        """
        content = self._content("adult:rollback:1")
        event, progress = self._record("adult:rollback:1", content)
        self.assertEqual(progress.status, "pending")

        calls = [0]
        original_record_memory = memory.record_memory

        def faulty_record_memory(*args, **kwargs):
            calls[0] += 1
            if calls[0] == 2:
                raise RuntimeError("Injected adult projection failure")
            return original_record_memory(*args, **kwargs)

        with patch("world.narrative.memory.record_memory", side_effect=faulty_record_memory):
            with self.assertRaises(RuntimeError):
                project_narrative_event_to_memories(event, projector_version=1)

        progress.refresh_from_db()
        self.assertEqual(progress.status, "pending")
        self.assertEqual(
            MemoryRecord.objects.filter(source_id="adult:rollback:1").count(), 0
        )

        self.assertEqual(process_pending_narrative_memory_projections(), 1)
        progress.refresh_from_db()
        self.assertEqual(progress.status, "completed")
        self.assertEqual(
            MemoryRecord.objects.filter(source_id="adult:rollback:1").count(), 2
        )

    @covers_requirement(
        "narrative-memory::memory-projection-is-idempotent-and-restart-safe",
        "narrative-events::adult-evidence-does-not-invent-consent-or-public-standing",
    )
    def test_unsupported_payload_fails_closed_without_raw_content_memory(self):
        """Scenario: Malformed adult payload does not bypass authorization.

        WHEN the adult payload cannot be authorized for a participant
        THEN projection settles with a bounded diagnostic and creates no
        raw-content memory for anyone.
        """
        warn: list[tuple[str, dict]] = []

        def record(event_name, *, context=None, exc=None):
            warn.append((event_name, dict(context or {})))

        content = self._content("adult:malformed:1")
        content["actor"] = {"id": "", "name": self.player.key, "role": "actor"}
        event, progress = self._record("adult:malformed:1", content)

        with patch("world.narrative.memory.log_warn", side_effect=record):
            self.assertEqual(process_pending_narrative_memory_projections(), 1)

        progress.refresh_from_db()
        self.assertEqual(progress.status, "completed")
        self.assertEqual(
            MemoryRecord.objects.filter(source_id="adult:malformed:1").count(), 0
        )
        self.assertFalse(
            MemoryRecord.objects.filter(
                source_id="adult:malformed:1", category="observation"
            ).exists()
        )
        self.assertEqual([name for name, _ in warn], ["adult_memory_projection_rejected"])
        self.assertLessEqual(
            set(warn[0][1]), {"source_id", "event_type", "projector_version"}
        )
        self.assertEqual(warn[0][1]["source_id"], "adult:malformed:1")

    @covers_requirement(
        "narrative-memory::memory-projection-is-idempotent-and-restart-safe"
    )
    def test_missing_field_access_and_unauthorized_owner_fail_closed(self):
        """A participant without a field grant gains no memory and no fallback.

        WHEN the payload carries no ``field_access``, or carries it without an
        entry for one participant THEN that participant gains no memory and
        nothing falls through to the raw-content branch.
        """
        warn: list[tuple[str, dict]] = []

        def record(event_name, *, context=None, exc=None):
            warn.append((event_name, dict(context or {})))

        unsigned = self._content("adult:unsigned:1")
        unsigned.pop("field_access")
        event, progress = self._record("adult:unsigned:1", unsigned)
        with patch("world.narrative.memory.log_warn", side_effect=record):
            project_narrative_event_to_memories(event, projector_version=1)
        progress.refresh_from_db()
        self.assertEqual(progress.status, "completed")
        self.assertEqual(
            MemoryRecord.objects.filter(source_id="adult:unsigned:1").count(), 0
        )
        self.assertEqual([name for name, _ in warn], ["adult_memory_projection_rejected"])

        partial = self._content(
            "adult:partial:1", grants={self.player_pk: list(ACTOR_GRANTS)}
        )
        event, _ = self._record("adult:partial:1", partial)
        records = project_narrative_event_to_memories(event, projector_version=1)
        self.assertEqual([r.owner_id for r in records], [self.player_pk])
        self.assertEqual(
            MemoryRecord.objects.filter(owner_id=self.other_pk).count(), 0
        )

    @covers_requirement(
        "narrative-memory::memory-projection-is-idempotent-and-restart-safe"
    )
    def test_malformed_second_owner_preparation_creates_no_partial_memory(self):
        """A rejection while preparing another owner creates nothing at all.

        WHEN one authorized owner's family is malformed THEN every envelope is
        rejected before the first write, so no partially authorized record is
        committed.
        """
        content = self._content("adult:prep:1")
        content["outcomes"]["counters"] = [
            {"target_id": self.other_pk, "target_name": self.other.key}
        ]
        event, progress = self._record("adult:prep:1", content)

        with patch("world.narrative.memory.log_warn"):
            project_narrative_event_to_memories(event, projector_version=1)

        progress.refresh_from_db()
        self.assertEqual(progress.status, "completed")
        self.assertEqual(MemoryRecord.objects.filter(source_id="adult:prep:1").count(), 0)

    @covers_requirement(
        "narrative-memory::cognition-is-owner-scoped-and-provenance-preserving"
    )
    def test_private_and_non_adult_sources_keep_existing_visibility_behavior(self):
        """Private sources stay unprojected and unrelated categories are unchanged.

        WHEN an adult action is private, or a non-adult event is projected
        THEN the existing skip and raw-content behavior is preserved.
        """
        private_content = self._content("adult:private:1")
        private_content["visibility"] = "private"
        private_event, private_progress = self._record(
            "adult:private:1", private_content
        )
        self.assertEqual(private_event.visibility, "private")
        self.assertEqual(
            project_narrative_event_to_memories(private_event, projector_version=1), []
        )
        private_progress.refresh_from_db()
        self.assertEqual(private_progress.status, "completed")
        self.assertEqual(
            MemoryRecord.objects.filter(source_id="adult:private:1").count(), 0
        )

        private_skill, private_skill_progress, _ = record_narrative_event(
            source_id="skill:private:1",
            event_type="skill_use",
            content={"skill_key": "t_probe", "actor": {"id": self.player_pk}},
            participants=[self.player_pk],
            tick=100,
            visibility="private",
        )
        self.assertEqual(
            project_narrative_event_to_memories(private_skill, projector_version=1), []
        )
        private_skill_progress.refresh_from_db()
        self.assertEqual(private_skill_progress.status, "completed")

        public_skill, _, _ = record_narrative_event(
            source_id="skill:public:1",
            event_type="skill_use",
            content={"skill_key": "t_probe", "actor": {"id": self.player_pk}},
            participants=[self.player_pk],
            tick=100,
        )
        records = project_narrative_event_to_memories(public_skill, projector_version=1)
        self.assertEqual([r.category for r in records], ["observation"])
        self.assertEqual(records[0].content["skill_key"], "t_probe")

    @covers_requirement(
        "title-system::recent-deed-eligibility-is-closed-and-personally-authorized",
        "narrative-memory::cognition-is-owner-scoped-and-provenance-preserving",
    )
    def test_one_source_reaches_nomination_and_authorized_memory(self):
        """The player's own occurrence reaches nomination; memory stays scoped.

        WHEN one occurrence is public because a third living entity is present
        THEN the same record supplies the player's own milestone to nomination
        while the player's memory omits the other participant's fields.
        """
        content = self._content("adult:shared:1")
        event, _ = self._record("adult:shared:1", content)
        self.assertEqual(event.participants, [self.player_pk, self.other_pk])

        rendered = recent_deeds.select_authorized_recent_deeds(
            self.player, frozen_tick=100
        ).rendered_json
        self.assertIn("adult:shared:1", rendered)
        self.assertIn("actor_milestone", rendered)
        self.assertNotIn("virginity_loss", rendered)

        records = project_narrative_event_to_memories(event, projector_version=1)
        actor_memory = next(r for r in records if r.owner_id == self.player_pk)
        self.assertEqual(actor_memory.source_id, "adult:shared:1")
        self.assertEqual(
            [row["identifier"] for row in actor_memory.content["milestones"]],
            ["actor_milestone"],
        )
        self.assertNotIn(
            "virginity_loss",
            json.dumps(actor_memory.content, ensure_ascii=False, sort_keys=True),
        )


class SharedAdultProjectionTests(EvenniaTestCase):
    """One projector serves nomination and memory without side effects."""

    def setUp(self):
        super().setUp()
        self.actor_pk = "1"
        self.recipient_pk = "2"

    def _content(self, source_id: str, *, other_roll: int = 42, other_milestone: str = "virginity_loss") -> dict:
        return adult_content(
            source_id,
            actor_pk=self.actor_pk,
            actor_name="Actor",
            recipient_pk=self.recipient_pk,
            recipient_name="Recipient",
            other_roll=other_roll,
            other_milestone=other_milestone,
        )

    @covers_requirement(
        "title-system::recent-deed-eligibility-is-closed-and-personally-authorized",
        "narrative-events::adult-evidence-does-not-invent-consent-or-public-standing",
    )
    def test_nomination_and_memory_resolve_the_same_projector(self):
        """Scenario: Production composition preserves the boundary.

        WHEN nomination and memory project an adult occurrence THEN both call
        the same recipient-parameterized helper, which imports no AI proposer
        and writes no gameplay state.
        """
        self.assertIs(
            recent_deeds.project_adult_action_for_recipient,
            adult_projection.project_adult_action_for_recipient,
        )
        self.assertIs(
            memory.project_adult_action_for_recipient,
            adult_projection.project_adult_action_for_recipient,
        )

        source = Path(adult_projection.__file__).read_text(encoding="utf-8")
        self.assertNotIn("from world.ai", source)
        self.assertNotIn("import world.ai", source)
        self.assertNotIn("MemoryRecord", source)
        self.assertNotIn("NarrativeEvent", source)

        before = (
            MemoryRecord.objects.count(),
            NarrativeEvent.objects.count(),
            ProjectionProgress.objects.count(),
        )
        project_adult_action_for_recipient(
            self._content("adult:pure:1"),
            recipient_pk=self.actor_pk,
            source_id="adult:pure:1",
        )
        self.assertEqual(
            before,
            (
                MemoryRecord.objects.count(),
                NarrativeEvent.objects.count(),
                ProjectionProgress.objects.count(),
            ),
        )

    @covers_requirement(
        "narrative-memory::cognition-is-owner-scoped-and-provenance-preserving"
    )
    def test_private_fields_of_another_participant_never_change_owner_content(self):
        """Another participant's private state cannot shape an owner's memory.

        WHEN the other participant's roll, compliance reasoning and milestone
        mutate THEN the owner's projection and memory content are identical.
        """
        baseline = self._content("adult:invariant:1")
        mutated = self._content(
            "adult:invariant:1", other_roll=99, other_milestone="climax_onset"
        )
        first = project_adult_action_for_recipient(
            baseline, recipient_pk=self.actor_pk, source_id="adult:invariant:1"
        )
        second = project_adult_action_for_recipient(
            mutated, recipient_pk=self.actor_pk, source_id="adult:invariant:1"
        )
        self.assertEqual(first, second)
        self.assertEqual(
            build_adult_memory_content(first, recipient_pk=self.actor_pk),
            build_adult_memory_content(second, recipient_pk=self.actor_pk),
        )

    @covers_requirement(
        "narrative-memory::cognition-is-owner-scoped-and-provenance-preserving"
    )
    def test_projection_is_detached_from_the_source_content(self):
        """The authorized envelope is a detached copy of allowlisted fields.

        WHEN the source content or a returned envelope is mutated THEN neither
        the other representation nor a fresh projection changes.
        """
        content = self._content("adult:detached:1")
        projection = project_adult_action_for_recipient(
            content, recipient_pk=self.actor_pk, source_id="adult:detached:1"
        )
        self.assertIsNot(projection["actor"], content["actor"])

        content["outcomes"]["counters"][0]["counter"] = "tampered_source"
        content["actor"]["name"] = "tampered_actor"
        self.assertEqual(projection["outcomes"]["counters"][0]["counter"], "actor_counter")
        self.assertEqual(projection["actor"]["name"], "Actor")

        projection["outcomes"]["counters"][0]["counter"] = "tampered_projection"
        fresh = project_adult_action_for_recipient(
            content, recipient_pk=self.actor_pk, source_id="adult:detached:1"
        )
        self.assertEqual(fresh["outcomes"]["counters"][0]["counter"], "tampered_source")

    @covers_requirement(
        "narrative-events::adult-evidence-does-not-invent-consent-or-public-standing"
    )
    def test_unsupported_shapes_raise_instead_of_widening_the_envelope(self):
        """Unsupported shapes fail closed rather than being coerced.

        WHEN an authorized effect field, encounter context, or verdict has an
        unsupported shape THEN the projector raises instead of inventing or
        widening a value.
        """
        with self.assertRaises(AdultProjectionError):
            project_adult_action_for_recipient(
                {"field_access": {self.actor_pk: list(ACTOR_GRANTS)}},
                recipient_pk=self.actor_pk,
                source_id="adult:no_actor",
            )

        unknown_result = self._content("adult:unknown_result:1")
        unknown_result["outcomes"]["effects"][0]["result"]["roll"] = 7
        with self.assertRaises(AdultProjectionError):
            project_adult_action_for_recipient(
                unknown_result,
                recipient_pk=self.actor_pk,
                source_id="adult:unknown_result:1",
            )

        unknown_row = self._content("adult:unknown_row:1")
        unknown_row["outcomes"]["effects"][0]["roll"] = 7
        with self.assertRaises(AdultProjectionError):
            project_adult_action_for_recipient(
                unknown_row,
                recipient_pk=self.actor_pk,
                source_id="adult:unknown_row:1",
            )

        text_verdict = self._content("adult:text_verdict:1")
        text_verdict["outcomes"]["resistance"][0]["resisted"] = "false"
        with self.assertRaises(AdultProjectionError):
            project_adult_action_for_recipient(
                text_verdict,
                recipient_pk=self.actor_pk,
                source_id="adult:text_verdict:1",
            )

        field_access_grants = self._content("adult:bad_context:1")
        field_access_grants["encounter_context"] = {"round_number": "three"}
        with self.assertRaises(AdultProjectionError):
            project_adult_action_for_recipient(
                field_access_grants,
                recipient_pk=self.actor_pk,
                source_id="adult:bad_context:1",
            )

    @covers_requirement(
        "narrative-events::adult-evidence-does-not-invent-consent-or-public-standing"
    )
    def test_unauthorized_recipient_receives_no_projection_or_participation(self):
        """An owner without a grant receives no projection at all.

        WHEN field_access names only the actor THEN the other participant is
        neither projected nor invention-attributed a role.
        """
        content = self._content("adult:unauthorized:1")
        content["field_access"] = {self.actor_pk: list(ACTOR_GRANTS)}
        self.assertIsNone(
            project_adult_action_for_recipient(
                content,
                recipient_pk=self.recipient_pk,
                source_id="adult:unauthorized:1",
            )
        )
        projection = project_adult_action_for_recipient(
            content, recipient_pk=self.actor_pk, source_id="adult:unauthorized:1"
        )
        self.assertEqual(projection["actor"]["id"], self.actor_pk)
        self.assertEqual(
            [row["id"] for row in projection["recipients"]], [self.recipient_pk]
        )
        self.assertEqual(
            [row["target_id"] for row in projection["outcomes"]["counters"]],
            [self.actor_pk],
        )

    @covers_requirement(
        "narrative-events::adult-evidence-does-not-invent-consent-or-public-standing"
    )
    def test_unauthorized_families_are_never_validated(self):
        """A family the recipient cannot know is never read or rejected on.

        WHEN an outcome family the recipient holds no token for is malformed
        THEN that owner's projection still succeeds, because the family is not
        theirs to validate; the owner holding the token still fails closed.
        """
        content = self._content("adult:perm_first:1")
        content["outcomes"]["resistance"][0]["resisted"] = "false"
        content["field_access"] = {
            self.actor_pk: list(ACTOR_GRANTS),
            self.recipient_pk: ["target_own_outcome", "target_milestones"],
        }

        projection = project_adult_action_for_recipient(
            content,
            recipient_pk=self.recipient_pk,
            source_id="adult:perm_first:1",
        )
        self.assertEqual(projection["outcomes"], {})

        with self.assertRaises(AdultProjectionError):
            project_adult_action_for_recipient(
                content,
                recipient_pk=self.actor_pk,
                source_id="adult:perm_first:1",
            )
