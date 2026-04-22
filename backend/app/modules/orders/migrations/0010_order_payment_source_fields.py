from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0009_order_inventory_exception_owner_label"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="payment_reference",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="order",
            name="payment_source_label",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="order",
            name="payment_source_type",
            field=models.CharField(blank=True, max_length=32),
        ),
    ]
