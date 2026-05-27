from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("cart", "0001_initial"),
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CartMutation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("mutation_key", models.CharField(max_length=120)),
                (
                    "mutation_type",
                    models.CharField(choices=[("add_item", "Adicionar item")], max_length=32),
                ),
                ("result_snapshot", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "cart",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="mutations",
                        to="cart.cart",
                    ),
                ),
                (
                    "tenant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="cart_mutations",
                        to="tenants.tenant",
                    ),
                ),
            ],
            options={
                "ordering": ("tenant_id", "-created_at", "-id"),
            },
        ),
        migrations.AddIndex(
            model_name="cartmutation",
            index=models.Index(fields=["tenant", "mutation_type"], name="cart_mut_tenant_type_idx"),
        ),
        migrations.AddIndex(
            model_name="cartmutation",
            index=models.Index(fields=["cart", "mutation_key"], name="cart_mut_cart_key_idx"),
        ),
        migrations.AddConstraint(
            model_name="cartmutation",
            constraint=models.UniqueConstraint(fields=("tenant", "cart", "mutation_key"), name="cart_mutation_unique_key"),
        ),
    ]
