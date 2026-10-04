from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("narrative", "0009_authoring_records"),
    ]

    operations = [
        migrations.CreateModel(
            name="DreamSession",
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
                ("session_id", models.CharField(db_index=True, max_length=64, unique=True)),
                ("owner_id", models.CharField(db_index=True, max_length=255)),
                ("completed_exchanges", models.BigIntegerField(default=0)),
                ("revision", models.BigIntegerField(default=1)),
                ("state", models.CharField(default="open", max_length=16)),
                ("outcome", models.CharField(default="", max_length=16)),
                ("pending_submission_id", models.CharField(default="", max_length=64)),
                ("saved_input", models.TextField(default="")),
                ("draft_id", models.CharField(default="", max_length=128)),
                ("request_key", models.CharField(default="", max_length=160)),
                ("created_tick", models.BigIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "narrative_dream_sessions",
                "ordering": ["id"],
            },
        ),
        migrations.CreateModel(
            name="DreamExchange",
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
                ("delivery_id", models.CharField(db_index=True, max_length=160, unique=True)),
                ("owner_id", models.CharField(db_index=True, max_length=255)),
                ("exchange_number", models.BigIntegerField()),
                ("submission_id", models.CharField(db_index=True, max_length=64)),
                ("response_ref", models.CharField(default="", max_length=255)),
                ("tick", models.BigIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="exchanges",
                        to="narrative.dreamsession",
                    ),
                ),
            ],
            options={
                "db_table": "narrative_dream_exchanges",
                "ordering": ["id"],
            },
        ),
        migrations.AddConstraint(
            model_name="dreamexchange",
            constraint=models.UniqueConstraint(
                fields=("session", "exchange_number"),
                name="unique_dream_exchange_number",
            ),
        ),
        migrations.AddConstraint(
            model_name="dreamexchange",
            constraint=models.UniqueConstraint(
                fields=("session", "submission_id"),
                name="unique_dream_exchange_submission",
            ),
        ),
    ]
