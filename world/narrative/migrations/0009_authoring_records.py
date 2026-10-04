from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("narrative", "0008_story_threads"),
    ]

    operations = [
        migrations.CreateModel(
            name="AuthoringDraft",
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
                ("draft_id", models.CharField(db_index=True, max_length=128, unique=True)),
                ("owner_id", models.CharField(db_index=True, max_length=255)),
                ("direction", models.JSONField(default=dict)),
                ("sources", models.JSONField(default=list)),
                ("revision", models.BigIntegerField(default=1)),
                ("confirmed_revision", models.BigIntegerField(null=True)),
                ("created_tick", models.BigIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "narrative_authoring_drafts",
                "ordering": ["id"],
            },
        ),
        migrations.CreateModel(
            name="CreativeRequest",
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
                ("submission_key", models.CharField(db_index=True, max_length=160, unique=True)),
                ("owner_id", models.CharField(db_index=True, max_length=255)),
                ("version", models.BigIntegerField()),
                ("direction", models.JSONField(default=dict)),
                ("sources", models.JSONField(default=list)),
                ("validation_status", models.CharField(default="valid", max_length=16)),
                ("submitted_tick", models.BigIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "draft",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="requests",
                        to="narrative.authoringdraft",
                    ),
                ),
            ],
            options={
                "db_table": "narrative_authoring_requests",
                "ordering": ["id"],
            },
        ),
        migrations.AddConstraint(
            model_name="creativerequest",
            constraint=models.UniqueConstraint(
                fields=("draft", "version"),
                name="unique_creative_request_version",
            ),
        ),
    ]
