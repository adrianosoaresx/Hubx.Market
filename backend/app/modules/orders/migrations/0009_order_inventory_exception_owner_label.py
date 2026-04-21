from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0008_order_inventory_exception_markers"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="inventory_exception_owner_label",
            field=models.CharField(blank=True, max_length=120),
        ),
    ]
