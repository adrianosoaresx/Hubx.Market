from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0007_order_inventory_finalized_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="inventory_exception_resolved_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="order",
            name="inventory_exception_under_review_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
