from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve
from django.views.generic import TemplateView

from app.modules.catalog.interfaces.views import PublicDemoAccessView, StorefrontHomeView
from app.modules.pages.interfaces.views import DesignSystemPagesView

urlpatterns = [
    path("", StorefrontHomeView.as_view(), name="storefront-home"),
    path("demo/", PublicDemoAccessView.as_view(), name="public-demo"),
    path("admin/", admin.site.urls),
    path("accounts/", include(("app.modules.accounts.interfaces.urls", "accounts"), namespace="accounts")),
    path("plans/", include(("app.modules.subscriptions.interfaces.public_urls", "subscription_public"), namespace="subscription_public")),
    path("api-keys/", include(("app.modules.api_keys.interfaces.urls", "api_keys"), namespace="api_keys")),
    path("api/v1/catalog/", include(("app.modules.catalog.interfaces.public_api_urls", "catalog_public_api"), namespace="catalog_public_api")),
    path("cart/", include(("app.modules.cart.interfaces.urls", "cart"), namespace="cart")),
    path("catalog/", include(("app.modules.catalog.interfaces.storefront_urls", "storefront"), namespace="storefront")),
    path("checkout/", include(("app.modules.checkout.interfaces.urls", "checkout"), namespace="checkout")),
    path("payments/", include(("app.modules.payments.interfaces.urls", "payments"), namespace="payments")),
    path("notifications/", include(("app.modules.notifications.interfaces.urls", "notifications"), namespace="notifications")),
    path("newsletter/", include(("app.modules.newsletter.interfaces.storefront_urls", "storefront_newsletter"), namespace="storefront_newsletter")),
    path("ops/branding/", include(("app.modules.tenants.interfaces.ops_urls", "tenant_branding"), namespace="tenant_branding")),
    path("ops/", include(("app.modules.accounts.interfaces.merchant_ops_urls", "merchant_ops"), namespace="merchant_ops")),
    path("ops/audit/", include(("app.modules.audit.interfaces.urls", "audit"), namespace="audit")),
    path("ops/api-keys/", include(("app.modules.api_keys.interfaces.ops_urls", "api_keys_ops"), namespace="api_keys_ops")),
    path("ops/catalog/", include(("app.modules.catalog.interfaces.urls", "catalog"), namespace="catalog")),
    path("ops/checkout/", include(("app.modules.checkout.interfaces.ops_urls", "checkout_ops"), namespace="checkout_ops")),
    path("ops/coupons/", include(("app.modules.coupons.interfaces.urls", "coupons"), namespace="coupons")),
    path("ops/customers/", include(("app.modules.customers.interfaces.urls", "customers"), namespace="customers")),
    path("ops/newsletter/", include(("app.modules.newsletter.interfaces.urls", "newsletter"), namespace="newsletter")),
    path("ops/owners/", include(("app.modules.accounts.interfaces.owner_urls", "owners"), namespace="owners")),
    path("ops/orders/", include(("app.modules.orders.interfaces.urls", "orders"), namespace="orders")),
    path("ops/payments/", include(("app.modules.payments.interfaces.ops_urls", "payments_ops"), namespace="payments_ops")),
    path("ops/pages/", include(("app.modules.pages.interfaces.urls", "pages"), namespace="pages")),
    path("ops/platform/acquisitions/", include(("app.modules.subscriptions.interfaces.acquisition_urls", "subscription_acquisitions"), namespace="subscription_acquisitions")),
    path("ops/platform/subscription-coupons/", include(("app.modules.subscriptions.interfaces.coupon_urls", "subscription_coupons"), namespace="subscription_coupons")),
    path("ops/platform/onboarding/", include(("app.modules.tenants.interfaces.onboarding_urls", "tenant_onboarding"), namespace="tenant_onboarding")),
    path("ops/platform/tenants/", include(("app.modules.tenants.interfaces.urls", "tenants"), namespace="tenants")),
    path("ops/reviews/", include(("app.modules.reviews.interfaces.urls", "reviews"), namespace="reviews")),
    path("ops/shipping/", include(("app.modules.shipping.interfaces.urls", "shipping"), namespace="shipping")),
    path("ops/subscriptions/", include(("app.modules.subscriptions.interfaces.urls", "subscriptions"), namespace="subscriptions")),
    path("pages/", include(("app.modules.pages.interfaces.storefront_urls", "storefront_pages"), namespace="storefront_pages")),
]

if settings.DEBUG:
    urlpatterns += [
        path(
            "__internal__/design-system/",
            TemplateView.as_view(template_name="pages/design_system/index.html"),
            name="design-system-index",
        ),
        path(
            "__internal__/design-system/components/",
            TemplateView.as_view(template_name="pages/design_system/components.html"),
            name="design-system-components",
        ),
        path(
            "__internal__/design-system/forms/",
            TemplateView.as_view(template_name="pages/design_system/forms.html"),
            name="design-system-forms",
        ),
        path(
            "__internal__/design-system/ecommerce/",
            TemplateView.as_view(template_name="pages/design_system/ecommerce.html"),
            name="design-system-ecommerce",
        ),
        path(
            "__internal__/design-system/pages/",
            DesignSystemPagesView.as_view(),
            name="design-system-pages",
        ),
    ]

    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif getattr(settings, "HUBX_SERVE_MEDIA_LOCALLY", False):
    urlpatterns += [
        re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    ]
