from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Product",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("brand_name", models.CharField(blank=True, max_length=120)),
                ("category_label", models.CharField(blank=True, max_length=120)),
                ("status", models.CharField(choices=[("active", "Ativo"), ("draft", "Rascunho"), ("inactive", "Inativo")], default="draft", max_length=16)),
                ("is_active", models.BooleanField(default=False)),
                ("is_featured", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tenant", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="products", to="tenants.tenant")),
            ],
            options={
                "ordering": ("tenant_id", "name"),
            },
        ),
        migrations.CreateModel(
            name="ProductVariant",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sku", models.CharField(max_length=120, unique=True)),
                ("price", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("compare_price", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("stock", models.PositiveIntegerField(default=0)),
                ("reserved_stock", models.PositiveIntegerField(default=0)),
                ("track_inventory", models.BooleanField(default=True)),
                ("allow_backorder", models.BooleanField(default=False)),
                ("is_default", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("product", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="variants", to="catalog.product")),
            ],
            options={
                "ordering": ("product_id", "-is_default", "sku"),
            },
        ),
        migrations.AddConstraint(
            model_name="product",
            constraint=models.UniqueConstraint(fields=("tenant", "slug"), name="catalog_product_unique_slug_per_tenant"),
        ),
    ]
