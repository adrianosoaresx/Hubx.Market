from django.urls import path

from .views import AdminAuditEvidenceExportView, AdminAuditLogListView


app_name = "audit"


urlpatterns = [
    path("", AdminAuditLogListView.as_view(), name="admin-audit-log-list"),
    path("export/", AdminAuditEvidenceExportView.as_view(), name="admin-audit-evidence-export"),
]
