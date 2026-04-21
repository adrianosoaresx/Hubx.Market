from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("orders", "0004_orderstatushistory_attribution"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="inventory_reserved_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="variant_sku",
            field=models.CharField(blank=True, max_length=120),
        ),
    ]
