from django.contrib import admin

from app.modules.reviews.models import ProductReview


@admin.register(ProductReview)
class ProductReviewAdmin(admin.ModelAdmin):
    list_display = ("tenant", "product", "rating", "status", "author_name", "created_at")
    list_filter = ("status", "rating", "tenant")
    search_fields = ("product__name", "author_name", "title", "body")
    readonly_fields = ("created_at", "updated_at")
