from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0002_tenantonboarding"),
    ]

    operations = [
        migrations.AddField(
            model_name="tenant",
            name="storefront_hero_enabled",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="tenant",
            name="storefront_hero_title",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name="tenant",
            name="storefront_hero_description",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="tenant",
            name="storefront_hero_image_url",
            field=models.URLField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="tenant",
            name="storefront_hero_cta_label",
            field=models.CharField(blank=True, max_length=80),
        ),
        migrations.AddField(
            model_name="tenant",
            name="storefront_hero_cta_href",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
