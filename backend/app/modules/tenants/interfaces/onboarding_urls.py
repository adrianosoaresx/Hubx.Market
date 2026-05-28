from django.urls import path

from .views import (
    TenantOnboardingCompleteView,
    TenantOnboardingCreateView,
    TenantOnboardingDetailView,
    TenantOnboardingListView,
    TenantOnboardingStepView,
)


app_name = "tenant_onboarding"


urlpatterns = [
    path("", TenantOnboardingListView.as_view(), name="onboarding-list"),
    path("new/", TenantOnboardingCreateView.as_view(), name="onboarding-create"),
    path("<int:onboarding_id>/", TenantOnboardingDetailView.as_view(), name="onboarding-detail"),
    path("<int:onboarding_id>/step/<slug:step_key>/", TenantOnboardingStepView.as_view(), name="onboarding-step"),
    path("<int:onboarding_id>/complete/", TenantOnboardingCompleteView.as_view(), name="onboarding-complete"),
]
