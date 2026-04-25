import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("shipping", "0001_initial"),
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ShipmentStatusHistory",
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
                    "shipment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="history_entries",
                        to="shipping.shipment",
                    ),
                ),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="shipment_status_history",
                        to="tenants.tenant",
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at", "-id"),
                "indexes": [
                    models.Index(fields=["tenant", "event_type"], name="ship_hist_tenant_event_idx"),
                    models.Index(fields=["shipment", "-created_at"], name="ship_hist_shipment_time_idx"),
                ],
            },
        ),
    ]
