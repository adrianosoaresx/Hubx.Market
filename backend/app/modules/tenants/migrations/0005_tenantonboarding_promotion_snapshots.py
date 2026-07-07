from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0004_tenant_logo_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenantonboarding",
            name="coupon_code_snapshot",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="tenantonboarding",
            name="coupon_discount_total_snapshot",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="tenantonboarding",
            name="coupon_discount_type_snapshot",
            field=models.CharField(blank=True, max_length=16),
        ),
        migrations.AddField(
            model_name="tenantonboarding",
            name="coupon_discount_value_snapshot",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="tenantonboarding",
            name="effective_monthly_price_snapshot",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="tenantonboarding",
            name="promotion_snapshot",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
