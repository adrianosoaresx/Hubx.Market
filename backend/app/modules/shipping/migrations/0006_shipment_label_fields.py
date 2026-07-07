from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("shipping", "0005_shipmentstatushistory_provider_http_status_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="shipment",
            name="label_status",
            field=models.CharField(
                choices=[("missing", "Sem etiqueta"), ("generated", "Gerada")],
                default="missing",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="shipment",
            name="label_code",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="shipment",
            name="label_url",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="shipment",
            name="label_created_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name="shipment",
            index=models.Index(fields=("tenant", "label_code"), name="ship_tenant_label_idx"),
        ),
    ]
