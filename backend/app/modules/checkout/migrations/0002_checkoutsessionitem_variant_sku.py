from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("checkout", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="checkoutsessionitem",
            name="variant_sku",
            field=models.CharField(blank=True, max_length=120),
        ),
    ]
