from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SubscriptionPlan",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.SlugField(max_length=80, unique=True)),
                ("name", models.CharField(max_length=120)),
                ("description", models.TextField(blank=True)),
                ("monthly_price", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("currency_code", models.CharField(default="BRL", max_length=3)),
                ("included_api_quota", models.PositiveIntegerField(default=0)),
                ("status", models.CharField(choices=[("active", "Ativo"), ("archived", "Arquivado")], default="active", max_length=16)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ("monthly_price", "code"),
            },
        ),
        migrations.CreateModel(
            name="TenantSubscription",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("trialing", "Trial"), ("active", "Ativa"), ("past_due", "Em atraso"), ("suspended", "Suspensa"), ("canceled", "Cancelada")], default="trialing", max_length=16)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("trial_ends_at", models.DateTimeField(blank=True, null=True)),
                ("current_period_ends_at", models.DateTimeField(blank=True, null=True)),
                ("canceled_at", models.DateTimeField(blank=True, null=True)),
                ("external_reference", models.CharField(blank=True, max_length=180)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="tenant_subscriptions", to="subscriptions.subscriptionplan")),
                ("tenant", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="subscription", to="tenants.tenant")),
            ],
            options={
                "ordering": ("tenant_id",),
            },
        ),
        migrations.AddConstraint(
            model_name="subscriptionplan",
            constraint=models.CheckConstraint(check=models.Q(("status__in", ("active", "archived"))), name="subscription_plan_status_valid"),
        ),
        migrations.AddConstraint(
            model_name="subscriptionplan",
            constraint=models.CheckConstraint(check=models.Q(("monthly_price__gte", 0)), name="subscription_plan_price_non_negative"),
        ),
        migrations.AddIndex(
            model_name="subscriptionplan",
            index=models.Index(fields=["status", "code"], name="sub_plan_status_code_idx"),
        ),
        migrations.AddConstraint(
            model_name="tenantsubscription",
            constraint=models.CheckConstraint(check=models.Q(("status__in", ("trialing", "active", "past_due", "suspended", "canceled"))), name="tenant_subscription_status_valid"),
        ),
        migrations.AddIndex(
            model_name="tenantsubscription",
            index=models.Index(fields=["status", "current_period_ends_at"], name="tenant_sub_status_period_idx"),
        ),
    ]
