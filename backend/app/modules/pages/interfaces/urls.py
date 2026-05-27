from django.urls import path

from .views import AdminPageFormView, AdminPagesListView


app_name = "pages"


urlpatterns = [
    path("", AdminPagesListView.as_view(), name="admin-pages-list"),
    path("new/", AdminPageFormView.as_view(), name="admin-pages-create"),
    path("<int:page_id>/edit/", AdminPageFormView.as_view(), name="admin-pages-edit"),
]
