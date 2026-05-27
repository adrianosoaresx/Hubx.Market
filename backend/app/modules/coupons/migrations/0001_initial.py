from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Coupon",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=64)),
                ("name", models.CharField(blank=True, max_length=120)),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Ativo"), ("inactive", "Inativo")],
                        default="active",
                        max_length=16,
                    ),
                ),
                (
                    "discount_type",
                    models.CharField(
                        choices=[("percent", "Percentual"), ("fixed", "Valor fixo")],
                        max_length=16,
                    ),
                ),
                ("discount_value", models.DecimalField(decimal_places=2, max_digits=12)),
                ("starts_at", models.DateTimeField(blank=True, null=True)),
                ("ends_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="coupons",
                        to="tenants.tenant",
                    ),
                ),
            ],
            options={
                "ordering": ("tenant_id", "code"),
            },
        ),
        migrations.AddIndex(
            model_name="coupon",
            index=models.Index(fields=["tenant", "status"], name="coupon_tenant_status_idx"),
        ),
        migrations.AddIndex(
            model_name="coupon",
            index=models.Index(fields=["tenant", "code"], name="coupon_tenant_code_idx"),
        ),
        migrations.AddConstraint(
            model_name="coupon",
            constraint=models.UniqueConstraint(fields=("tenant", "code"), name="coupon_unique_code_per_tenant"),
        ),
    ]
