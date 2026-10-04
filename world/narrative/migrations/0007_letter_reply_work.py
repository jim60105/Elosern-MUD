from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("narrative", "0006_dialogue_epochs")]

    operations = [
        migrations.AddField(
            model_name="lettersend", name="source_snapshot_id",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
        migrations.CreateModel(
            name="LetterReplyWork",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("snapshot_id", models.CharField(blank=True, default="", max_length=128)),
                ("outgoing_source_id", models.CharField(blank=True, default="", max_length=128)),
                ("status", models.CharField(default="pending", max_length=16)),
                ("letter", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to="narrative.lettersend")),
            ],
        ),
    ]
