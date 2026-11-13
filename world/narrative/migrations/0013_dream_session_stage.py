from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("narrative", "0012_dream_dispatch"),
    ]

    operations = [
        migrations.AddField(
            model_name="dreamsession",
            name="stage",
            field=models.CharField(default="conversing", max_length=16),
        ),
    ]
