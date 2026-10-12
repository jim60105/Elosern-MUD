from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("quests", "0003_escort_outcomes"),
    ]

    operations = [
        migrations.AlterField(
            model_name="scenepackage",
            name="owner_id",
            field=models.CharField(db_index=True, max_length=255),
        ),
    ]
