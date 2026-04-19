from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("customers", "0002_customeraddress"),
    ]

    operations = [
        migrations.AddField(
            model_name="customer",
            name="marked_as_priority",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="customer",
            name="marked_for_followup",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="customer",
            name="marked_for_reengagement",
            field=models.BooleanField(default=False),
        ),
    ]
