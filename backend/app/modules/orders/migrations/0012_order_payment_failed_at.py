from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0011_order_payment_confirmed_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="payment_failed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
