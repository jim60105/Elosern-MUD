from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("narrative", "0010_dream_sessions"),
    ]

    operations = [
        migrations.CreateModel(
            name="StoryDirectorDecision",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("decision_id", models.CharField(db_index=True, max_length=160, unique=True)),
                ("owner_id", models.CharField(db_index=True, max_length=255)),
                ("source_kind", models.CharField(max_length=16)),
                ("source_ref", models.CharField(max_length=255)),
                ("source_revision", models.BigIntegerField(default=0)),
                ("thread_id", models.CharField(db_index=True, default="", max_length=128)),
                ("thread_revision", models.BigIntegerField(default=0)),
                ("outcome", models.CharField(max_length=32)),
                ("scheduled", models.BooleanField(default=False)),
                ("snapshot_id", models.CharField(default="", max_length=128)),
                ("created_tick", models.BigIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": "narrative_director_decisions",
                "ordering": ["id"],
            },
        ),
        migrations.CreateModel(
            name="ScheduledBeat",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("beat_id", models.CharField(db_index=True, max_length=200, unique=True)),
                ("owner_id", models.CharField(db_index=True, max_length=255)),
                ("kind", models.CharField(max_length=16)),
                ("effect", models.CharField(max_length=32)),
                ("arrangement_revision", models.BigIntegerField(default=0)),
                ("payload", models.JSONField(default=dict)),
                ("execution_ref", models.CharField(default="", max_length=255)),
                ("created_tick", models.BigIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "decision",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="beat",
                        to="narrative.storydirectordecision",
                    ),
                ),
                (
                    "thread",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="scheduled_beats",
                        to="narrative.storythread",
                    ),
                ),
            ],
            options={
                "db_table": "narrative_scheduled_beats",
                "ordering": ["id"],
            },
        ),
        migrations.AddConstraint(
            model_name="storydirectordecision",
            constraint=models.UniqueConstraint(
                fields=("owner_id", "source_kind", "source_ref", "source_revision"),
                name="unique_director_decision_source",
            ),
        ),
        migrations.AddConstraint(
            model_name="scheduledbeat",
            constraint=models.UniqueConstraint(
                fields=("thread", "arrangement_revision"),
                name="unique_scheduled_beat_arrangement",
            ),
        ),
    ]
