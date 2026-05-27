from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("coupons", "0001_initial"),
        ("customers", "0003_customer_execution_flags"),
        ("orders", "0013_order_coupon_snapshot"),
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CouponRedemption",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("coupon_code_snapshot", models.CharField(max_length=64)),
                ("discount_total_snapshot", models.DecimalField(decimal_places=2, max_digits=12)),
                ("promotion_snapshot", models.JSONField(blank=True, default=dict)),
                (
                    "status",
                    models.CharField(
                        choices=[("applied", "Aplicado"), ("reversed", "Revertido")],
                        default="applied",
                        max_length=16,
                    ),
                ),
                ("source_type", models.CharField(blank=True, max_length=64)),
                ("source_label", models.CharField(blank=True, max_length=120)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("reversed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "coupon",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="redemptions",
                        to="coupons.coupon",
                    ),
                ),
                (
                    "customer",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="coupon_redemptions",
                        to="customers.customer",
                    ),
                ),
                (
                    "order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="coupon_redemptions",
                        to="orders.order",
                    ),
                ),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="coupon_redemptions",
                        to="tenants.tenant",
                    ),
                ),
            ],
            options={
                "ordering": ("tenant_id", "-created_at", "-id"),
            },
        ),
        migrations.AddIndex(
            model_name="couponredemption",
            index=models.Index(fields=["tenant", "coupon_code_snapshot"], name="coupon_red_tenant_code_idx"),
        ),
        migrations.AddIndex(
            model_name="couponredemption",
            index=models.Index(fields=["tenant", "status"], name="coupon_red_tenant_status_idx"),
        ),
        migrations.AddIndex(
            model_name="couponredemption",
            index=models.Index(fields=["coupon", "created_at"], name="coupon_red_coupon_time_idx"),
        ),
        migrations.AddConstraint(
            model_name="couponredemption",
            constraint=models.UniqueConstraint(
                fields=("tenant", "order", "coupon_code_snapshot"),
                name="coupon_redemption_unique_order_code",
            ),
        ),
    ]
