from django.db import migrations, models
import django.db.models.deletion


def fill_existing_effective_prices(apps, schema_editor):
    TenantSubscription = apps.get_model("subscriptions", "TenantSubscription")
    SubscriptionAcquisitionLead = apps.get_model("subscriptions", "SubscriptionAcquisitionLead")

    for subscription in TenantSubscription.objects.select_related("plan").all():
        if not subscription.effective_monthly_price_snapshot:
            subscription.effective_monthly_price_snapshot = subscription.plan.monthly_price
            subscription.save(update_fields=["effective_monthly_price_snapshot"])

    for lead in SubscriptionAcquisitionLead.objects.all():
        if not lead.effective_monthly_price_snapshot:
            lead.effective_monthly_price_snapshot = lead.plan_monthly_price_snapshot
            lead.save(update_fields=["effective_monthly_price_snapshot"])


class Migration(migrations.Migration):
    dependencies = [
        ("subscriptions", "0004_tenantsubscription_billing_checkout_url_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="SubscriptionCoupon",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=64, unique=True)),
                ("name", models.CharField(blank=True, max_length=120)),
                ("status", models.CharField(choices=[("active", "Ativo"), ("inactive", "Inativo")], default="active", max_length=16)),
                ("discount_type", models.CharField(choices=[("percent", "Percentual"), ("fixed", "Valor fixo")], max_length=16)),
                ("discount_value", models.DecimalField(decimal_places=2, max_digits=12)),
                ("starts_at", models.DateTimeField(blank=True, null=True)),
                ("ends_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "plan",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="subscription_coupons",
                        to="subscriptions.subscriptionplan",
                    ),
                ),
            ],
            options={
                "ordering": ("code",),
            },
        ),
        migrations.AddField(
            model_name="subscriptionacquisitionlead",
            name="coupon_code_snapshot",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="subscriptionacquisitionlead",
            name="coupon_discount_total_snapshot",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="subscriptionacquisitionlead",
            name="coupon_discount_type_snapshot",
            field=models.CharField(blank=True, max_length=16),
        ),
        migrations.AddField(
            model_name="subscriptionacquisitionlead",
            name="coupon_discount_value_snapshot",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="subscriptionacquisitionlead",
            name="effective_monthly_price_snapshot",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="subscriptionacquisitionlead",
            name="promotion_snapshot",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="tenantsubscription",
            name="coupon_code_snapshot",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="tenantsubscription",
            name="coupon_discount_total_snapshot",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="tenantsubscription",
            name="coupon_discount_type_snapshot",
            field=models.CharField(blank=True, max_length=16),
        ),
        migrations.AddField(
            model_name="tenantsubscription",
            name="coupon_discount_value_snapshot",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="tenantsubscription",
            name="effective_monthly_price_snapshot",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="tenantsubscription",
            name="promotion_snapshot",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddConstraint(
            model_name="subscriptioncoupon",
            constraint=models.CheckConstraint(check=models.Q(("status__in", ("active", "inactive"))), name="subscription_coupon_status_valid"),
        ),
        migrations.AddConstraint(
            model_name="subscriptioncoupon",
            constraint=models.CheckConstraint(check=models.Q(("discount_type__in", ("percent", "fixed"))), name="subscription_coupon_discount_type_valid"),
        ),
        migrations.AddConstraint(
            model_name="subscriptioncoupon",
            constraint=models.CheckConstraint(check=models.Q(("discount_value__gt", 0)), name="subscription_coupon_discount_positive"),
        ),
        migrations.AddIndex(
            model_name="subscriptioncoupon",
            index=models.Index(fields=["status", "code"], name="sub_coupon_status_code_idx"),
        ),
        migrations.AddIndex(
            model_name="subscriptioncoupon",
            index=models.Index(fields=["plan", "status"], name="sub_coupon_plan_status_idx"),
        ),
        migrations.RunPython(fill_existing_effective_prices, migrations.RunPython.noop),
    ]
