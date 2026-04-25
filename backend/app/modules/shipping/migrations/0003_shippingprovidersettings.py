from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("shipping", "0002_shipmentstatushistory"),
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ShippingProviderSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider_name", models.CharField(default="manual", max_length=80)),
                ("base_url", models.URLField(blank=True)),
                ("api_token", models.CharField(blank=True, max_length=255)),
                ("timeout_seconds", models.DecimalField(decimal_places=2, default=3, max_digits=4)),
                ("is_active", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "tenant",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="shipping_provider_settings",
                        to="tenants.tenant",
                    ),
                ),
            ],
            options={
                "ordering": ("tenant_id",),
                "indexes": [
                    models.Index(fields=["tenant", "is_active"], name="ship_provider_active_idx"),
                ],
            },
        ),
    ]
