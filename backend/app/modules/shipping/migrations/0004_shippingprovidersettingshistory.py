import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shipping", "0003_shippingprovidersettings"),
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ShippingProviderSettingsHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(max_length=64)),
                ("source_type", models.CharField(blank=True, max_length=64)),
                ("source_label", models.CharField(blank=True, max_length=120)),
                ("actor_label", models.CharField(blank=True, max_length=120)),
                ("title", models.CharField(max_length=160)),
                ("description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "settings",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="history_entries",
                        to="shipping.shippingprovidersettings",
                    ),
                ),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="shipping_provider_settings_history",
                        to="tenants.tenant",
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at", "-id"),
                "indexes": [
                    models.Index(fields=["tenant", "event_type"], name="ship_provider_hist_event_idx"),
                    models.Index(fields=["settings", "-created_at"], name="ship_provider_hist_time_idx"),
                ],
            },
        ),
    ]
