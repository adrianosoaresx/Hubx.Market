from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0005_tenantonboarding_promotion_snapshots"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenant",
            name="conversion_primary_color",
            field=models.CharField(blank=True, default="", max_length=7),
            preserve_default=False,
        ),
    ]
