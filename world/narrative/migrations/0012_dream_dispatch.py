from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("narrative", "0011_director_beats"),
    ]

    operations = [
        migrations.CreateModel(
            name="DreamDispatch",
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
                (
                    "dispatch_id",
                    models.CharField(db_index=True, max_length=160, unique=True),
                ),
                ("submission_key", models.CharField(max_length=160)),
                ("owner_id", models.CharField(db_index=True, max_length=255)),
                ("draft_id", models.CharField(default="", max_length=128)),
                ("request_version", models.BigIntegerField(default=0)),
                ("source_key", models.CharField(default="", max_length=255)),
                ("state", models.CharField(default="queued", max_length=24)),
                ("stage", models.CharField(default="", max_length=16)),
                ("execution_token", models.CharField(default="", max_length=64)),
                ("claimed_by", models.CharField(default="", max_length=64)),
                ("story_checkpoint", models.JSONField(blank=True, null=True)),
                ("scene_checkpoint", models.JSONField(blank=True, null=True)),
                ("decision_id", models.CharField(default="", max_length=160)),
                ("thread_id", models.CharField(default="", max_length=128)),
                ("beat_id", models.CharField(default="", max_length=200)),
                ("package_id", models.CharField(default="", max_length=128)),
                ("reason_code", models.CharField(default="", max_length=48)),
                ("attempts", models.IntegerField(default=0)),
                ("tick", models.BigIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "narrative_dream_dispatch",
                "ordering": ["id"],
            },
        ),
        migrations.AddConstraint(
            model_name="dreamdispatch",
            constraint=models.UniqueConstraint(
                fields=("submission_key",),
                name="unique_dream_dispatch_submission",
            ),
        ),
        migrations.AddIndex(
            model_name="dreamdispatch",
            index=models.Index(
                fields=["state", "id"], name="dream_dispatch_state_id"
            ),
        ),
        migrations.AddIndex(
            model_name="dreamdispatch",
            index=models.Index(
                fields=["owner_id", "id"], name="dream_dispatch_owner_id"
            ),
        ),
    ]
