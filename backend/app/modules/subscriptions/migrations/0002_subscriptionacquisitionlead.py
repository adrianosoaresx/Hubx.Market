from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("subscriptions", "0001_initial"),
        ("tenants", "0002_tenantonboarding"),
    ]

    operations = [
        migrations.CreateModel(
            name="SubscriptionAcquisitionLead",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("new", "Novo"), ("converted", "Convertido"), ("discarded", "Descartado")], default="new", max_length=16)),
                ("plan_code_snapshot", models.SlugField(max_length=80)),
                ("plan_name_snapshot", models.CharField(max_length=120)),
                ("plan_monthly_price_snapshot", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("plan_currency_snapshot", models.CharField(default="BRL", max_length=3)),
                ("store_name", models.CharField(max_length=150)),
                ("desired_subdomain", models.SlugField(max_length=63)),
                ("contact_name", models.CharField(blank=True, max_length=150)),
                ("contact_email", models.EmailField(max_length=254)),
                ("contact_phone", models.CharField(blank=True, max_length=40)),
                ("message", models.TextField(blank=True)),
                ("source", models.CharField(default="public-plans", max_length=80)),
                ("converted_at", models.DateTimeField(blank=True, null=True)),
                ("discarded_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "onboarding",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="subscription_acquisition_lead",
                        to="tenants.tenantonboarding",
                    ),
                ),
                (
                    "plan",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="acquisition_leads",
                        to="subscriptions.subscriptionplan",
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at", "-id"),
            },
        ),
        migrations.AddConstraint(
            model_name="subscriptionacquisitionlead",
            constraint=models.CheckConstraint(check=models.Q(("status__in", ("new", "converted", "discarded"))), name="sub_acq_lead_status_valid"),
        ),
        migrations.AddIndex(
            model_name="subscriptionacquisitionlead",
            index=models.Index(fields=["status", "-created_at"], name="sub_acq_status_created_idx"),
        ),
        migrations.AddIndex(
            model_name="subscriptionacquisitionlead",
            index=models.Index(fields=["desired_subdomain"], name="sub_acq_subdomain_idx"),
        ),
        migrations.AddIndex(
            model_name="subscriptionacquisitionlead",
            index=models.Index(fields=["contact_email"], name="sub_acq_contact_email_idx"),
        ),
    ]
