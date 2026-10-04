from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("narrative", "0007_letter_reply_work"),
    ]

    operations = [
        migrations.AddField(
            model_name="narrativecontextsnapshot",
            name="thread_revisions",
            field=models.JSONField(default=dict),
        ),
        migrations.CreateModel(
            name="StoryThread",
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
                ("thread_id", models.CharField(db_index=True, max_length=128, unique=True)),
                ("origin", models.CharField(max_length=255)),
                ("participants", models.JSONField(default=list)),
                ("visible_to", models.JSONField(default=list)),
                ("factual_summary", models.TextField(blank=True, default="")),
                ("unresolved_questions", models.JSONField(default=list)),
                ("proposed_plans", models.JSONField(default=list)),
                ("commitments", models.JSONField(default=list)),
                ("memory_references", models.JSONField(default=list)),
                ("development_ticks", models.JSONField(default=list)),
                ("state", models.CharField(db_index=True, default="active", max_length=16)),
                ("revision", models.BigIntegerField(default=1)),
                ("created_tick", models.BigIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "narrative_story_threads",
                "ordering": ["id"],
            },
        ),
        migrations.CreateModel(
            name="StoryThreadLink",
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
                ("source_kind", models.CharField(max_length=16)),
                ("source_ref", models.CharField(max_length=255)),
                ("relation", models.CharField(max_length=32)),
                ("provenance", models.JSONField(default=dict)),
                ("created_tick", models.BigIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "thread",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="links",
                        to="narrative.storythread",
                    ),
                ),
            ],
            options={
                "db_table": "narrative_story_thread_links",
                "ordering": ["id"],
            },
        ),
        migrations.CreateModel(
            name="StoryThreadRevision",
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
                ("revision_number", models.IntegerField()),
                ("operation", models.CharField(max_length=32)),
                ("state", models.CharField(max_length=16)),
                ("details", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "thread",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="revisions",
                        to="narrative.storythread",
                    ),
                ),
            ],
            options={
                "db_table": "narrative_story_thread_revisions",
                "ordering": ["thread", "revision_number"],
            },
        ),
        migrations.AddConstraint(
            model_name="storythreadlink",
            constraint=models.UniqueConstraint(
                fields=("thread", "source_kind", "source_ref", "relation"),
                name="unique_story_thread_link",
            ),
        ),
        migrations.AddIndex(
            model_name="storythreadlink",
            index=models.Index(
                fields=["source_kind", "source_ref"], name="thread_link_source_idx"
            ),
        ),
        migrations.AddConstraint(
            model_name="storythreadrevision",
            constraint=models.UniqueConstraint(
                fields=("thread", "revision_number"),
                name="unique_story_thread_revision",
            ),
        ),
    ]
