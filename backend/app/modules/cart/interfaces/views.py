from __future__ import annotations

from urllib.parse import urlencode

from django.contrib import messages
from django.http import Http404
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from django.views.generic import TemplateView

from app.modules.cart.application.cart_checkout_queries import cart_checkout_queries
from app.modules.cart.application.cart_commands import cart_commands
from app.modules.cart.application.cart_page_queries import cart_page_queries
from app.modules.checkout.application.checkout_activation_commands import checkout_activation_commands


def _require_storefront_tenant(request):
    tenant = getattr(request, "tenant", None)
    if not getattr(tenant, "id", None):
        raise Http404("Tenant not found")
    return tenant


def _session_key(request) -> str:
    if not request.session.session_key:
        request.session.save()
    return str(request.session.session_key or "")


def _stock_guard_message(result: dict[str, object]) -> str:
    available_quantity = result.get("available_quantity")
    if result.get("result") == "cart-item-stock-unavailable":
        return "Este item não está disponível para compra no momento."
    if available_quantity is not None:
        return f"Temos {available_quantity} unidade(s) disponível(is) para este item agora."
    return "Não foi possível atualizar a quantidade solicitada."


class CartPageView(TemplateView):
    template_name = "pages/templates/cart_page.html"

    def post(self, request, *args, **kwargs):
        tenant = _require_storefront_tenant(request)
        tenant_id = getattr(tenant, "id", None)
        session_key = _session_key(request)
        intent = str(request.POST.get("cart_intent") or "").strip()

        if intent == "checkout":
            payload = cart_checkout_queries.get_checkout_payload(tenant_id=tenant_id, session_key=session_key)
            cart = payload.get("cart") if isinstance(payload, dict) else None
            checkout_session_key = checkout_activation_commands.activate_from_cart(cart or {})
            if checkout_session_key and cart:
                cart_commands.mark_converted(
                    tenant_id=tenant_id,
                    cart_id=int(cart["id"]),
                    checkout_session_key=checkout_session_key,
                )
                params = {
                    "back_url": reverse("cart:cart-page"),
                    "stage": "cart",
                    "session_key": checkout_session_key,
                }
                return HttpResponseRedirect(f'{reverse("checkout:checkout-page")}?{urlencode(params)}')
            return HttpResponseRedirect(reverse("cart:cart-page"))

        if intent == "apply_coupon":
            cart_commands.apply_coupon_intent(
                tenant_id=tenant_id,
                session_key=session_key,
                coupon_code=request.POST.get("coupon_code", ""),
            )
            return HttpResponseRedirect(reverse("cart:cart-page"))

        if intent == "remove_coupon":
            cart_commands.remove_coupon_intent(tenant_id=tenant_id, session_key=session_key)
            return HttpResponseRedirect(reverse("cart:cart-page"))

        item_id = request.POST.get("item_id")
        cart_id = request.POST.get("cart_id")
        action = str(request.POST.get("item_action") or "").strip()
        try:
            current_quantity = max(1, int(request.POST.get("quantity", 1) or 1))
            normalized_cart_id = int(cart_id)
            normalized_item_id = int(item_id)
        except (TypeError, ValueError):
            return HttpResponseRedirect(reverse("cart:cart-page"))

        if action == "increment":
            result = cart_commands.update_quantity(
                tenant_id=tenant_id,
                cart_id=normalized_cart_id,
                item_id=normalized_item_id,
                quantity=current_quantity + 1,
            )
        elif action == "decrement":
            result = cart_commands.update_quantity(
                tenant_id=tenant_id,
                cart_id=normalized_cart_id,
                item_id=normalized_item_id,
                quantity=max(1, current_quantity - 1),
            )
        elif action == "remove":
            result = cart_commands.remove_item(
                tenant_id=tenant_id,
                cart_id=normalized_cart_id,
                item_id=normalized_item_id,
            )
        else:
            result = {}
        if result.get("result") in {"cart-item-stock-conflict", "cart-item-stock-unavailable"}:
            messages.warning(request, _stock_guard_message(result))

        return HttpResponseRedirect(reverse("cart:cart-page"))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = _require_storefront_tenant(self.request)
        payload = cart_page_queries.get_cart_page_data(
            tenant_id=getattr(tenant, "id", None),
            session_key=_session_key(self.request),
        )
        continue_href = reverse("storefront:catalog-list")
        payload["continue_shopping_href"] = continue_href
        payload["continue_shopping_action"] = format_html(
            '<a class="ds-btn ds-btn-secondary ds-btn-md" href="{}">Continuar comprando</a>',
            continue_href,
        )
        payload["checkout_action_enabled"] = bool(payload.get("cart_items"))
        context.update(payload)
        return context
