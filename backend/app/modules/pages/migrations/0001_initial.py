from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Page",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=160)),
                ("title", models.CharField(max_length=180)),
                ("body", models.TextField(blank=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("draft", "Rascunho"), ("published", "Publicado")],
                        default="draft",
                        max_length=16,
                    ),
                ),
                ("seo_title", models.CharField(blank=True, max_length=180)),
                ("seo_description", models.CharField(blank=True, max_length=300)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "tenant",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pages", to="tenants.tenant"),
                ),
            ],
            options={
                "ordering": ("tenant_id", "title", "id"),
            },
        ),
        migrations.AddConstraint(
            model_name="page",
            constraint=models.UniqueConstraint(fields=("tenant", "slug"), name="page_unique_slug_per_tenant"),
        ),
        migrations.AddConstraint(
            model_name="page",
            constraint=models.CheckConstraint(
                check=models.Q(("status__in", ("draft", "published"))),
                name="page_status_valid",
            ),
        ),
        migrations.AddIndex(
            model_name="page",
            index=models.Index(fields=("tenant", "status", "slug"), name="page_tenant_stat_slug_idx"),
        ),
        migrations.AddIndex(
            model_name="page",
            index=models.Index(fields=("tenant", "updated_at"), name="page_tenant_updated_idx"),
        ),
    ]
