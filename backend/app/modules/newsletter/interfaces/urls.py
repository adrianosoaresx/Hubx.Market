from django.urls import path

from .views import AdminNewsletterCampaignCreateView, AdminNewsletterCampaignSendView, AdminNewsletterListView


app_name = "newsletter"


urlpatterns = [
    path("", AdminNewsletterListView.as_view(), name="admin-newsletter-list"),
    path("campaigns/new/", AdminNewsletterCampaignCreateView.as_view(), name="admin-newsletter-campaign-create"),
    path(
        "campaigns/<int:campaign_id>/send/",
        AdminNewsletterCampaignSendView.as_view(),
        name="admin-newsletter-campaign-send",
    ),
]
