from django.db import migrations, models


class Migration(migrations.Migration):
    """Declare the escort outcome and per-event transition tables (escort §7).

    Schema declaration only: no data migration, no backfill and no reset is
    executed. The two unique constraints are the reason these records are
    database rows rather than another ``db`` list — one owner can never hold two
    competing resolution rows for one declared group, and one stable event
    source can never advance a record twice across a pre/post-follow pair or a
    committed reload.
    """

    dependencies = [
        ("quests", "0002_encounter_room"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExclusiveOutcomeGroup",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("owner_id", models.BigIntegerField()),
                ("package_id", models.CharField(max_length=128)),
                ("group_id", models.CharField(max_length=128)),
                ("resolved", models.BooleanField(default=False)),
                (
                    "resolution_source",
                    models.CharField(blank=True, default="", max_length=200),
                ),
                (
                    "winner_quest_id",
                    models.CharField(blank=True, default="", max_length=128),
                ),
                ("no_commission", models.BooleanField(default=False)),
                ("next_sequence", models.PositiveIntegerField(default=1)),
                ("updated_tick", models.BigIntegerField(default=0)),
            ],
            options={
                "app_label": "quests",
            },
        ),
        migrations.AddConstraint(
            model_name="exclusiveoutcomegroup",
            constraint=models.UniqueConstraint(
                fields=("owner_id", "package_id", "group_id"),
                name="quests_unique_outcome_group",
            ),
        ),
        migrations.CreateModel(
            name="EscortEventTransition",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("owner_id", models.BigIntegerField()),
                ("record_id", models.CharField(max_length=128)),
                ("source_key", models.CharField(max_length=200)),
                ("consumed_tick", models.BigIntegerField(default=0)),
            ],
            options={
                "app_label": "quests",
            },
        ),
        migrations.AddConstraint(
            model_name="escorteventtransition",
            constraint=models.UniqueConstraint(
                fields=("owner_id", "record_id", "source_key"),
                name="quests_unique_escort_transition",
            ),
        ),
    ]