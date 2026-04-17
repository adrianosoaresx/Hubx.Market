from __future__ import annotations

from django.urls import reverse
from django.views.generic import TemplateView

from app.modules.checkout.application.checkout_page_queries import checkout_page_queries


class CheckoutPageView(TemplateView):
    template_name = "pages/templates/checkout_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(checkout_page_queries.get_checkout_page_data())
        context["back_url"] = reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner"})
        return context
