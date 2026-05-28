from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="TenantOnboarding",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("draft", "Rascunho"), ("in_progress", "Em andamento"), ("ready_for_review", "Pronto para revisão"), ("completed", "Concluído"), ("blocked", "Bloqueado")], default="draft", max_length=24)),
                ("store_name", models.CharField(blank=True, max_length=150)),
                ("store_slug", models.SlugField(blank=True, max_length=150)),
                ("store_subdomain", models.SlugField(blank=True, max_length=63)),
                ("custom_domain", models.CharField(blank=True, max_length=255)),
                ("plan_code", models.SlugField(blank=True, max_length=80)),
                ("owner_email", models.EmailField(blank=True, max_length=254)),
                ("owner_name", models.CharField(blank=True, max_length=150)),
                ("owner_role", models.CharField(blank=True, default="owner", max_length=64)),
                ("store_display_name", models.CharField(blank=True, max_length=150)),
                ("primary_color", models.CharField(blank=True, max_length=7)),
                ("blockers", models.JSONField(blank=True, default=list)),
                ("created_by_label", models.CharField(blank=True, max_length=180)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="onboarding", to="tenants.tenant")),
            ],
            options={
                "verbose_name": "Tenant onboarding",
                "verbose_name_plural": "Tenant onboardings",
                "ordering": ("-updated_at", "-id"),
            },
        ),
        migrations.AddIndex(
            model_name="tenantonboarding",
            index=models.Index(fields=["status", "updated_at"], name="tenant_onboarding_status_idx"),
        ),
        migrations.AddIndex(
            model_name="tenantonboarding",
            index=models.Index(fields=["store_slug"], name="tenant_onboarding_slug_idx"),
        ),
    ]
