from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ScenePackage",
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
                ("package_id", models.CharField(max_length=128, unique=True)),
                (
                    "source_id",
                    models.CharField(
                        blank=True, max_length=255, null=True, unique=True
                    ),
                ),
                ("owner_id", models.CharField(max_length=255)),
                ("version", models.BigIntegerField(default=1)),
                ("status", models.CharField(default="published", max_length=16)),
                ("payload", models.JSONField()),
                ("created_tick", models.BigIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"app_label": "quests"},
        ),
        migrations.CreateModel(
            name="StoryRoleBinding",
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
                ("role_id", models.CharField(max_length=128)),
                ("npc_id", models.BigIntegerField()),
                ("provenance", models.JSONField(default=dict)),
                ("availability", models.CharField(default="bound", max_length=32)),
                ("updated_tick", models.BigIntegerField(default=0)),
                (
                    "package",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="role_bindings",
                        to="quests.scenepackage",
                    ),
                ),
            ],
            options={"app_label": "quests"},
        ),
        migrations.CreateModel(
            name="SceneEncounterRuntime",
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
                ("scene_id", models.CharField(max_length=128)),
                ("player_id", models.BigIntegerField()),
                ("state", models.CharField(default="pending", max_length=16)),
                ("activation_tick", models.BigIntegerField(blank=True, null=True)),
                ("reason", models.CharField(blank=True, default="", max_length=255)),
                ("updated_tick", models.BigIntegerField(default=0)),
                (
                    "package",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="encounter_runtime",
                        to="quests.scenepackage",
                    ),
                ),
            ],
            options={"app_label": "quests"},
        ),
        migrations.CreateModel(
            name="StoryRoleDialogueRuntime",
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
                ("role_id", models.CharField(max_length=128)),
                ("selected_phase", models.CharField(max_length=128)),
                ("revision", models.BigIntegerField(default=0)),
                ("updated_tick", models.BigIntegerField(default=0)),
                (
                    "package",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dialogue_runtime",
                        to="quests.scenepackage",
                    ),
                ),
            ],
            options={"app_label": "quests"},
        ),
        migrations.CreateModel(
            name="StoryCommissionGrant",
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
                ("role_id", models.CharField(max_length=128)),
                ("npc_id", models.BigIntegerField()),
                ("definition_key", models.CharField(max_length=128)),
                ("issuer_key", models.CharField(max_length=64)),
                ("registered", models.BooleanField(default=False)),
                ("updated_tick", models.BigIntegerField(default=0)),
                (
                    "package",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="commission_grants",
                        to="quests.scenepackage",
                    ),
                ),
            ],
            options={"app_label": "quests"},
        ),
        migrations.AddConstraint(
            model_name="storyrolebinding",
            constraint=models.UniqueConstraint(
                fields=("package", "role_id"), name="quests_unique_role_binding"
            ),
        ),
        migrations.AddConstraint(
            model_name="sceneencounterruntime",
            constraint=models.UniqueConstraint(
                fields=("package", "scene_id", "player_id"),
                name="quests_unique_encounter_identity",
            ),
        ),
        migrations.AddConstraint(
            model_name="storyroledialogueruntime",
            constraint=models.UniqueConstraint(
                fields=("package", "role_id"), name="quests_unique_role_phase"
            ),
        ),
        migrations.AddConstraint(
            model_name="storycommissiongrant",
            constraint=models.UniqueConstraint(
                fields=("package", "role_id", "definition_key"),
                name="quests_unique_commission_grant",
            ),
        ),
    ]
