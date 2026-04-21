from __future__ import annotations

from urllib.parse import urlencode

from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import TemplateView

from app.modules.checkout.application.checkout_completion_commands import checkout_completion_commands
from app.modules.checkout.application.checkout_page_queries import checkout_page_queries
from app.modules.checkout.application.checkout_session_commands import checkout_session_commands


class CheckoutPageView(TemplateView):
    template_name = "pages/templates/checkout_page.html"

    def _base_query_context(self) -> tuple[str | None, str, str | None]:
        session_key = self.request.GET.get("session_key") or self.request.POST.get("session_key")
        back_url = self.request.GET.get(
            "back_url",
            self.request.POST.get(
                "back_url",
                reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner"}),
            ),
        )
        stage = self.request.GET.get("stage") or self.request.POST.get("current_stage")
        return session_key, back_url, stage

    def post(self, request, *args, **kwargs):
        session_key, back_url, stage = self._base_query_context()
        if stage == "review":
            result, order_number = checkout_completion_commands.complete_checkout(session_key=str(session_key or ""))
            if result == "checkout-completed" and order_number:
                return HttpResponseRedirect(
                    f'{reverse("accounts:account-order-detail", kwargs={"order_number": order_number})}?{urlencode({"result": result})}'
                )
            fallback_stage = stage or "review"
            if session_key:
                payload = checkout_page_queries.get_checkout_page_data(session_key=session_key, requested_stage=stage)
                fallback_stage = str(payload.get("current_stage", fallback_stage))
            params = {"back_url": back_url, "result": result, "stage": fallback_stage}
            if session_key:
                params["session_key"] = session_key
            return HttpResponseRedirect(f'{reverse("checkout:checkout-page")}?{urlencode(params)}')
        result = checkout_session_commands.update_session(
            session_key=str(session_key or ""),
            payload={
                "first_name": request.POST.get("first_name", ""),
                "last_name": request.POST.get("last_name", ""),
                "email": request.POST.get("email", ""),
                "phone": request.POST.get("phone", ""),
                "address_line_1": request.POST.get("address_line_1", ""),
                "address_line_2": request.POST.get("address_line_2", ""),
                "city": request.POST.get("city", ""),
                "state": request.POST.get("state", ""),
                "zip_code": request.POST.get("zip_code", ""),
                "shipping_method_selected": request.POST.get("shipping_method", ""),
                "payment_method_selected": request.POST.get("payment_method", ""),
                "installments_selected": request.POST.get("installments", ""),
                "accept_terms": bool(request.POST.get("accept_terms")),
            },
        )
        params = {"back_url": back_url, "result": result}
        if session_key:
            params["session_key"] = session_key
        if result == "checkout-saved":
            payload = checkout_page_queries.get_checkout_page_data(session_key=session_key, requested_stage=stage)
            params["stage"] = str(payload.get("next_stage", stage or "delivery"))
        elif stage:
            params["stage"] = stage
        return HttpResponseRedirect(f'{reverse("checkout:checkout-page")}?{urlencode(params)}')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session_key, back_url, stage = self._base_query_context()
        context.update(checkout_page_queries.get_checkout_page_data(session_key=session_key, requested_stage=stage))
        context["back_url"] = back_url
        form_params = {"back_url": back_url}
        if session_key:
            form_params["session_key"] = session_key
        if context.get("current_stage"):
            form_params["stage"] = context["current_stage"]
        context["form_action"] = f'{self.request.path}?{urlencode(form_params)}'
        if session_key:
            context["session_key"] = session_key
        result = self.request.GET.get("result", "").strip()
        if result == "checkout-saved":
            context["checkout_feedback"] = {
                "variant": "success",
                "icon": "✅",
                "title": "Etapa salva",
                "description": f'Os dados de {str(context.get("current_stage_label", "checkout")).lower()} foram salvos na sua sessão atual.',
            }
        elif result == "checkout-save-unavailable":
            context["checkout_feedback"] = {
                "variant": "warning",
                "icon": "ℹ️",
                "title": "Sessão indisponível",
                "description": "Não foi possível salvar esta etapa agora. Tente iniciar o checkout novamente a partir do produto.",
            }
        elif result == "checkout-completion-blocked":
            context["checkout_feedback"] = {
                "variant": "warning",
                "icon": "🧩",
                "title": "Revisão ainda incompleta",
                "description": "Antes de gerar o pedido, confirme entrega, pagamento e aceite de termos na sessão atual.",
            }
        elif result == "checkout-completion-unavailable":
            context["checkout_feedback"] = {
                "variant": "warning",
                "icon": "ℹ️",
                "title": "Não foi possível gerar o pedido",
                "description": "A sessão atual não pôde ser concluída agora. Tente retomar o checkout a partir do produto.",
            }
        elif result == "checkout-completion-inventory-link-missing":
            context["checkout_feedback"] = {
                "variant": "warning",
                "icon": "🧩",
                "title": "Vínculo de estoque incompleto",
                "description": "Um item desta sessão não está ligado com segurança a uma variante vendável. Retome o checkout a partir do produto.",
            }
        elif result == "checkout-completion-inventory-unavailable":
            context["checkout_feedback"] = {
                "variant": "warning",
                "icon": "📦",
                "title": "Item indisponível para concluir",
                "description": "Uma das variantes desta sessão não está mais disponível para confirmação segura. Revise o produto antes de continuar.",
            }
        elif result == "checkout-completion-stock-conflict":
            context["checkout_feedback"] = {
                "variant": "warning",
                "icon": "⚠️",
                "title": "Estoque mudou durante o checkout",
                "description": "O saldo livre da variante não é mais suficiente para concluir esta sessão com segurança. Revise o produto e tente novamente.",
            }
        return context
