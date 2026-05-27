from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("checkout", "0004_checkoutrecoveryevent"),
    ]

    operations = [
        migrations.AddField(
            model_name="checkoutsession",
            name="coupon_code",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="checkoutsession",
            name="promotion_snapshot",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
