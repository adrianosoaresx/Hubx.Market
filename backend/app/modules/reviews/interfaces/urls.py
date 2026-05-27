from django.urls import path

from .views import AdminReviewCreateView, AdminReviewModerateView, AdminReviewsListView


app_name = "reviews"


urlpatterns = [
    path("", AdminReviewsListView.as_view(), name="admin-reviews-list"),
    path("new/", AdminReviewCreateView.as_view(), name="admin-reviews-create"),
    path("<int:review_id>/moderate/", AdminReviewModerateView.as_view(), name="admin-review-moderate"),
]
