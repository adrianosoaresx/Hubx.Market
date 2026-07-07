from django.urls import path

from .ops_views import (
    AdminPaymentFinanceView,
    AdminPaymentRefundApproveView,
    AdminPaymentRefundExecuteView,
    AdminPaymentRefundsView,
)


app_name = "payments_ops"


urlpatterns = [
    path("finance/", AdminPaymentFinanceView.as_view(), name="admin-finance"),
    path("refunds/", AdminPaymentRefundsView.as_view(), name="admin-refunds"),
    path("refunds/<uuid:refund_key>/approve/", AdminPaymentRefundApproveView.as_view(), name="admin-refund-approve"),
    path("refunds/<uuid:refund_key>/execute/", AdminPaymentRefundExecuteView.as_view(), name="admin-refund-execute"),
]
