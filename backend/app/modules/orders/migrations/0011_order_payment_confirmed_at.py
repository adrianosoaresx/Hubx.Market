from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0010_order_payment_source_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="payment_confirmed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
