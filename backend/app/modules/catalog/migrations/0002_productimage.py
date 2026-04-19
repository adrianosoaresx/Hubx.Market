from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image_url", models.URLField(max_length=500)),
                ("alt_text", models.CharField(blank=True, max_length=255)),
                ("position", models.PositiveIntegerField(default=0)),
                ("is_primary", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "product",
                    models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="images", to="catalog.product"),
                ),
            ],
            options={
                "ordering": ("product_id", "-is_primary", "position", "id"),
            },
        ),
    ]
