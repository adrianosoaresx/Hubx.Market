from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("accounts", "0005_ownermfarecoverycode"),
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ApiKey",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("prefix", models.CharField(max_length=24, unique=True)),
                ("key_hash", models.CharField(max_length=255)),
                ("scopes", models.JSONField(blank=True, default=list)),
                ("status", models.CharField(choices=[("active", "Ativa"), ("revoked", "Revogada")], default="active", max_length=16)),
                ("created_by_label", models.CharField(blank=True, max_length=180)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("last_used_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_by_label", models.CharField(blank=True, max_length=180)),
                ("owner", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="api_keys", to="accounts.owneruser")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="api_keys", to="tenants.tenant")),
            ],
            options={
                "ordering": ("tenant_id", "-created_at", "-id"),
            },
        ),
        migrations.AddConstraint(
            model_name="apikey",
            constraint=models.CheckConstraint(check=models.Q(("status__in", ("active", "revoked"))), name="api_key_status_valid"),
        ),
        migrations.AddIndex(
            model_name="apikey",
            index=models.Index(fields=["tenant", "status"], name="api_key_tenant_status_idx"),
        ),
        migrations.AddIndex(
            model_name="apikey",
            index=models.Index(fields=["tenant", "created_at"], name="api_key_tenant_created_idx"),
        ),
        migrations.AddIndex(
            model_name="apikey",
            index=models.Index(fields=["prefix"], name="api_key_prefix_idx"),
        ),
    ]
