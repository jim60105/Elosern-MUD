from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("narrative", "0005_lettersend_letterstate")]
    operations = [
        migrations.CreateModel(name="DialogueEpoch", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("npc_id", models.CharField(max_length=64)),
            ("player_id", models.CharField(max_length=64)),
            ("sequence", models.PositiveIntegerField()),
            ("version", models.CharField(max_length=64)),
            ("reason", models.CharField(max_length=32)),
            ("start_turn_id", models.BigIntegerField(default=0)),
            ("summary", models.TextField(default="")),
            ("generation_id", models.CharField(max_length=64, unique=True)),
            ("source_refs", models.JSONField(default=list)),
            ("snapshot_id", models.CharField(default="", max_length=128)),
        ], options={"constraints": [models.UniqueConstraint(fields=("npc_id", "player_id", "sequence"), name="unique_dialogue_pair_epoch")]}),
        migrations.CreateModel(name="DialogueFrame", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("identity", models.CharField(max_length=64)),
            ("content", models.TextField()),
            ("tick", models.IntegerField(default=0)),
            ("sources", models.JSONField(default=list)),
            ("epoch", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="narrative.dialogueepoch")),
        ], options={"constraints": [models.UniqueConstraint(fields=("epoch", "identity"), name="unique_dialogue_epoch_frame")]}),
    ]
