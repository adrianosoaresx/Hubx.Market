from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q


class ProductReview(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        APPROVED = "approved", "Aprovada"
        REJECTED = "rejected", "Rejeitada"

    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="product_reviews")
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE, related_name="reviews")
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        related_name="product_reviews",
        null=True,
        blank=True,
    )
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=120, blank=True)
    body = models.TextField(blank=True)
    author_name = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    moderated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("tenant_id", "product_id", "-created_at", "-id")
        constraints = [
            models.CheckConstraint(check=Q(rating__gte=1) & Q(rating__lte=5), name="review_rating_between_1_and_5"),
        ]
        indexes = [
            models.Index(fields=("tenant", "product", "status"), name="review_tenant_prod_stat_idx"),
            models.Index(fields=("tenant", "status", "created_at"), name="review_tenant_stat_cr_idx"),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.tenant_id}:{self.product_id}:{self.rating}:{self.status}"
