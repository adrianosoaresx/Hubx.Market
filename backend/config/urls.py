from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include(("app.modules.accounts.interfaces.urls", "accounts"), namespace="accounts")),
    path("catalog/", include(("app.modules.catalog.interfaces.storefront_urls", "storefront"), namespace="storefront")),
    path("checkout/", include(("app.modules.checkout.interfaces.urls", "checkout"), namespace="checkout")),
    path("payments/", include(("app.modules.payments.interfaces.urls", "payments"), namespace="payments")),
    path("ops/catalog/", include(("app.modules.catalog.interfaces.urls", "catalog"), namespace="catalog")),
    path("ops/customers/", include(("app.modules.customers.interfaces.urls", "customers"), namespace="customers")),
    path("ops/orders/", include(("app.modules.orders.interfaces.urls", "orders"), namespace="orders")),
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
            TemplateView.as_view(template_name="pages/design_system/pages.html"),
            name="design-system-pages",
        ),
    ]

    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
