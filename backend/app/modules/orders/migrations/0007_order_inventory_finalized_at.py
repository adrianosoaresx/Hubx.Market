from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0006_order_inventory_recovered_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="inventory_finalized_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
