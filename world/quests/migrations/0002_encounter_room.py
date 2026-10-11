from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("quests", "0001_scene_packages"),
    ]

    operations = [
        migrations.AddField(
            model_name="sceneencounterruntime",
            name="room_id",
            field=models.BigIntegerField(blank=True, null=True),
        ),
    ]