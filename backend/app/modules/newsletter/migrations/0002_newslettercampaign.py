from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("newsletter", "0001_initial"),
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="NewsletterCampaign",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=150)),
                ("subject", models.CharField(max_length=180)),
                ("body_text", models.TextField()),
                (
                    "status",
                    models.CharField(
                        choices=[("draft", "Rascunho"), ("sent", "Enviada"), ("failed", "Falhou")],
                        default="draft",
                        max_length=16,
                    ),
                ),
                ("segment_status", models.CharField(default="subscribed", max_length=24)),
                ("recipient_count", models.PositiveIntegerField(default=0)),
                ("created_by_label", models.CharField(blank=True, max_length=180)),
                ("sent_by_label", models.CharField(blank=True, max_length=180)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("last_error", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="newsletter_campaigns",
                        to="tenants.tenant",
                    ),
                ),
            ],
            options={
                "ordering": ("tenant_id", "-created_at", "-id"),
            },
        ),
        migrations.AddConstraint(
            model_name="newslettercampaign",
            constraint=models.CheckConstraint(
                check=models.Q(("status__in", ("draft", "sent", "failed"))),
                name="newsletter_campaign_status_valid",
            ),
        ),
        migrations.AddConstraint(
            model_name="newslettercampaign",
            constraint=models.CheckConstraint(
                check=models.Q(("segment_status__in", ("subscribed",))),
                name="newsletter_campaign_segment_status_valid",
            ),
        ),
        migrations.AddIndex(
            model_name="newslettercampaign",
            index=models.Index(fields=("tenant", "status", "created_at"), name="newsletter_campaign_status_idx"),
        ),
        migrations.AddIndex(
            model_name="newslettercampaign",
            index=models.Index(fields=("tenant", "sent_at"), name="newsletter_campaign_sent_idx"),
        ),
    ]
