from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("subscriptions", "0002_subscriptionacquisitionlead"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscriptionplan",
            name="feature_list",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="subscriptionplan",
            name="requires_payment_method",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="subscriptionplan",
            name="trial_days",
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
