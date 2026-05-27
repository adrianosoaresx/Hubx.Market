from django.contrib import admin

from .models import Page


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "tenant", "status", "updated_at")
    list_filter = ("status", "tenant")
    search_fields = ("title", "slug", "seo_title", "seo_description")
    readonly_fields = ("created_at", "updated_at", "published_at")
