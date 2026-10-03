from django.db import models


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
