from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0003_storefrontdiscoveryeventlog"),
    ]

    operations = [
        migrations.AddField(
            model_name="productvariant",
            name="barcode",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="productvariant",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="productvariant",
            name="label",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name="productvariant",
            name="option_values",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="productvariant",
            name="position",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="productvariant",
            name="weight_grams",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterModelOptions(
            name="productvariant",
            options={"ordering": ("product_id", "position", "-is_default", "sku")},
        ),
        migrations.AddIndex(
            model_name="productvariant",
            index=models.Index(
                fields=["product", "is_active", "is_default", "position"],
                name="cat_var_prod_active_idx",
            ),
        ),
    ]
