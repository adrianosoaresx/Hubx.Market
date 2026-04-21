from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0005_order_inventory_reserved_and_variant_sku"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="inventory_recovered_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
