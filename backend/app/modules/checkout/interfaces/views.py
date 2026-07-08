from __future__ import annotations

from urllib.parse import urlencode

from django.conf import settings
from django.http import Http404
from django.http import HttpResponse
from django.http import HttpResponseNotFound
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from app.modules.checkout.application.checkout_completion_commands import checkout_completion_commands
from app.modules.checkout.application.checkout_metrics_queries import checkout_metrics_queries
from app.modules.checkout.application.checkout_page_queries import checkout_page_queries
from app.modules.checkout.application.checkout_recovery_event_commands import record_checkout_recovery_event
from app.modules.checkout.application.checkout_result_taxonomy import classify_checkout_result
from app.modules.checkout.application.checkout_session_commands import checkout_session_commands
from app.modules.checkout.application.checkout_shipping_quote_commands import checkout_shipping_quote_commands


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
            "description": "Volte ao produto para iniciar uma nova sessão de checkout com itens, frete e totais atuais.",
            "helper": "Isso evita seguir com uma sessão incompleta, expirada ou desatualizada.",
            "primary_label": "Voltar ao produto",
            "primary_href": back_url,
            "secondary_label": "",
            "secondary_href": "",
        },
        "checkout-completion-session-drift": {
            "title": "Como retomar com segurança",
            "description": "Esta sessão já apontava para um pedido anterior, mas esse vínculo não está mais íntegro. Volte ao produto para criar uma sessão nova antes de seguir.",
            "helper": "Isso evita reutilizar uma sessão concluída que já não representa com segurança o pedido persistido.",
            "primary_label": "Voltar ao produto",
            "primary_href": back_url,
            "secondary_label": "",
            "secondary_href": "",
        },
        "checkout-completion-inventory-link-missing": {
            "title": "Como retomar com segurança",
            "description": "Volte ao produto para recriar o checkout a partir de uma variante vendável válida.",
            "helper": "A sessão atual não mantém um vínculo seguro para concluir este pedido inicial.",
            "primary_label": "Voltar ao produto",
            "primary_href": back_url,
            "secondary_label": "",
            "secondary_href": "",
        },
        "checkout-completion-inventory-unavailable": {
            "title": "Como retomar com segurança",
            "description": "Volte ao produto para conferir disponibilidade atual antes de tentar gerar o pedido inicial novamente.",
            "helper": "Se a variante não estiver mais disponível, a retomada segura é recomeçar pelo produto.",
            "primary_label": "Voltar ao produto",
            "primary_href": back_url,
            "secondary_label": "",
            "secondary_href": "",
        },
        "checkout-completion-stock-conflict": {
            "title": "Como retomar com segurança",
            "description": "Revise os itens afetados nesta sessão antes de tentar gerar o pedido inicial novamente.",
            "helper": "O saldo livre mudou durante o checkout; confirme a quantidade desejada sem criar pedido parcial nem ajuste silencioso.",
            "primary_label": "Reabrir checkout",
            "primary_href": retry_href,
            "secondary_label": "Voltar ao produto",
            "secondary_href": back_url,
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
        "checkout-completion-order-limit-reached": {
            "title": "Como retomar",
            "description": "Esta loja atingiu o limite mensal de pedidos pagos do plano atual.",
            "helper": "Entre em contato com a loja para concluir a compra assim que a operação liberar mais capacidade.",
            "primary_label": "Voltar ao produto",
            "primary_href": back_url,
            "secondary_label": "",
            "secondary_href": "",
        },
    }
    payload = recovery_map.get(result)
    if not payload:
        return {}
    return {"checkout_recovery": payload}


class CheckoutMetricsView(View):
    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        configured_token = str(getattr(settings, "CHECKOUT_OBSERVABILITY_TOKEN", "") or "").strip()
        if not configured_token:
            return HttpResponseNotFound("Métricas de checkout indisponíveis.")

        provided_token = str(request.headers.get("X-Hubx-Observability-Token", "") or "").strip()
        if not provided_token:
            authorization_header = str(request.headers.get("Authorization", "") or "").strip()
            if authorization_header.lower().startswith("bearer "):
                provided_token = authorization_header[7:].strip()
        if provided_token != configured_token:
            return HttpResponse("Forbidden", status=403, content_type="text/plain; charset=utf-8")

        return HttpResponse(
            checkout_metrics_queries.export_prometheus_metrics(),
            status=200,
            content_type="text/plain; version=0.0.4; charset=utf-8",
        )


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

    def _posted_checkout_payload(self, request) -> dict[str, object]:
        return {
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
        }

    def _post_includes_checkout_fields(self, request) -> bool:
        checkout_field_names = {
            "first_name",
            "last_name",
            "email",
            "phone",
            "address_line_1",
            "address_line_2",
            "city",
            "state",
            "zip_code",
            "shipping_method",
            "payment_method",
            "installments",
            "accept_terms",
        }
        return any(field_name in request.POST for field_name in checkout_field_names)

    def _save_checkout_progress(self, request, *, tenant_id: int | None, session_key: str | None) -> str:
        payload = self._posted_checkout_payload(request)
        quote_result = checkout_shipping_quote_commands.refresh_quote(
            tenant_id=tenant_id,
            session_key=str(session_key or ""),
            zip_code=payload["zip_code"],
        )
        result = checkout_session_commands.update_session(
            session_key=str(session_key or ""),
            payload=payload,
        )
        if result == "checkout-saved" and not bool(quote_result.get("ready")):
            return str(quote_result.get("result") or result)
        return result

    def _apply_demo_checkout_context(self, context: dict[str, object]) -> None:
        demo_flow = str(self.request.GET.get("demo_flow", "") or "").strip()
        if not bool(getattr(self.request, "is_demo_read_only", False)) or demo_flow not in {"checkout", "complete"}:
            return

        context["checkout_session_readonly"] = True
        context["page_meta"] = "Simulação da loja demo · nenhum pedido, pagamento ou estoque será alterado."
        context["back_url"] = f'{reverse("cart:cart-page")}?{urlencode({"demo_flow": "cart"})}'
        context["form_action"] = self.request.path
        if demo_flow == "complete":
            context.update(
                {
                    "page_title": "Pedido simulado recebido",
                    "page_description": "Esta é a confirmação demonstrativa da jornada de compra da loja demo.",
                    "checkout_feedback": {
                        "variant": "success",
                        "icon_name": "check-circle",
                        "title": "Operação simulada até o fim",
                        "description": "A experiência chegou à confirmação sem criar pedido, pagamento, carrinho ou baixa de estoque.",
                    },
                    "final_action_title": "Simulação concluída",
                    "final_action_description": "Você revisou carrinho, entrega, pagamento e confirmação usando dados demonstrativos.",
                    "final_action_helper": "As proteções de somente leitura da demo continuam bloqueando qualquer escrita real.",
                    "demo_checkout_action_href": reverse("storefront:catalog-list"),
                    "demo_checkout_action_label": "Voltar ao catálogo",
                }
            )
            return

        context.update(
            {
                "checkout_feedback": {
                    "variant": "info",
                    "icon_name": "info",
                    "title": "Checkout demonstrativo",
                    "description": "Revise entrega, pagamento e itens como exemplo da operação. O botão final apenas simula a confirmação.",
                },
                "submit_label": "Simular conclusão",
                "demo_checkout_action_href": f'{reverse("checkout:checkout-page")}?{urlencode({"demo_flow": "complete", "stage": "review"})}',
                "demo_checkout_action_label": "Simular conclusão",
            }
        )

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
            try:
                requested_quantity = int(request.POST.get("quantity", "") or 0)
            except (TypeError, ValueError):
                requested_quantity = 0
            inventory_reconciliation = str(request.POST.get("inventory_reconciliation", "") or "").strip() == "1"
            result = checkout_session_commands.mutate_item(
                session_key=str(session_key or ""),
                item_id=item_id,
                operation=operation,
                quantity=requested_quantity,
                inventory_reconciliation=inventory_reconciliation,
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
            if self._post_includes_checkout_fields(request):
                save_result = self._save_checkout_progress(
                    request,
                    tenant_id=tenant_id,
                    session_key=session_key,
                )
                if save_result != "checkout-saved":
                    fallback_stage = stage or "review"
                    if session_key:
                        payload = checkout_page_queries.get_checkout_page_data(
                            tenant_id=tenant_id,
                            session_key=session_key,
                            requested_stage=stage,
                        )
                        fallback_stage = str(payload.get("current_stage", fallback_stage))
                    params = {"back_url": back_url, "result": save_result, "stage": fallback_stage}
                    if session_key:
                        params["session_key"] = session_key
                    return HttpResponseRedirect(f'{reverse("checkout:checkout-page")}?{urlencode(params)}')
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
        result = self._save_checkout_progress(request, tenant_id=tenant_id, session_key=session_key)
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
        checkout_recovery = context.get("checkout_recovery")
        if isinstance(checkout_recovery, dict) and checkout_recovery.get("primary_label") and not checkout_recovery.get("primary_href"):
            checkout_recovery["primary_href"] = back_url
        form_params = {"back_url": back_url}
        if session_key:
            form_params["session_key"] = session_key
        if context.get("current_stage"):
            form_params["stage"] = context["current_stage"]
        context["form_action"] = f'{self.request.path}?{urlencode(form_params)}'
        if session_key:
            context["session_key"] = session_key
        self._apply_demo_checkout_context(context)
        result = self.request.GET.get("result", "").strip()
        if result:
            context["checkout_result_taxonomy"] = classify_checkout_result(result)
            record_checkout_recovery_event(
                tenant_id=tenant_id,
                result=result,
                session_key=session_key,
                stage=stage,
            )
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
        elif result == "checkout-shipping-method-invalid":
            context["checkout_feedback"] = {
                "variant": "warning",
                "icon": "🚚",
                "title": "Escolha uma entrega válida",
                "description": "Selecione uma modalidade de frete disponível nesta sessão antes de seguir para pagamento ou revisão.",
            }
        elif result == "checkout-shipping-quote-failed":
            context["checkout_feedback"] = {
                "variant": "warning",
                "icon": "🚚",
                "title": "Não foi possível calcular o frete",
                "description": "Revise o CEP informado para carregar modalidades de entrega antes de seguir.",
            }
        elif result == "checkout-shipping-quote-unavailable":
            context["checkout_feedback"] = {
                "variant": "warning",
                "icon": "🚚",
                "title": "Frete indisponível nesta sessão",
                "description": "Reabra o checkout a partir do carrinho ou produto para recalcular a entrega com segurança.",
            }
        elif result == "checkout-payment-method-invalid":
            context["checkout_feedback"] = {
                "variant": "warning",
                "icon": "💳",
                "title": "Escolha um pagamento válido",
                "description": "Selecione uma forma de pagamento disponível nesta sessão antes de seguir para revisão.",
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
            context["inventory_conflicts"] = checkout_completion_commands.get_inventory_conflicts(
                session_key=str(session_key or "")
            )
            context["checkout_feedback"] = {
                "variant": "warning",
                "icon": "⚠️",
                "title": "Estoque mudou durante o checkout",
                "description": "O saldo livre de um ou mais itens não é mais suficiente para concluir esta sessão com segurança. Revise os detalhes antes de tentar gerar o pedido inicial novamente.",
            }
        elif result == "checkout-completion-snapshot-conflict":
            context["checkout_feedback"] = {
                "variant": "warning",
                "icon": "🧾",
                "title": "Sessão mudou antes da conclusão",
                "description": "Itens ou totais desta sessão já não estão consistentes para gerar o pedido inicial. Reabra o checkout e revise os dados antes de concluir.",
            }
        elif result == "checkout-completion-order-limit-reached":
            context["checkout_feedback"] = {
                "variant": "warning",
                "icon": "🧾",
                "title": "Limite mensal da loja atingido",
                "description": "Esta loja atingiu o limite de pedidos pagos do plano atual. Nenhum pedido novo foi criado a partir desta tentativa.",
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
        elif result == "checkout-inventory-reconciled":
            context["checkout_feedback"] = {
                "variant": "success",
                "icon": "📦",
                "title": "Estoque reconciliado",
                "description": "Ajustamos este item ao estoque disponível. Revise os novos totais e tente criar o pedido inicial novamente.",
            }
        elif result == "checkout-inventory-item-removed":
            context["checkout_feedback"] = {
                "variant": "success",
                "icon": "🧺",
                "title": "Item indisponível removido",
                "description": "Removemos o item indisponível da sessão. Revise os novos totais antes de criar o pedido inicial novamente.",
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
