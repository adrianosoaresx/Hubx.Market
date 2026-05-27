from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="NewsletterSubscriber",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(max_length=254)),
                ("name", models.CharField(blank=True, max_length=120)),
                (
                    "status",
                    models.CharField(
                        choices=[("subscribed", "Inscrito"), ("unsubscribed", "Descadastrado")],
                        default="subscribed",
                        max_length=20,
                    ),
                ),
                ("source", models.CharField(blank=True, max_length=80)),
                ("consent_label", models.CharField(blank=True, max_length=180)),
                ("consented_at", models.DateTimeField(blank=True, null=True)),
                ("unsubscribed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="newsletter_subscribers",
                        to="tenants.tenant",
                    ),
                ),
            ],
            options={
                "ordering": ("tenant_id", "-updated_at", "email"),
            },
        ),
        migrations.AddConstraint(
            model_name="newslettersubscriber",
            constraint=models.UniqueConstraint(fields=("tenant", "email"), name="newsletter_unique_email_per_tenant"),
        ),
        migrations.AddConstraint(
            model_name="newslettersubscriber",
            constraint=models.CheckConstraint(
                check=models.Q(("status__in", ("subscribed", "unsubscribed"))),
                name="newsletter_status_valid",
            ),
        ),
        migrations.AddIndex(
            model_name="newslettersubscriber",
            index=models.Index(fields=("tenant", "status", "updated_at"), name="newsletter_tenant_status_idx"),
        ),
        migrations.AddIndex(
            model_name="newslettersubscriber",
            index=models.Index(fields=("tenant", "email"), name="newsletter_tenant_email_idx"),
        ),
    ]
