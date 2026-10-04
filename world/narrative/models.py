from django.db import models


class ImmutableLetterQuerySet(models.QuerySet):
    """Prevent rewriting accepted send records through bulk ORM operations."""

    def update(self, *args, **kwargs):
        raise ValueError("Accepted letter sends are immutable.")

    def bulk_update(self, *args, **kwargs):
        raise ValueError("Accepted letter sends are immutable.")

    def delete(self, *args, **kwargs):
        raise ValueError("Accepted letter sends are immutable.")

    def bulk_create(self, objs, **kwargs):
        if kwargs.get("update_conflicts"):
            raise ValueError("Accepted letter sends are immutable.")
        return super().bulk_create(objs, **kwargs)


class LetterSend(models.Model):
    """Immutable accepted correspondence; state lives in a separate row."""

    objects = ImmutableLetterQuerySet.as_manager()
    source_id = models.CharField(max_length=128, unique=True)
    sender_id = models.CharField(max_length=64)
    recipient_id = models.CharField(max_length=64)
    recipient_kind = models.CharField(max_length=16)
    body = models.TextField()
    sent_tick = models.BigIntegerField()
    due_tick = models.BigIntegerField(db_index=True)
    reply_to = models.CharField(max_length=128, blank=True, default="")
    source_snapshot_id = models.CharField(max_length=128, blank=True, default="")

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Accepted letter sends are immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Accepted letter sends are immutable.")

    class Meta:
        app_label = "narrative"


class LetterState(models.Model):
    """Delivery state, without a recipient live-object dependency."""

    letter = models.OneToOneField(LetterSend, on_delete=models.CASCADE)
    recipient_id = models.CharField(max_length=64)
    due_tick = models.BigIntegerField()
    status = models.CharField(max_length=32, default="sent")
    transition_id = models.CharField(max_length=255, blank=True, default="")
    collection_tick = models.BigIntegerField(null=True)
    read_tick = models.BigIntegerField(null=True)

    class Meta:
        app_label = "narrative"
        indexes = [
            models.Index(fields=["status", "due_tick"], name="letter_due_idx"),
            models.Index(fields=["recipient_id", "status"], name="letter_recipient_idx"),
        ]


class LetterReplyWork(models.Model):
    """One durable optional response per delivered incoming NPC letter."""

    letter = models.OneToOneField(LetterSend, on_delete=models.CASCADE)
    snapshot_id = models.CharField(max_length=128, blank=True, default="")
    outgoing_source_id = models.CharField(max_length=128, blank=True, default="")
    status = models.CharField(max_length=16, default="pending")

    class Meta:
        app_label = "narrative"


class AppendOnlyDialogueQuerySet(models.QuerySet):
    """Reject every update/delete path for original dialogue speech."""

    def update(self, *args, **kwargs):
        raise ValueError("Dialogue turns are append-only.")

    def delete(self, *args, **kwargs):
        raise ValueError("Dialogue turns are append-only.")

    def bulk_update(self, *args, **kwargs):
        raise ValueError("Dialogue turns are append-only.")

    def bulk_create(self, objs, **kwargs):
        if kwargs.get("update_conflicts"):
            raise ValueError("Dialogue turns are append-only.")
        return super().bulk_create(objs, **kwargs)


class DialogueTurn(models.Model):
    """Original pair speech, uniquely settled by submission/kind."""

    objects = AppendOnlyDialogueQuerySet.as_manager()
    submission_id = models.CharField(max_length=64, db_index=True)
    kind = models.CharField(max_length=16)
    npc_id = models.CharField(max_length=64, db_index=True)
    player_id = models.CharField(max_length=64, db_index=True)
    speaker = models.CharField(max_length=255)
    speech = models.TextField()
    tick = models.IntegerField(default=0)
    provenance = models.JSONField(default=dict)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Dialogue turns are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Dialogue turns are append-only.")

    class Meta:
        app_label = "narrative"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["submission_id", "kind"], name="unique_dialogue_submission_kind"
            )
        ]


class DialogueEpoch(models.Model):
    """Immutable pair boundary and optional derived summary generation."""

    objects = AppendOnlyDialogueQuerySet.as_manager()
    npc_id = models.CharField(max_length=64)
    player_id = models.CharField(max_length=64)
    sequence = models.PositiveIntegerField()
    version = models.CharField(max_length=64)
    reason = models.CharField(max_length=32)
    start_turn_id = models.BigIntegerField(default=0)
    summary = models.TextField(default="")
    generation_id = models.CharField(max_length=64, unique=True)
    source_refs = models.JSONField(default=list)
    snapshot_id = models.CharField(max_length=128, default="")

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Dialogue epochs are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Dialogue epochs are append-only.")

    class Meta:
        app_label = "narrative"
        constraints = [
            models.UniqueConstraint(fields=["npc_id", "player_id", "sequence"],
                                    name="unique_dialogue_pair_epoch")
        ]


class DialogueFrame(models.Model):
    """Exact bytes supplied at the original tick, never regenerated."""

    objects = AppendOnlyDialogueQuerySet.as_manager()
    epoch = models.ForeignKey(DialogueEpoch, on_delete=models.PROTECT)
    identity = models.CharField(max_length=64)
    content = models.TextField()
    tick = models.IntegerField(default=0)
    sources = models.JSONField(default=list)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Dialogue frames are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Dialogue frames are append-only.")

    class Meta:
        app_label = "narrative"
        constraints = [
            models.UniqueConstraint(fields=["epoch", "identity"],
                                    name="unique_dialogue_epoch_frame")
        ]


class NarrativeEvent(models.Model):
    """An immutable, committed narrative occurrence."""

    source_id = models.CharField(max_length=255, unique=True, db_index=True)
    event_type = models.CharField(max_length=64, db_index=True)
    content = models.JSONField(default=dict)
    participants = models.JSONField(default=list)
    location = models.CharField(max_length=128, blank=True, default="", db_index=True)
    tick = models.IntegerField(default=0, db_index=True)
    visibility = models.CharField(max_length=32, default="public")
    salience = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "narrative"
        db_table = "narrative_events"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"NarrativeEvent({self.source_id}, type={self.event_type})"


class ProjectionProgress(models.Model):
    """Pending or completed projection work for an event and projector version."""

    source_id = models.CharField(max_length=255, db_index=True)
    projector_version = models.IntegerField(default=1)
    status = models.CharField(max_length=32, default="pending", db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "narrative"
        db_table = "narrative_projection_progress"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["source_id", "projector_version"],
                name="unique_narrative_source_projector",
            )
        ]

    def __str__(self) -> str:
        return f"ProjectionProgress({self.source_id}, v={self.projector_version}, {self.status})"


class OwnerMemoryGeneration(models.Model):
    """Atomic monotonic generation counter for an owner's effective narrative memories."""

    owner_id = models.CharField(max_length=64, unique=True, db_index=True)
    generation = models.BigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "narrative"
        db_table = "narrative_owner_memory_generations"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"OwnerMemoryGeneration({self.owner_id}, gen={self.generation})"


class MemoryRecord(models.Model):
    """An immutable narrative memory record owned by an entity."""

    owner_id = models.CharField(max_length=64, db_index=True)
    tick = models.IntegerField(default=0, db_index=True)
    category = models.CharField(max_length=64, default="observation", db_index=True)
    content = models.JSONField(default=dict)
    salience = models.IntegerField(default=1)
    knowledge_scope = models.CharField(max_length=32, default="witnessed", db_index=True)
    confidence = models.FloatField(default=1.0)
    subjects = models.JSONField(default=list)
    source_id = models.CharField(max_length=255, db_index=True, blank=True, default="")
    projector_version = models.IntegerField(null=True, blank=True, db_index=True)
    derived_generation = models.IntegerField(null=True, blank=True)

    # Materialized effective metadata from latest revision
    effective_tier = models.CharField(max_length=32, default="working", db_index=True)
    effective_availability = models.CharField(max_length=32, default="active", db_index=True)
    latest_revision_number = models.IntegerField(default=1)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "narrative"
        db_table = "narrative_memory_records"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner_id", "source_id", "projector_version"],
                name="unique_owner_source_projector",
                condition=models.Q(projector_version__isnull=False),
            )
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            # Check if attempting to update immutable fields
            orig = MemoryRecord.objects.get(pk=self.pk)
            if (orig.owner_id != self.owner_id or orig.tick != self.tick or orig.content != self.content or
                orig.knowledge_scope != self.knowledge_scope or orig.source_id != self.source_id or
                orig.projector_version != self.projector_version or orig.category != self.category or
                orig.subjects != self.subjects or orig.derived_generation != self.derived_generation):
                raise ValueError("MemoryRecord content and provenance are immutable. Use revisions for effective metadata.")
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"MemoryRecord({self.id}, owner={self.owner_id}, scope={self.knowledge_scope}, status={self.effective_availability})"


class MemoryRevision(models.Model):
    """An append-only revision record for memory metadata, tier, decay, and supersession."""

    record = models.ForeignKey(MemoryRecord, on_delete=models.PROTECT, related_name="revisions")
    revision_number = models.IntegerField(default=1)
    availability = models.CharField(max_length=32, default="active")
    tier = models.CharField(max_length=32, default="working")
    decay_metadata = models.JSONField(default=dict)
    supersedes_record_id = models.CharField(max_length=64, blank=True, default="")
    relations = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("MemoryRevision records are append-only and cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("MemoryRevision records cannot be deleted.")

    class Meta:
        app_label = "narrative"
        db_table = "narrative_memory_revisions"
        ordering = ["record", "revision_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["record", "revision_number"],
                name="unique_memory_record_revision",
            )
        ]

    def __str__(self) -> str:
        return f"MemoryRevision(record={self.record_id}, rev={self.revision_number}, {self.availability}, tier={self.tier})"


class NarrativeContextSnapshot(models.Model):
    """An immutable context snapshot captured for a generative cognition call."""

    class AppendOnlyQuerySet(models.QuerySet):
        """QuerySet that refuses every bulk mutation or bulk delete path."""

        def update(self, *args, **kwargs):
            raise ValueError(
                "NarrativeContextSnapshot records are immutable and cannot be updated."
            )

        def delete(self, *args, **kwargs):
            raise ValueError(
                "NarrativeContextSnapshot records are immutable and cannot be deleted."
            )

        def _bulk_update(self, *args, **kwargs):
            raise ValueError(
                "NarrativeContextSnapshot records are immutable and cannot be bulk-updated."
            )

        def bulk_create(self, objs, **kwargs):
            if kwargs.get("update_conflicts"):
                raise ValueError(
                    "NarrativeContextSnapshot records are immutable and cannot be "
                    "conflict-updated through bulk insert."
                )
            return super().bulk_create(objs, **kwargs)

    objects = AppendOnlyQuerySet.as_manager()

    snapshot_id = models.CharField(max_length=128, unique=True, db_index=True)
    capability = models.CharField(max_length=64, db_index=True)
    prompt_version = models.CharField(max_length=64)
    schema_version = models.CharField(max_length=64, blank=True, default="")
    rendering_version = models.CharField(max_length=64)
    owner_id = models.CharField(max_length=64, db_index=True)
    owner_generation = models.BigIntegerField(default=0)
    sources = models.JSONField(default=list)
    thread_revisions = models.JSONField(default=dict)
    section_hashes = models.JSONField(default=dict)
    budget_accounting = models.JSONField(default=dict)
    truncation_decisions = models.JSONField(default=list)
    rendered_payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("NarrativeContextSnapshot records are immutable and cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("NarrativeContextSnapshot records are immutable and cannot be deleted.")

    class Meta:
        app_label = "narrative"
        db_table = "narrative_context_snapshots"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"NarrativeContextSnapshot({self.snapshot_id}, capability={self.capability}, owner={self.owner_id}, gen={self.owner_generation})"


class ImmutableStoryThreadQuerySet(models.QuerySet):
    """Prevent bulk rewrites of durable story threads and their provenance rows."""

    def update(self, *args, **kwargs):
        raise ValueError("Story threads are append-only; use the thread operations.")

    def bulk_update(self, *args, **kwargs):
        raise ValueError("Story threads are append-only; use the thread operations.")

    def delete(self, *args, **kwargs):
        raise ValueError("Story threads are durable and cannot be deleted.")

    def bulk_create(self, objs, **kwargs):
        if kwargs.get("update_conflicts"):
            raise ValueError("Story threads cannot be conflict-updated through bulk insert.")
        return super().bulk_create(objs, **kwargs)


class StoryThread(models.Model):
    """Durable continuity across events, interactions, and quests.

    Facts (factual summary and gameplay-established commitments) stay separate
    from plans and unresolved questions. ``origin`` and ``thread_id`` are
    immutable; every effective change appends a ``StoryThreadRevision`` and
    advances ``revision``.
    """

    objects = ImmutableStoryThreadQuerySet.as_manager()

    thread_id = models.CharField(max_length=128, unique=True, db_index=True)
    origin = models.CharField(max_length=255)
    participants = models.JSONField(default=list)
    visible_to = models.JSONField(default=list)
    factual_summary = models.TextField(default="", blank=True)
    unresolved_questions = models.JSONField(default=list)
    proposed_plans = models.JSONField(default=list)
    commitments = models.JSONField(default=list)
    memory_references = models.JSONField(default=list)
    development_ticks = models.JSONField(default=list)
    state = models.CharField(max_length=16, default="active", db_index=True)
    revision = models.BigIntegerField(default=1)
    created_tick = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.pk:
            original = StoryThread.objects.get(pk=self.pk)
            if (
                original.thread_id != self.thread_id
                or original.origin != self.origin
                or original.created_tick != self.created_tick
            ):
                raise ValueError(
                    "StoryThread identity, origin and creation tick are immutable."
                )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Story threads are durable and cannot be deleted.")

    class Meta:
        app_label = "narrative"
        db_table = "narrative_story_threads"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"StoryThread({self.thread_id}, state={self.state}, rev={self.revision})"


class StoryThreadLink(models.Model):
    """Durable provenance linking one source to one thread."""

    objects = ImmutableStoryThreadQuerySet.as_manager()

    thread = models.ForeignKey(
        StoryThread, on_delete=models.PROTECT, related_name="links"
    )
    source_kind = models.CharField(max_length=16)
    source_ref = models.CharField(max_length=255)
    relation = models.CharField(max_length=32)
    provenance = models.JSONField(default=dict)
    created_tick = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Story thread links are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Story thread links are append-only.")

    class Meta:
        app_label = "narrative"
        db_table = "narrative_story_thread_links"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["thread", "source_kind", "source_ref", "relation"],
                name="unique_story_thread_link",
            )
        ]
        indexes = [
            models.Index(fields=["source_kind", "source_ref"], name="thread_link_source_idx"),
        ]

    def __str__(self) -> str:
        return f"StoryThreadLink({self.thread_id}, {self.source_kind}:{self.source_ref}, {self.relation})"


class StoryThreadRevision(models.Model):
    """Append-only revision history for a story thread's effective changes."""

    objects = ImmutableStoryThreadQuerySet.as_manager()

    thread = models.ForeignKey(
        StoryThread, on_delete=models.PROTECT, related_name="revisions"
    )
    revision_number = models.IntegerField()
    operation = models.CharField(max_length=32)
    state = models.CharField(max_length=16)
    details = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Story thread revisions are append-only and cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Story thread revisions cannot be deleted.")

    class Meta:
        app_label = "narrative"
        db_table = "narrative_story_thread_revisions"
        ordering = ["thread", "revision_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["thread", "revision_number"],
                name="unique_story_thread_revision",
            )
        ]

    def __str__(self) -> str:
        return f"StoryThreadRevision(thread={self.thread_id}, rev={self.revision_number}, {self.operation})"


class ImmutableAuthoringDraftQuerySet(models.QuerySet):
    """Drafts change only through the authoring operations, never by bulk rewrite."""

    def update(self, *args, **kwargs):
        raise ValueError("Authoring drafts change only through the authoring operations.")

    def bulk_update(self, *args, **kwargs):
        raise ValueError("Authoring drafts change only through the authoring operations.")

    def delete(self, *args, **kwargs):
        raise ValueError("Authoring drafts are durable and cannot be deleted.")

    def bulk_create(self, objs, **kwargs):
        if kwargs.get("update_conflicts"):
            raise ValueError("Authoring drafts cannot be conflict-updated through bulk insert.")
        return super().bulk_create(objs, **kwargs)


class AuthoringDraft(models.Model):
    """Private creative discussion; never in-world knowledge.

    ``draft_id``, ``owner_id`` and ``created_tick`` are immutable. Every content
    change advances ``revision``; ``confirmed_revision`` records the revision of
    the last explicitly confirmed version, so ``confirmed_revision == revision``
    means the current version is confirmed and a later edit is unconfirmed again.
    """

    objects = ImmutableAuthoringDraftQuerySet.as_manager()

    draft_id = models.CharField(max_length=128, unique=True, db_index=True)
    owner_id = models.CharField(max_length=255, db_index=True)
    direction = models.JSONField(default=dict)
    sources = models.JSONField(default=list)
    revision = models.BigIntegerField(default=1)
    confirmed_revision = models.BigIntegerField(null=True)
    created_tick = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.pk:
            original = AuthoringDraft.objects.get(pk=self.pk)
            if (
                original.draft_id != self.draft_id
                or original.owner_id != self.owner_id
                or original.created_tick != self.created_tick
            ):
                raise ValueError(
                    "AuthoringDraft identity, owner and creation tick are immutable."
                )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Authoring drafts are durable and cannot be deleted.")

    class Meta:
        app_label = "narrative"
        db_table = "narrative_authoring_drafts"
        ordering = ["id"]

    def __str__(self) -> str:
        return f"AuthoringDraft({self.draft_id}, owner={self.owner_id}, rev={self.revision})"


class ImmutableCreativeRequestQuerySet(models.QuerySet):
    """Reject every rewrite path for confirmed request versions."""

    def update(self, *args, **kwargs):
        raise ValueError("Confirmed creative requests are immutable.")

    def bulk_update(self, *args, **kwargs):
        raise ValueError("Confirmed creative requests are immutable.")

    def delete(self, *args, **kwargs):
        raise ValueError("Confirmed creative requests are durable and cannot be deleted.")

    def bulk_create(self, objs, **kwargs):
        if kwargs.get("update_conflicts"):
            raise ValueError("Confirmed creative requests are immutable.")
        return super().bulk_create(objs, **kwargs)


class CreativeRequest(models.Model):
    """An immutable, deterministically validated request version.

    One row exists per confirmed draft revision. ``submission_key`` (derived from
    ``draft_id`` and ``version``) is the unique submission identity, so a repeated
    confirmation or a restart returns the same row instead of submitting twice;
    the unique ``(draft, version)`` constraint is the durable backstop.
    """

    objects = ImmutableCreativeRequestQuerySet.as_manager()

    submission_key = models.CharField(max_length=160, unique=True, db_index=True)
    draft = models.ForeignKey(
        AuthoringDraft, on_delete=models.PROTECT, related_name="requests"
    )
    owner_id = models.CharField(max_length=255, db_index=True)
    version = models.BigIntegerField()
    direction = models.JSONField(default=dict)
    sources = models.JSONField(default=list)
    validation_status = models.CharField(max_length=16, default="valid")
    submitted_tick = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Confirmed creative requests are immutable.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Confirmed creative requests are durable and cannot be deleted.")

    class Meta:
        app_label = "narrative"
        db_table = "narrative_authoring_requests"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["draft", "version"],
                name="unique_creative_request_version",
            )
        ]

    def __str__(self) -> str:
        return f"CreativeRequest({self.submission_key}, owner={self.owner_id}, v={self.version})"


class DreamSessionQuerySet(models.QuerySet):
    """Dream sessions change only through the dream-session operations."""

    def update(self, *args, **kwargs):
        raise ValueError("Dream sessions change only through the dream-session operations.")

    def bulk_update(self, *args, **kwargs):
        raise ValueError("Dream sessions change only through the dream-session operations.")

    def delete(self, *args, **kwargs):
        raise ValueError("Dream sessions are durable and cannot be deleted.")

    def bulk_create(self, objs, **kwargs):
        if kwargs.get("update_conflicts"):
            raise ValueError("Dream sessions cannot be conflict-updated through bulk insert.")
        return super().bulk_create(objs, **kwargs)


class DreamSession(models.Model):
    """Durable accounting for one six-exchange dream collaboration session.

    ``session_id``, ``owner_id`` and ``created_tick`` are immutable. The
    mutable lifecycle fields advance only through ``world.narrative.dream_session``:
    ``completed_exchanges`` counts successfully delivered validated exchanges
    (never opening text, confirmation, transport failures, validation retries or
    duplicate submissions), ``pending_submission_id`` holds the at-most-one
    outstanding turn, and ``saved_input`` keeps that turn's bounded rendered
    input so a disconnect resumes it. ``state`` is ``open`` or ``ended`` and
    ``outcome`` records how a terminal choice was made (``draft``/``confirmed``).
    ``revision`` is a monotonic row revision for durable change ordering;
    concurrency safety rests on the unique constraints and the pending-turn
    check, not on the row lock.
    """

    objects = DreamSessionQuerySet.as_manager()

    session_id = models.CharField(max_length=64, unique=True, db_index=True)
    owner_id = models.CharField(max_length=255, db_index=True)
    completed_exchanges = models.BigIntegerField(default=0)
    revision = models.BigIntegerField(default=1)
    state = models.CharField(max_length=16, default="open")
    outcome = models.CharField(max_length=16, default="")
    pending_submission_id = models.CharField(max_length=64, default="")
    saved_input = models.TextField(default="")
    draft_id = models.CharField(max_length=128, default="")
    request_key = models.CharField(max_length=160, default="")
    created_tick = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.pk:
            original = DreamSession.objects.get(pk=self.pk)
            if (
                original.session_id != self.session_id
                or original.owner_id != self.owner_id
                or original.created_tick != self.created_tick
            ):
                raise ValueError(
                    "DreamSession identity, owner and creation tick are immutable."
                )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Dream sessions are durable and cannot be deleted.")

    class Meta:
        app_label = "narrative"
        db_table = "narrative_dream_sessions"
        ordering = ["id"]

    def __str__(self) -> str:
        return (
            f"DreamSession({self.session_id}, owner={self.owner_id}, "
            f"{self.completed_exchanges}/{6}, {self.state})"
        )


class ImmutableDreamExchangeQuerySet(models.QuerySet):
    """Delivered dream exchanges are append-only durable evidence."""

    def update(self, *args, **kwargs):
        raise ValueError("Dream exchanges are append-only.")

    def bulk_update(self, *args, **kwargs):
        raise ValueError("Dream exchanges are append-only.")

    def delete(self, *args, **kwargs):
        raise ValueError("Dream exchanges are append-only.")

    def bulk_create(self, objs, **kwargs):
        if kwargs.get("update_conflicts"):
            raise ValueError("Dream exchanges are append-only.")
        return super().bulk_create(objs, **kwargs)


class DreamExchange(models.Model):
    """One successfully delivered validated response, durably counted once.

    ``delivery_id`` is the unique response-delivery identity at the presentation
    acceptance boundary, so replaying the same delivery after a restart returns
    this row instead of creating a second exchange. The unique
    ``(session, exchange_number)`` and ``(session, submission_id)`` constraints
    make the count and the delivered-response identity idempotent even without
    a working row lock; ``response_ref`` references the recoverable delivered
    response record without storing its content.
    """

    objects = ImmutableDreamExchangeQuerySet.as_manager()

    delivery_id = models.CharField(max_length=160, unique=True, db_index=True)
    session = models.ForeignKey(
        DreamSession, on_delete=models.PROTECT, related_name="exchanges"
    )
    owner_id = models.CharField(max_length=255, db_index=True)
    exchange_number = models.BigIntegerField()
    submission_id = models.CharField(max_length=64, db_index=True)
    response_ref = models.CharField(max_length=255, default="")
    tick = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Dream exchanges are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Dream exchanges are append-only.")

    class Meta:
        app_label = "narrative"
        db_table = "narrative_dream_exchanges"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "exchange_number"],
                name="unique_dream_exchange_number",
            ),
            models.UniqueConstraint(
                fields=["session", "submission_id"],
                name="unique_dream_exchange_submission",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"DreamExchange({self.delivery_id}, session={self.session_id}, "
            f"#{self.exchange_number})"
        )


class ImmutableDirectorQuerySet(models.QuerySet):
    """Director decisions and scheduled beats are append-only durable evidence."""

    def update(self, *args, **kwargs):
        raise ValueError("Story director rows are append-only.")

    def bulk_update(self, *args, **kwargs):
        raise ValueError("Story director rows are append-only.")

    def delete(self, *args, **kwargs):
        raise ValueError("Story director rows are durable and cannot be deleted.")

    def bulk_create(self, objs, **kwargs):
        if kwargs.get("update_conflicts"):
            raise ValueError("Story director rows cannot be conflict-updated.")
        return super().bulk_create(objs, **kwargs)


class StoryDirectorDecision(models.Model):
    """One deterministic director decision over an immutable source identity.

    ``decision_id`` is derived from ``(owner, source kind, source ref, source
    revision)``, so repeated processing of the same source after a restart
    returns this row instead of deciding again; the unique source constraint is
    the durable backstop. ``outcome`` records the settlement result
    (``scheduled`` or a concrete rejection code). ``thread_revision`` is the
    revision captured when the decision was prepared for a thread-scoped source;
    for a new story it is the revision of the thread the beat created, and a
    decision that scheduled nothing records ``0`` with the thread it would have
    used (empty for a new story).
    """

    objects = ImmutableDirectorQuerySet.as_manager()

    decision_id = models.CharField(max_length=160, unique=True, db_index=True)
    owner_id = models.CharField(max_length=255, db_index=True)
    source_kind = models.CharField(max_length=16)
    source_ref = models.CharField(max_length=255)
    source_revision = models.BigIntegerField(default=0)
    thread_id = models.CharField(max_length=128, default="", db_index=True)
    thread_revision = models.BigIntegerField(default=0)
    outcome = models.CharField(max_length=32)
    scheduled = models.BooleanField(default=False)
    snapshot_id = models.CharField(max_length=128, default="")
    created_tick = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Story director decisions are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Story director decisions are durable and cannot be deleted.")

    class Meta:
        app_label = "narrative"
        db_table = "narrative_director_decisions"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner_id", "source_kind", "source_ref", "source_revision"],
                name="unique_director_decision_source",
            ),
        ]

    def __str__(self) -> str:
        return f"StoryDirectorDecision({self.decision_id}, outcome={self.outcome})"


class ScheduledBeat(models.Model):
    """One durable beat materialized by a decision, at most one per decision.

    ``arrangement_revision`` is the thread revision the decision captured; the
    unique ``(thread, arrangement_revision)`` constraint is the durable backstop
    that keeps two settlements from establishing conflicting arrangements for
    one thread revision. ``execution_ref`` names the durable record the effect
    produced (narrative event or letter source identity).
    """

    objects = ImmutableDirectorQuerySet.as_manager()

    beat_id = models.CharField(max_length=200, unique=True, db_index=True)
    decision = models.OneToOneField(
        StoryDirectorDecision, on_delete=models.PROTECT, related_name="beat"
    )
    owner_id = models.CharField(max_length=255, db_index=True)
    thread = models.ForeignKey(
        StoryThread, on_delete=models.PROTECT, related_name="scheduled_beats"
    )
    kind = models.CharField(max_length=16)
    effect = models.CharField(max_length=32)
    arrangement_revision = models.BigIntegerField(default=0)
    payload = models.JSONField(default=dict)
    execution_ref = models.CharField(max_length=255, default="")
    created_tick = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Scheduled beats are append-only.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Scheduled beats are durable and cannot be deleted.")

    class Meta:
        app_label = "narrative"
        db_table = "narrative_scheduled_beats"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["thread", "arrangement_revision"],
                name="unique_scheduled_beat_arrangement",
            ),
        ]

    def __str__(self) -> str:
        return f"ScheduledBeat({self.beat_id}, kind={self.kind}, effect={self.effect})"
