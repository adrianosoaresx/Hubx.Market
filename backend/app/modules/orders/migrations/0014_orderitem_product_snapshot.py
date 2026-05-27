from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0013_order_coupon_snapshot"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderitem",
            name="product_id_snapshot",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="product_slug_snapshot",
            field=models.SlugField(blank=True, max_length=255),
        ),
    ]
