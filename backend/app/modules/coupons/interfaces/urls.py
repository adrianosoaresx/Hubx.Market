from django.urls import path

from .views import AdminCouponCreateView, AdminCouponsListView


app_name = "coupons"


urlpatterns = [
    path("", AdminCouponsListView.as_view(), name="admin-coupons-list"),
    path("new/", AdminCouponCreateView.as_view(), name="admin-coupons-create"),
]
