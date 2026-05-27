from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0012_order_payment_failed_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="coupon_code",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="order",
            name="promotion_snapshot",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
