from __future__ import annotations

from urllib.parse import urlencode

from django.http import Http404
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import TemplateView

from app.modules.checkout.application.checkout_completion_commands import checkout_completion_commands
from app.modules.checkout.application.checkout_page_queries import checkout_page_queries
from app.modules.checkout.application.checkout_session_commands import checkout_session_commands


def _build_checkout_recovery_context(*, request, result: str, back_url: str, session_key: str | None, stage: str | None) -> dict[str, object]:
    retry_params = {}
    if back_url:
        retry_params["back_url"] = back_url
    if session_key:
        retry_params["session_key"] = session_key
    if stage:
        retry_params["stage"] = stage
    retry_href = f'{reverse("checkout:checkout-page")}?{urlencode(retry_params)}' if retry_params else reverse("checkout:checkout-page")

    recovery_map = {
        "checkout-save-unavailable": {
            "title": "Como retomar com segurança",
            "description": "Volte ao produto para iniciar uma nova sessão de checkout antes de tentar novamente.",
            "helper": "Use a própria página do produto para recriar o caminho com itens e variante atualizados.",
            "primary_label": "Voltar ao produto",
            "primary_href": back_url,
            "secondary_label": "",
            "secondary_href": "",
        },
        "checkout-completion-unavailable": {
            "title": "Como retomar com segurança",
            "description": "Tente reabrir esta sessão primeiro. Se ela continuar indisponível, retome o checkout a partir do produto.",
            "helper": "Isso evita seguir com uma sessão incompleta ou desatualizada.",
            "primary_label": "Reabrir checkout",
            "primary_href": retry_href,
            "secondary_label": "Voltar ao produto",
            "secondary_href": back_url,
        },
        "checkout-completion-session-drift": {
            "title": "Como retomar com segurança",
            "description": "Esta sessão já apontava para um pedido anterior, mas esse vínculo não está mais íntegro. Reabra o checkout com uma sessão nova antes de seguir.",
            "helper": "Isso evita reutilizar uma sessão concluída que já não representa com segurança o pedido persistido.",
            "primary_label": "Reabrir checkout",
            "primary_href": retry_href,
            "secondary_label": "Voltar ao produto",
            "secondary_href": back_url,
        },
        "checkout-completion-inventory-link-missing": {
            "title": "Como retomar com segurança",
            "description": "Volte ao produto para reconstruir o checkout a partir de uma variante vendável válida.",
            "helper": "A sessão atual não mantém um vínculo seguro para concluir este pedido inicial.",
            "primary_label": "Revisar produto",
            "primary_href": back_url,
            "secondary_label": "Reabrir checkout",
            "secondary_href": retry_href,
        },
        "checkout-completion-inventory-unavailable": {
            "title": "Como retomar com segurança",
            "description": "Revise a disponibilidade no produto antes de tentar gerar o pedido inicial novamente.",
            "helper": "Se a variante não estiver mais disponível, a melhor retomada é recomeçar pelo produto.",
            "primary_label": "Revisar produto",
            "primary_href": back_url,
            "secondary_label": "Reabrir checkout",
            "secondary_href": retry_href,
        },
        "checkout-completion-stock-conflict": {
            "title": "Como retomar com segurança",
            "description": "Revise o produto para confirmar estoque e só depois tente gerar o pedido inicial novamente.",
            "helper": "O saldo livre mudou durante o checkout; reabrir a sessão ajuda a conferir o estado atual antes de seguir.",
            "primary_label": "Revisar produto",
            "primary_href": back_url,
            "secondary_label": "Reabrir checkout",
            "secondary_href": retry_href,
        },
        "checkout-completion-snapshot-conflict": {
            "title": "Como retomar com segurança",
            "description": "Reabra esta sessão para revisar itens e totais antes de tentar gerar o pedido inicial novamente.",
            "helper": "Encontramos uma inconsistência entre os itens do checkout e os totais salvos na sessão atual.",
            "primary_label": "Reabrir checkout",
            "primary_href": retry_href,
            "secondary_label": "Voltar ao produto",
            "secondary_href": back_url,
        },
    }
    payload = recovery_map.get(result)
    if not payload:
        return {}
    return {"checkout_recovery": payload}


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
        tenant = getattr(request, "tenant", None)
        tenant_id = getattr(tenant, "id", None)
        if not tenant_id and not session_key:
            raise Http404("Checkout session not found")
        item_action = str(request.POST.get("item_action", "") or "").strip()
        if item_action:
            operation, _, raw_item_id = item_action.partition(":")
            try:
                item_id = int(raw_item_id)
            except (TypeError, ValueError):
                item_id = 0
            result = checkout_session_commands.mutate_item(
                session_key=str(session_key or ""),
                item_id=item_id,
                operation=operation,
            )
            fallback_stage = stage or "delivery"
            if session_key:
                payload = checkout_page_queries.get_checkout_page_data(
                    tenant_id=tenant_id,
                    session_key=session_key,
                    requested_stage=stage,
                )
                fallback_stage = str(payload.get("current_stage", fallback_stage))
            params = {"back_url": back_url, "result": result, "stage": fallback_stage}
            if session_key:
                params["session_key"] = session_key
            return HttpResponseRedirect(f'{reverse("checkout:checkout-page")}?{urlencode(params)}')
        if stage == "cart":
            params = {"back_url": back_url, "stage": "delivery"}
            if session_key:
                params["session_key"] = session_key
            return HttpResponseRedirect(f'{reverse("checkout:checkout-page")}?{urlencode(params)}')
        if stage == "review":
            result, order_number = checkout_completion_commands.complete_checkout(session_key=str(session_key or ""))
            if result == "checkout-completed" and order_number:
                return HttpResponseRedirect(
                    f'{reverse("accounts:account-order-detail", kwargs={"order_number": order_number})}?{urlencode({"result": result})}'
                )
            fallback_stage = stage or "review"
            if session_key:
                payload = checkout_page_queries.get_checkout_page_data(
                    tenant_id=tenant_id,
                    session_key=session_key,
                    requested_stage=stage,
                )
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
            payload = checkout_page_queries.get_checkout_page_data(
                tenant_id=tenant_id,
                session_key=session_key,
                requested_stage=stage,
            )
            params["stage"] = str(payload.get("next_stage", stage or "delivery"))
        elif stage:
            params["stage"] = stage
        return HttpResponseRedirect(f'{reverse("checkout:checkout-page")}?{urlencode(params)}')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session_key, back_url, stage = self._base_query_context()
        tenant = getattr(self.request, "tenant", None)
        tenant_id = getattr(tenant, "id", None)
        if not tenant_id and not session_key:
            raise Http404("Checkout session not found")
        context.update(
            checkout_page_queries.get_checkout_page_data(
                tenant_id=tenant_id,
                session_key=session_key,
                requested_stage=stage,
            )
        )
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
                "description": "Antes de gerar o pedido inicial, confirme entrega, pagamento e aceite de termos na sessão atual.",
            }
        elif result == "checkout-completion-unavailable":
            context["checkout_feedback"] = {
                "variant": "warning",
                "icon": "ℹ️",
                "title": "Não foi possível gerar o pedido",
                "description": "A sessão atual não pôde gerar o pedido inicial agora. Tente retomar o checkout a partir do produto.",
            }
        elif result == "checkout-completion-session-drift":
            context["checkout_feedback"] = {
                "variant": "warning",
                "icon": "🧭",
                "title": "Sessão concluída com vínculo inconsistente",
                "description": "A sessão já tinha sido concluída antes, mas o vínculo com o pedido persistido não está mais íntegro. Reabra o checkout com segurança antes de seguir.",
            }
        elif result == "checkout-completion-inventory-link-missing":
            context["checkout_feedback"] = {
                "variant": "warning",
                "icon": "🧩",
                "title": "Vínculo de estoque incompleto",
                "description": "Um item desta sessão não está ligado com segurança a uma variante vendável. Revise o produto e gere um novo pedido inicial a partir dele.",
            }
        elif result == "checkout-completion-inventory-unavailable":
            context["checkout_feedback"] = {
                "variant": "warning",
                "icon": "📦",
                "title": "Item indisponível para concluir",
                "description": "Uma das variantes desta sessão não está mais disponível para confirmação segura. Revise o produto antes de tentar gerar o pedido inicial novamente.",
            }
        elif result == "checkout-completion-stock-conflict":
            context["checkout_feedback"] = {
                "variant": "warning",
                "icon": "⚠️",
                "title": "Estoque mudou durante o checkout",
                "description": "O saldo livre da variante não é mais suficiente para concluir esta sessão com segurança. Revise o produto antes de tentar gerar o pedido inicial novamente.",
            }
        elif result == "checkout-completion-snapshot-conflict":
            context["checkout_feedback"] = {
                "variant": "warning",
                "icon": "🧾",
                "title": "Sessão mudou antes da conclusão",
                "description": "Itens ou totais desta sessão já não estão consistentes para gerar o pedido inicial. Reabra o checkout e revise os dados antes de concluir.",
            }
        elif result == "checkout-item-updated":
            context["checkout_feedback"] = {
                "variant": "success",
                "icon": "🛒",
                "title": "Item atualizado",
                "description": "Quantidade ajustada e totais recalculados na sessão atual.",
            }
        elif result == "checkout-item-removed":
            context["checkout_feedback"] = {
                "variant": "success",
                "icon": "🧺",
                "title": "Item removido",
                "description": "A sessão foi atualizada com segurança após remover este item.",
            }
        elif result == "checkout-item-session-empty":
            context["checkout_feedback"] = {
                "variant": "warning",
                "icon": "🧺",
                "title": "Sessão agora está vazia",
                "description": "Adicione um item válido para retomar entrega, pagamento e revisão nesta sessão.",
            }
        elif result == "checkout-item-mutation-unavailable":
            context["checkout_feedback"] = {
                "variant": "warning",
                "icon": "ℹ️",
                "title": "Não foi possível atualizar o item",
                "description": "Tente reabrir esta sessão antes de ajustar o carrinho novamente.",
            }
        elif result == "reorder-lite-ready":
            context["checkout_feedback"] = {
                "variant": "success",
                "icon": "🛒",
                "title": "Nova sessão pronta",
                "description": "Os itens elegíveis do pedido anterior já foram recriados nesta sessão para você revisar antes de seguir.",
            }
        elif result == "reorder-lite-partial":
            context["checkout_feedback"] = {
                "variant": "info",
                "icon": "🧺",
                "title": "Sessão recriada parcialmente",
                "description": "Só os itens ainda elegíveis voltaram para a sessão atual. Revise o carrinho antes de seguir.",
            }
        elif result == "payment-retry-ready":
            context["checkout_feedback"] = {
                "variant": "success",
                "icon": "💳",
                "title": "Sessão pronta para nova tentativa",
                "description": "Recriamos esta sessão a partir do pedido pendente para você revisar entrega e retomar o pagamento com segurança.",
            }
        elif result == "payment-retry-partial":
            context["checkout_feedback"] = {
                "variant": "info",
                "icon": "🧩",
                "title": "Sessão de pagamento recriada parcialmente",
                "description": "Só os itens ainda elegíveis voltaram para a sessão atual. Revise entrega e pagamento antes de seguir.",
            }
        elif result == "payment-retry-unavailable":
            context["checkout_feedback"] = {
                "variant": "warning",
                "icon": "ℹ️",
                "title": "Não foi possível retomar o pagamento",
                "description": "Não encontramos uma sessão segura para este pedido agora. Revise o pedido e tente novamente mais tarde.",
            }
        elif result == "payment-retry-blocked":
            context["checkout_feedback"] = {
                "variant": "warning",
                "icon": "🧾",
                "title": "Pedido não elegível para nova tentativa",
                "description": "Só pedidos pendentes com falha de pagamento podem abrir uma nova tentativa segura nesta etapa.",
            }
        context.update(
            _build_checkout_recovery_context(
                request=self.request,
                result=result,
                back_url=back_url,
                session_key=session_key,
                stage=stage,
            )
        )
        return context
