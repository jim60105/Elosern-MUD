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
