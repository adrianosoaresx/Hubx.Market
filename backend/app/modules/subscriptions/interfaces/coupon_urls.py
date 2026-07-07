from django.urls import path

from .views import (
    PlatformSubscriptionCouponCreateView,
    PlatformSubscriptionCouponListView,
    PlatformSubscriptionCouponStatusView,
)


app_name = "subscription_coupons"


urlpatterns = [
    path("", PlatformSubscriptionCouponListView.as_view(), name="platform-subscription-coupons-list"),
    path("new/", PlatformSubscriptionCouponCreateView.as_view(), name="platform-subscription-coupons-create"),
    path("<int:coupon_id>/status/", PlatformSubscriptionCouponStatusView.as_view(), name="platform-subscription-coupons-status"),
]
