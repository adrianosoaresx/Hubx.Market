from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0003_tenant_storefront_hero"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenant",
            name="logo_url",
            field=models.URLField(blank=True, max_length=500),
        ),
    ]
