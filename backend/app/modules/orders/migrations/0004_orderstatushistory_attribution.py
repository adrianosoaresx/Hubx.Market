from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0003_orderstatushistory"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderstatushistory",
            name="actor_label",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="orderstatushistory",
            name="source_label",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="orderstatushistory",
            name="source_type",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
    ]
