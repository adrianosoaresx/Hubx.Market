from django.contrib import admin

from .models import NewsletterSubscriber


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "tenant", "status", "source", "updated_at")
    list_filter = ("status", "tenant")
    search_fields = ("email", "name", "source")
    readonly_fields = ("created_at", "updated_at", "consented_at", "unsubscribed_at")
