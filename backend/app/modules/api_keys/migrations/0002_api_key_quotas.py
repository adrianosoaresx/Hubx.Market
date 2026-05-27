from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("api_keys", "0001_initial"),
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ApiKeyQuota",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("endpoint", models.CharField(max_length=120)),
                ("scope", models.CharField(default="read:catalog", max_length=80)),
                ("window_seconds", models.PositiveIntegerField(default=86400)),
                ("limit", models.PositiveIntegerField(default=10000)),
                ("status", models.CharField(choices=[("active", "Ativa"), ("disabled", "Desativada")], default="active", max_length=16)),
                ("created_by_label", models.CharField(blank=True, max_length=180)),
                ("updated_by_label", models.CharField(blank=True, max_length=180)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("api_key", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="quotas", to="api_keys.apikey")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="api_key_quotas", to="tenants.tenant")),
            ],
            options={
                "ordering": ("tenant_id", "api_key_id", "endpoint"),
            },
        ),
        migrations.CreateModel(
            name="ApiKeyQuotaUsage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("endpoint", models.CharField(max_length=120)),
                ("window_start", models.DateTimeField()),
                ("window_seconds", models.PositiveIntegerField(default=86400)),
                ("count", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("api_key", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="quota_usages", to="api_keys.apikey")),
                ("quota", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="usages", to="api_keys.apikeyquota")),
                ("tenant", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="api_key_quota_usages", to="tenants.tenant")),
            ],
            options={
                "ordering": ("tenant_id", "api_key_id", "endpoint", "-window_start"),
            },
        ),
        migrations.AddConstraint(
            model_name="apikeyquota",
            constraint=models.CheckConstraint(check=models.Q(("status__in", ("active", "disabled"))), name="api_key_quota_status_valid"),
        ),
        migrations.AddConstraint(
            model_name="apikeyquota",
            constraint=models.CheckConstraint(check=models.Q(("limit__gt", 0)), name="api_key_quota_limit_positive"),
        ),
        migrations.AddConstraint(
            model_name="apikeyquota",
            constraint=models.CheckConstraint(check=models.Q(("window_seconds__gt", 0)), name="api_key_quota_window_positive"),
        ),
        migrations.AddConstraint(
            model_name="apikeyquota",
            constraint=models.UniqueConstraint(fields=("tenant", "api_key", "endpoint"), name="api_key_quota_tenant_key_endpoint_unique"),
        ),
        migrations.AddIndex(
            model_name="apikeyquota",
            index=models.Index(fields=["tenant", "status"], name="api_key_quota_tenant_stat_idx"),
        ),
        migrations.AddIndex(
            model_name="apikeyquota",
            index=models.Index(fields=["tenant", "api_key", "endpoint"], name="api_key_quota_lookup_idx"),
        ),
        migrations.AddConstraint(
            model_name="apikeyquotausage",
            constraint=models.CheckConstraint(check=models.Q(("count__gte", 0)), name="api_key_quota_usage_count_non_negative"),
        ),
        migrations.AddConstraint(
            model_name="apikeyquotausage",
            constraint=models.CheckConstraint(check=models.Q(("window_seconds__gt", 0)), name="api_key_quota_usage_window_positive"),
        ),
        migrations.AddConstraint(
            model_name="apikeyquotausage",
            constraint=models.UniqueConstraint(fields=("tenant", "api_key", "endpoint", "window_start", "window_seconds"), name="api_key_quota_usage_window_unique"),
        ),
        migrations.AddIndex(
            model_name="apikeyquotausage",
            index=models.Index(fields=["tenant", "api_key", "endpoint", "window_start"], name="api_key_quota_usage_lookup_idx"),
        ),
        migrations.AddIndex(
            model_name="apikeyquotausage",
            index=models.Index(fields=["quota", "window_start"], name="api_key_quota_usage_quota_idx"),
        ),
    ]
