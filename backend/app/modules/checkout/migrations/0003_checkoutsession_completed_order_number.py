from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("checkout", "0002_checkoutsessionitem_variant_sku"),
    ]

    operations = [
        migrations.AddField(
            model_name="checkoutsession",
            name="completed_order_number",
            field=models.CharField(blank=True, max_length=32),
        ),
    ]
