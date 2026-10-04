from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("narrative", "0003_context_snapshots")]

    operations = [
        migrations.CreateModel(
            name="DialogueTurn",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("submission_id", models.CharField(db_index=True, max_length=64)),
                ("kind", models.CharField(max_length=16)),
                ("npc_id", models.CharField(db_index=True, max_length=64)),
                ("player_id", models.CharField(db_index=True, max_length=64)),
                ("speaker", models.CharField(max_length=255)),
                ("speech", models.TextField()),
                ("tick", models.IntegerField(default=0)),
                ("provenance", models.JSONField(default=dict)),
            ],
            options={
                "ordering": ["id"],
                "constraints": [
                    models.UniqueConstraint(fields=("submission_id", "kind"),
                                            name="unique_dialogue_submission_kind"),
                ],
            },
        ),
    ]
