from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from django.db import connection


def _fallback_checkout_steps() -> list[dict[str, object]]:
    return [
        {"label": "Carrinho", "state": "current"},
        {"label": "Entrega", "state": "upcoming"},
        {"label": "Pagamento", "state": "upcoming"},
        {"label": "Confirmação", "state": "upcoming"},
    ]


def _build_checkout_steps_from_session(
    *,
    current_stage: str,
    has_items: bool,
    has_shipping_address: bool,
    has_shipping_method: bool,
    has_payment_method: bool,
    accepted_terms: bool,
    status: str,
) -> list[dict[str, object]]:
    if status == "completed":
        return [
            {"label": "Carrinho", "state": "complete"},
            {"label": "Entrega", "state": "complete"},
            {"label": "Pagamento", "state": "complete"},
            {"label": "Confirmação", "state": "current"},
        ]

    delivery_complete = has_items and has_shipping_address and has_shipping_method
    payment_complete = delivery_complete and has_payment_method and accepted_terms

    return [
        {
            "label": "Carrinho",
            "state": (
                "current"
                if current_stage == "cart" or not has_items
                else "complete"
            ),
        },
        {
            "label": "Entrega",
            "state": (
                "complete"
                if delivery_complete
                else ("current" if current_stage == "delivery" else "upcoming")
            ),
        },
        {
            "label": "Pagamento",
            "state": (
                "complete"
                if payment_complete
                else ("current" if current_stage == "payment" else "upcoming")
            ),
        },
        {"label": "Confirmação", "state": "upcoming"},
    ]


def _fallback_shipping_methods() -> list[dict[str, object]]:
    return [
        {
            "value": "standard",
            "label": "Entrega padrão",
            "description": "Estimativa da modalidade: até 5 dias úteis após pagamento confirmado e preparo do pedido.",
            "price": "R$ 24,90",
            "checked": True,
        },
        {
            "value": "express",
            "label": "Entrega expressa",
            "description": "Estimativa da modalidade: até 2 dias úteis após pagamento confirmado e preparo do pedido.",
            "price": "R$ 39,90",
        },
    ]


def _fallback_payment_methods() -> list[dict[str, object]]:
    return [
        {
            "value": "credit_card",
            "label": "Cartão de crédito",
            "description": "Pagamento imediato com confirmação online.",
            "meta": "3x sem juros",
            "checked": True,
        },
        {
            "value": "pix",
            "label": "PIX",
            "description": "Aprovação rápida após a confirmação do pagamento.",
            "meta": "5% de desconto no pagamento à vista",
        },
    ]


def _fallback_order_items() -> list[dict[str, object]]:
    return [
        {
            "image_url": "https://placehold.co/240x240?text=runner",
            "image_alt": "Tênis Hubx Runner",
            "title": "Tênis Hubx Runner",
            "subtitle": "Preto · 42",
            "meta": "SKU RUNNER-001-BLK-42",
            "price": "R$ 299,90",
            "compare_price": "R$ 349,90",
            "quantity": 1,
            "quantity_readonly": True,
        },
        {
            "image_url": "https://placehold.co/240x240?text=meia",
            "image_alt": "Meia Performance",
            "title": "Meia Performance",
            "subtitle": "Pack com 3 pares",
            "meta": "SKU MP-030",
            "price": "R$ 59,90",
            "quantity": 1,
            "quantity_readonly": True,
        },
    ]


VALID_CHECKOUT_STAGES = ("cart", "delivery", "payment", "review")


class CheckoutReadRepository(Protocol):
    def get_checkout_page_data(
        self,
        tenant_id: int | None = None,
        session_key: str | None = None,
        requested_stage: str | None = None,
    ) -> dict[str, object] | None:
        ...


def _format_currency(value: object, *, negative: bool = False) -> str:
    if value in (None, ""):
        value = Decimal("0.00")
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    prefix = "-R$ " if negative and value > 0 else "R$ "
    return f"{prefix}{value:.2f}".replace(".", ",")


def _mark_selected(options: list[dict[str, object]], selected_value: str) -> list[dict[str, object]]:
    normalized = []
    for option in options:
        cloned = dict(option)
        if str(cloned.get("value", "")) == selected_value:
            cloned["checked"] = True
        else:
            cloned.pop("checked", None)
        normalized.append(cloned)
    return normalized


def _build_checkout_description(*, item_count: int, shipping_label: str, payment_label: str) -> str:
    if item_count <= 0:
        return "Sua sessão de checkout está vazia no momento."
    parts = [f"Revise {item_count} item(ns) antes de concluir o pedido."]
    if shipping_label:
        parts.append(f"Entrega selecionada: {shipping_label}.")
    if payment_label:
        parts.append(f"Pagamento selecionado: {payment_label}.")
    return " ".join(parts)


def _normalize_stage(requested_stage: str | None) -> str | None:
    normalized = str(requested_stage or "").strip().lower()
    return normalized if normalized in VALID_CHECKOUT_STAGES else None


def _build_stage_context(
    *,
    requested_stage: str | None,
    has_items: bool,
    delivery_complete: bool,
    payment_complete: bool,
) -> dict[str, object]:
    requested = _normalize_stage(requested_stage)
    redirected = False

    if not has_items:
        current_stage = "cart"
    elif requested == "delivery":
        current_stage = "delivery"
    elif requested == "payment" and not delivery_complete:
        current_stage = "delivery"
        redirected = True
    elif requested == "review" and not payment_complete:
        current_stage = "payment" if delivery_complete else "delivery"
        redirected = True
    elif requested:
        current_stage = requested
    elif has_items and not delivery_complete:
        current_stage = "cart"
    elif not delivery_complete:
        current_stage = "delivery"
    elif not payment_complete:
        current_stage = "payment"
    else:
        current_stage = "review"

    stage_labels = {
        "cart": "Carrinho",
        "delivery": "Entrega",
        "payment": "Pagamento",
        "review": "Revisão",
    }
    submit_labels = {
        "cart": "Conferir entrega",
        "delivery": "Salvar entrega e seguir",
        "payment": "Salvar pagamento e revisar",
        "review": "Criar pedido inicial",
    }
    final_action_titles = {
        "cart": "Próxima ação",
        "delivery": "Próxima ação",
        "payment": "Próxima ação",
        "review": "Ação final desta etapa",
    }
    final_action_descriptions = {
        "cart": "Confira os itens e siga para informar entrega quando a sessão representar o que você quer comprar.",
        "delivery": "Salve endereço e modalidade de frete estimada para liberar a escolha de pagamento desta sessão.",
        "payment": "Salve a forma de pagamento e o aceite para abrir uma revisão completa antes de criar o pedido.",
        "review": (
            "Ao clicar em “Criar pedido inicial”, salvaremos este pedido na sua conta e abriremos a confirmação inicial."
        ),
    }
    final_action_helpers = {
        "cart": "Nenhum pedido é criado aqui; esta etapa só organiza itens e totais.",
        "delivery": "O pedido ainda não nasce aqui; frete e prazo seguem como referência da sessão até o pagamento e o preparo avançarem.",
        "payment": "O pedido ainda não nasce aqui; esta etapa só prepara a revisão final.",
        "review": "Itens, entrega e pagamento revisados ficam registrados. O pagamento real continua pendente depois disso.",
    }
    stage_titles = {
        "cart": "Confira seu carrinho",
        "delivery": "Informe a entrega",
        "payment": "Escolha o pagamento",
        "review": "Revise antes de criar o pedido",
    }
    stage_descriptions = {
        "cart": "Ajuste itens e quantidades antes de seguir. O pedido ainda não será criado nesta etapa.",
        "delivery": "Confirme contato, endereço e frete estimado para liberar a escolha de pagamento.",
        "payment": "Escolha a forma de pagamento e aceite os termos para abrir a revisão final.",
        "review": (
            "Tudo principal já foi salvo. Ao criar o pedido inicial, itens, entrega e pagamento ficam registrados "
            "na sua conta. A confirmação real do pagamento acontece depois."
        ),
    }
    shipping_descriptions = {
        "cart": "A entrega fica disponível logo depois que você confirmar os itens desta sessão.",
        "delivery": "Preencha os dados de entrega e escolha uma modalidade de frete estimada para esta sessão.",
        "payment": "Entrega e frete estimado já podem ser revisados antes da confirmação final.",
        "review": "Entrega salva na sessão atual. O prazo continua condicionado ao pagamento confirmado e ao preparo do pedido.",
    }
    payment_descriptions = {
        "cart": "O pagamento fica disponível depois que você passar pela entrega com esta sessão pronta.",
        "delivery": "Esta etapa fica mais útil depois que entrega e frete estiverem definidos na sessão.",
        "payment": "Selecione a forma de pagamento e confirme os dados finais desta sessão.",
        "review": "Pagamento salvo na sessão atual. Revise a forma escolhida e mantenha os dados consistentes antes do próximo passo.",
    }
    review_descriptions = {
        "cart": "Use esta superfície leve para conferir itens e totais antes de abrir entrega, pagamento e revisão.",
        "delivery": "Os itens ficam aqui para orientar esta etapa enquanto você prepara entrega e frete.",
        "payment": "Com a entrega definida, use os itens e totais para revisar a compra enquanto escolhe o pagamento.",
        "review": "Revise itens, totais e parcelamento antes de gerar o pedido inicial que ficará disponível na sua conta.",
    }

    if current_stage == "cart":
        next_stage = "delivery" if has_items else "cart"
    elif current_stage == "delivery":
        next_stage = "payment" if delivery_complete else "delivery"
    elif current_stage == "payment":
        next_stage = "review" if payment_complete else "payment"
    else:
        next_stage = "review"

    stage_feedback = None
    if redirected:
        stage_feedback = {
            "variant": "info",
            "icon": "↩️",
            "title": "Etapa ajustada automaticamente",
            "description": "Abrimos a etapa que já pode ser trabalhada com segurança na sessão atual.",
        }

    return {
        "current_stage": current_stage,
        "current_stage_label": stage_labels[current_stage],
        "next_stage": next_stage,
        "submit_label": submit_labels[current_stage],
        "final_action_title": final_action_titles[current_stage],
        "final_action_description": final_action_descriptions[current_stage],
        "final_action_helper": final_action_helpers[current_stage],
        "stage_feedback": stage_feedback,
        "stage_title": stage_titles[current_stage],
        "stage_description": stage_descriptions[current_stage],
        "shipping_section_description": shipping_descriptions[current_stage],
        "payment_section_description": payment_descriptions[current_stage],
        "review_section_description": review_descriptions[current_stage],
    }


def _build_completion_hints(
    *,
    has_items: bool,
    has_shipping_address: bool,
    has_shipping_method: bool,
    has_payment_method: bool,
    accepted_terms: bool,
    current_stage: str,
) -> dict[str, object]:
    delivery_ready = has_items and has_shipping_address and has_shipping_method
    payment_ready = delivery_ready and has_payment_method and accepted_terms

    cart_hint = {
        "variant": "success" if has_items else "warning",
        "icon": "🛒" if has_items else "🧺",
        "title": "Carrinho pronto para seguir" if has_items else "Carrinho vazio",
        "description": (
            "Os itens e totais desta sessão já estão prontos para abrir a etapa de entrega."
            if has_items
            else "Adicione um item válido para liberar entrega, pagamento e revisão nesta sessão."
        ),
    }
    delivery_hint = {
        "variant": "success" if delivery_ready else "warning",
        "icon": "✅" if delivery_ready else "📝",
        "title": "Entrega salva" if delivery_ready else "Entrega ainda incompleta",
        "description": (
            "Contato, endereço e frete estimado já estão salvos nesta sessão."
            if delivery_ready
            else "Preencha contato, endereço e selecione uma modalidade de frete estimada para liberar a próxima etapa."
        ),
    }
    payment_hint = {
        "variant": "success" if payment_ready else ("info" if delivery_ready else "warning"),
        "icon": "✅" if payment_ready else ("💳" if delivery_ready else "⏳"),
        "title": "Pagamento pronto para revisão" if payment_ready else ("Pagamento em andamento" if delivery_ready else "Pagamento aguardando entrega"),
        "description": (
            "Forma de pagamento, parcelamento e termos já ficaram consistentes para revisão."
            if payment_ready
            else (
                "Agora você já pode confirmar pagamento, parcelas e termos nesta sessão."
                if delivery_ready
                else "Assim que a entrega estiver completa, o pagamento fica pronto para ser confirmado."
            )
        ),
    }
    review_hint = {
        "variant": "success" if payment_ready else "info",
        "icon": "🧾" if payment_ready else "👀",
        "title": "Revisão pronta para gerar pedido" if payment_ready else "Revisão ainda parcial",
        "description": (
            "Ao concluir agora, um pedido inicial será criado na sua conta com itens, entrega e pagamento já salvos. O pagamento ainda seguirá pendente."
            if payment_ready
            else "Os totais já aparecem aqui, mas a revisão fica mais confiável depois de concluir entrega e pagamento."
        ),
    }

    current_hint = {
        "cart": cart_hint,
        "delivery": delivery_hint,
        "payment": payment_hint,
        "review": review_hint,
    }[current_stage]

    return {
        "cart_completion_hint": cart_hint,
        "delivery_completion_hint": delivery_hint,
        "payment_completion_hint": payment_hint,
        "review_completion_hint": review_hint,
        "current_stage_completion_hint": current_hint,
        "completion_hints": [cart_hint, delivery_hint, payment_hint, review_hint],
    }


def _build_review_readiness(
    *,
    has_items: bool,
    delivery_complete: bool,
    has_payment_method: bool,
    accepted_terms: bool,
    grand_total: object,
    current_stage: str,
) -> dict[str, object]:
    try:
        total_value = Decimal(str(grand_total or "0.00"))
    except Exception:
        total_value = Decimal("0.00")

    totals_ready = has_items and total_value > 0
    review_ready = has_items and delivery_complete and has_payment_method and accepted_terms and totals_ready
    items = [
        {
            "label": "Itens confirmados na sessão",
            "ready": has_items,
            "description": "Os itens atuais já serão levados para o pedido inicial." if has_items else "Adicione itens válidos antes de concluir.",
        },
        {
            "label": "Entrega e frete salvos",
            "ready": delivery_complete,
            "description": "Contato, endereço e frete já estão consistentes nesta sessão."
            if delivery_complete
            else "Conclua contato, endereço e frete para liberar a criação do pedido.",
        },
        {
            "label": "Pagamento e termos revisados",
            "ready": has_payment_method and accepted_terms,
            "description": "Forma de pagamento e aceite já estão prontos para seguir."
            if has_payment_method and accepted_terms
            else "Confirme a forma de pagamento e o aceite para seguir com segurança.",
        },
        {
            "label": "Totais prontos para gerar o pedido",
            "ready": totals_ready,
            "description": "Os totais atuais já podem virar um pedido inicial consistente."
            if totals_ready
            else "Revise os itens e o total antes de gerar o pedido inicial.",
        },
    ]
    return {
        "review_readiness_title": "Pronto para gerar pedido inicial" if review_ready else "Ainda falta para gerar o pedido inicial",
        "review_readiness_description": (
            "Esta revisão já está consistente para criar um pedido inicial sem confirmar pagamento real."
            if review_ready
            else "Antes de gerar o pedido inicial, confirme os pontos pendentes abaixo."
        ),
        "review_readiness_items": items if current_stage == "review" else [],
    }


def _build_summary_confidence_copy(*, current_stage: str, has_items: bool) -> dict[str, str]:
    if not has_items:
        return {
            "summary_description": "O resumo ficará mais útil assim que houver itens válidos nesta sessão.",
            "summary_note": "Adicione itens para retomar entrega, pagamento e revisão com totais consistentes.",
        }

    descriptions = {
        "cart": "Confira itens, quantidades e totais antes de informar a entrega.",
        "delivery": "Use estes totais como referência enquanto define endereço e frete estimado.",
        "payment": "Revise total, frete estimado e parcelamento enquanto escolhe a forma de pagamento.",
        "review": "Confira o total que será levado para o pedido inicial salvo na sua conta.",
    }
    notes = {
        "cart": "Este resumo ainda representa uma sessão em preparação; nenhum pedido foi criado.",
        "delivery": "Frete e total podem mudar conforme endereço e modalidade escolhidos nesta etapa.",
        "payment": "O total já considera a entrega salva; prazo e envio ainda dependem de pagamento confirmado e preparo do pedido.",
        "review": (
            "Conclusão segura: itens, entrega e pagamento revisados serão levados para um pedido inicial. "
            "A confirmação real de pagamento acontece depois."
        ),
    }
    return {
        "summary_description": descriptions.get(current_stage, descriptions["cart"]),
        "summary_note": notes.get(current_stage, notes["cart"]),
    }


def _build_checkout_trust_items(*, current_stage: str) -> list[dict[str, str]]:
    items = [
        {
            "label": "Pedido só nasce na revisão",
            "description": "Entrega e pagamento podem ser salvos antes, mas o pedido inicial só é criado no último passo.",
        },
        {
            "label": "Pagamento real fica pendente",
            "description": "Criar o pedido inicial não confirma cobrança real nesta etapa.",
        },
        {
            "label": "Estoque é revalidado",
            "description": "Antes de criar o pedido, os itens passam por validação de disponibilidade.",
        },
    ]
    if current_stage == "review":
        return items
    return items[:2]


def _build_unavailable_session_payload(*, reason: str) -> dict[str, object]:
    expired = reason == "expired"
    title = "Sessão de checkout expirada" if expired else "Sessão de checkout indisponível"
    description = (
        "Esta sessão expirou por segurança. Retome a compra a partir do produto para recriar itens, entrega e pagamento."
        if expired
        else "Não encontramos uma sessão de checkout segura para este link. Retome a compra a partir do produto."
    )
    return {
        "page_title": title,
        "page_description": description,
        "page_meta": "Nenhum pedido foi criado a partir desta tela.",
        "checkout_steps": [
            {"label": "Carrinho", "state": "current"},
            {"label": "Entrega", "state": "upcoming"},
            {"label": "Pagamento", "state": "upcoming"},
            {"label": "Confirmação", "state": "upcoming"},
        ],
        "checkout_feedback": {
            "variant": "warning",
            "icon": "⏳" if expired else "ℹ️",
            "title": title,
            "description": description,
        },
        "checkout_recovery": {
            "title": "Como retomar com segurança",
            "description": "Volte ao produto para iniciar uma nova sessão de checkout com dados atuais.",
            "helper": "Isso evita reutilizar itens, frete ou totais que já não representam uma sessão ativa.",
            "primary_label": "Voltar ao produto",
            "primary_href": "",
            "secondary_label": "",
            "secondary_href": "",
        },
        "order_items": [],
        "subtotal": "R$ 0,00",
        "shipping_total": "R$ 0,00",
        "discount_total": "R$ 0,00",
        "grand_total": "R$ 0,00",
        "installments_summary": "",
        "installments_options": [],
        "summary_description": "Esta sessão não está disponível para edição.",
        "summary_note": "Retome pelo produto para gerar uma sessão nova e segura.",
        "current_stage": "cart",
        "current_stage_label": "Carrinho",
        "next_stage": "cart",
        "stage_title": title,
        "stage_description": description,
        "submit_label": "",
        "final_action_title": "Sessão bloqueada para edição",
        "final_action_description": "Não é possível salvar entrega, pagamento ou gerar pedido a partir desta sessão.",
        "final_action_helper": "Retome a compra a partir do produto para continuar.",
        "checkout_session_state": reason,
        "checkout_session_readonly": True,
        "show_cart_surface": False,
        "show_delivery_surface": False,
        "show_payment_surface": False,
        "show_order_items_surface": False,
    }


class FallbackCheckoutRepository:
    def get_checkout_page_data(
        self,
        tenant_id: int | None = None,
        session_key: str | None = None,
        requested_stage: str | None = None,
    ) -> dict[str, object]:
        payload = {
            "page_title": "Finalizar compra",
            "page_description": "Revise seus itens, informe entrega e pagamento antes de concluir o pedido.",
            "checkout_steps": _fallback_checkout_steps(),
            "first_name": "Ana",
            "last_name": "Souza",
            "email": "ana@hubx.market",
            "phone": "(11) 99999-0000",
            "address_line_1": "Rua das Laranjeiras, 100",
            "address_line_2": "Apto 42",
            "city": "São Paulo",
            "state": "SP",
            "zip_code": "01310-100",
            "shipping_methods": _fallback_shipping_methods(),
            "shipping_method_selected": "standard",
            "payment_methods": _fallback_payment_methods(),
            "payment_method_selected": "credit_card",
            "order_items": _fallback_order_items(),
            "subtotal": "R$ 359,80",
            "shipping_total": "R$ 24,90",
            "discount_total": "-R$ 20,00",
            "installments_summary": "3x de R$ 121,56 sem juros",
            "grand_total": "R$ 364,70",
            "installments_selected": "3x",
            "installments_options": [
                {"value": "1x", "label": "1x de R$ 364,70"},
                {"value": "2x", "label": "2x de R$ 182,35"},
                {"value": "3x", "label": "3x de R$ 121,56"},
            ],
            "accept_terms": True,
        }
        payload.update(
            _build_stage_context(
                requested_stage=requested_stage or "delivery",
                has_items=bool(payload["order_items"]),
                delivery_complete=True,
                payment_complete=True,
            )
        )
        payload.update(
            _build_completion_hints(
                has_items=bool(payload["order_items"]),
                has_shipping_address=True,
                has_shipping_method=True,
                has_payment_method=True,
                accepted_terms=True,
                current_stage=str(payload["current_stage"]),
            )
        )
        payload.update(
            _build_review_readiness(
                has_items=bool(payload["order_items"]),
                delivery_complete=True,
                has_payment_method=True,
                accepted_terms=True,
                grand_total=Decimal("364.70"),
                current_stage=str(payload["current_stage"]),
            )
        )
        payload.update(
            _build_summary_confidence_copy(
                current_stage=str(payload["current_stage"]),
                has_items=bool(payload["order_items"]),
            )
        )
        payload["page_description"] = f'{payload["page_description"]} {payload["stage_description"]}'
        payload["show_cart_surface"] = str(payload.get("current_stage")) == "cart"
        payload["show_delivery_surface"] = str(payload.get("current_stage")) in {"delivery", "payment", "review"}
        payload["show_payment_surface"] = str(payload.get("current_stage")) in {"delivery", "payment", "review"}
        return payload


class DjangoOrmCheckoutRepository:
    def __init__(self) -> None:
        try:
            from app.modules.checkout import models as checkout_models
        except Exception:
            self.session_model = None
            return

        self.session_model = getattr(checkout_models, "CheckoutSession", None)

    def is_ready(self) -> bool:
        if self.session_model is None:
            return False

        try:
            table_names = {
                self.session_model._meta.db_table,
                self.session_model._meta.get_field("items").related_model._meta.db_table,
            }
        except Exception:
            return False

        try:
            with connection.cursor() as cursor:
                tables = connection.introspection.table_names(cursor)
        except Exception:
            return False

        return table_names.issubset(set(tables))

    def get_checkout_page_data(
        self,
        tenant_id: int | None = None,
        session_key: str | None = None,
        requested_stage: str | None = None,
    ) -> dict[str, object] | None:
        if not self.is_ready():
            return None

        try:
            queryset = self.session_model._default_manager.prefetch_related("items")
            if tenant_id:
                queryset = queryset.filter(tenant_id=tenant_id)
            elif not session_key:
                return None
            if session_key:
                queryset = queryset.filter(session_key=session_key)
            else:
                queryset = queryset.filter(status="open")
            session = queryset.order_by("-updated_at", "-id").first()
        except Exception:
            return None

        if not session:
            return None

        return self._serialize_session(session, requested_stage=requested_stage)

    def _serialize_session(self, session: object, *, requested_stage: str | None = None) -> dict[str, object]:
        shipping_selected = str(getattr(session, "shipping_method_selected", "") or "")
        payment_selected = str(getattr(session, "payment_method_selected", "") or "")

        try:
            items = list(getattr(session, "items").all())
        except Exception:
            items = []

        shipping_methods = _mark_selected(list(getattr(session, "shipping_methods", []) or []), shipping_selected)
        payment_methods = _mark_selected(list(getattr(session, "payment_methods", []) or []), payment_selected)
        selected_shipping = next((item for item in shipping_methods if item.get("checked")), {})
        selected_payment = next((item for item in payment_methods if item.get("checked")), {})
        has_shipping_address = all(
            [
                str(getattr(session, "first_name", "") or "").strip(),
                str(getattr(session, "last_name", "") or "").strip(),
                str(getattr(session, "address_line_1", "") or "").strip(),
                str(getattr(session, "city", "") or "").strip(),
                str(getattr(session, "state", "") or "").strip(),
                str(getattr(session, "zip_code", "") or "").strip(),
            ]
        )
        session_status = str(getattr(session, "status", "open") or "open")
        accepted_terms = bool(getattr(session, "accept_terms", False))
        serialized_items = [
            self._serialize_item(item, mutable=session_status == "open")
            for item in items
        ]
        delivery_complete = bool(serialized_items) and has_shipping_address and bool(shipping_selected)
        payment_complete = delivery_complete and bool(payment_selected) and accepted_terms
        stage_context = _build_stage_context(
            requested_stage=requested_stage,
            has_items=bool(serialized_items),
            delivery_complete=delivery_complete,
            payment_complete=payment_complete,
        )
        completion_hints = _build_completion_hints(
            has_items=bool(serialized_items),
            has_shipping_address=has_shipping_address,
            has_shipping_method=bool(shipping_selected),
            has_payment_method=bool(payment_selected),
            accepted_terms=accepted_terms,
            current_stage=str(stage_context["current_stage"]),
        )
        review_readiness = _build_review_readiness(
            has_items=bool(serialized_items),
            delivery_complete=delivery_complete,
            has_payment_method=bool(payment_selected),
            accepted_terms=accepted_terms,
            grand_total=getattr(session, "grand_total", Decimal("0.00")),
            current_stage=str(stage_context["current_stage"]),
        )
        summary_confidence = _build_summary_confidence_copy(
            current_stage=str(stage_context["current_stage"]),
            has_items=bool(serialized_items),
        )
        page_description = _build_checkout_description(
            item_count=len(serialized_items),
            shipping_label=str(selected_shipping.get("label", "") or ""),
            payment_label=str(selected_payment.get("label", "") or ""),
        )

        payload = {
            "page_title": "Finalizar compra",
            "page_description": f"{page_description} {stage_context['stage_description']}",
            "page_meta": (
                "Ao concluir, você verá a confirmação inicial do pedido na sua conta."
                if str(stage_context["current_stage"]) == "review"
                else "O pedido só é gerado quando a etapa atual estiver consistente."
            ),
            "checkout_steps": _build_checkout_steps_from_session(
                current_stage=str(stage_context["current_stage"]),
                has_items=bool(serialized_items),
                has_shipping_address=has_shipping_address,
                has_shipping_method=bool(shipping_selected),
                has_payment_method=bool(payment_selected),
                accepted_terms=accepted_terms,
                status=session_status,
            ),
            "first_name": str(getattr(session, "first_name", "") or ""),
            "last_name": str(getattr(session, "last_name", "") or ""),
            "email": str(getattr(session, "email", "") or ""),
            "phone": str(getattr(session, "phone", "") or ""),
            "address_line_1": str(getattr(session, "address_line_1", "") or ""),
            "address_line_2": str(getattr(session, "address_line_2", "") or ""),
            "city": str(getattr(session, "city", "") or ""),
            "state": str(getattr(session, "state", "") or ""),
            "zip_code": str(getattr(session, "zip_code", "") or ""),
            "shipping_methods": shipping_methods,
            "shipping_method_selected": shipping_selected,
            "payment_methods": payment_methods,
            "payment_method_selected": payment_selected,
            "order_items": serialized_items,
            "subtotal": _format_currency(getattr(session, "subtotal", Decimal("0.00"))),
            "shipping_total": _format_currency(getattr(session, "shipping_total", Decimal("0.00"))),
            "discount_total": _format_currency(getattr(session, "discount_total", Decimal("0.00")), negative=True),
            "installments_summary": str(getattr(session, "installments_summary", "") or ""),
            "grand_total": _format_currency(getattr(session, "grand_total", Decimal("0.00"))),
            "installments_selected": str(getattr(session, "installments_selected", "") or ""),
            "installments_options": list(getattr(session, "installments_options", []) or []),
            "accept_terms": accepted_terms,
            "summary_description": summary_confidence["summary_description"],
            "summary_note": summary_confidence["summary_note"],
            "checkout_trust_title": "Compra com revisão segura",
            "checkout_trust_items": _build_checkout_trust_items(current_stage=str(stage_context["current_stage"])),
            "show_cart_surface": str(stage_context["current_stage"]) == "cart",
            "show_delivery_surface": str(stage_context["current_stage"]) in {"delivery", "payment", "review"},
            "show_payment_surface": str(stage_context["current_stage"]) in {"delivery", "payment", "review"},
            "show_order_items_surface": True,
            "checkout_session_state": session_status,
            "checkout_session_readonly": session_status != "open",
        }
        payload.update(stage_context)
        payload.update(completion_hints)
        payload.update(review_readiness)
        if session_status == "expired":
            payload.update(
                {
                    "page_title": "Sessão de checkout expirada",
                    "page_description": (
                        "Esta sessão expirou por segurança. Retome a compra a partir do produto para recriar itens, entrega e pagamento."
                    ),
                    "page_meta": "Nenhum pedido novo será criado a partir desta sessão expirada.",
                    "checkout_feedback": {
                        "variant": "warning",
                        "icon": "⏳",
                        "title": "Sessão de checkout expirada",
                        "description": (
                            "Esta sessão não aceita mais alterações. Inicie uma nova compra para revisar dados e totais atuais."
                        ),
                    },
                    "checkout_recovery": {
                        "title": "Como retomar com segurança",
                        "description": "Volte ao produto para iniciar uma nova sessão com disponibilidade, frete e totais atualizados.",
                        "helper": "Mantemos esta sessão apenas como referência; ela não pode mais gerar pedido.",
                        "primary_label": "Voltar ao produto",
                        "primary_href": "",
                        "secondary_label": "",
                        "secondary_href": "",
                    },
                    "stage_title": "Sessão expirada",
                    "stage_description": "Os dados abaixo são apenas referência e não podem mais ser editados.",
                    "submit_label": "",
                    "final_action_title": "Sessão bloqueada para edição",
                    "final_action_description": "Não é possível salvar entrega, pagamento ou gerar pedido a partir desta sessão.",
                    "final_action_helper": "Retome a compra a partir do produto para continuar com dados atuais.",
                    "show_cart_surface": False,
                    "show_delivery_surface": False,
                    "show_payment_surface": False,
                    "checkout_session_readonly": True,
                }
            )
        return payload

    @staticmethod
    def _serialize_item(item: object, *, mutable: bool = False) -> dict[str, object]:
        compare_price = getattr(item, "compare_price", None)
        item_id = int(getattr(item, "id", 0) or 0)
        quantity = int(getattr(item, "quantity", 1) or 1)
        mutation_actions = []
        if mutable and item_id:
            mutation_actions.append({"label": "Adicionar 1", "value": f"increment:{item_id}", "variant": "secondary"})
            if quantity > 1:
                mutation_actions.append({"label": "Diminuir 1", "value": f"decrement:{item_id}", "variant": "secondary"})
            mutation_actions.append({"label": "Remover", "value": f"remove:{item_id}", "variant": "secondary"})
        return {
            "id": item_id,
            "image_url": str(getattr(item, "image_url", "") or ""),
            "image_alt": str(getattr(item, "image_alt", "") or ""),
            "title": str(getattr(item, "title", "") or ""),
            "subtitle": str(getattr(item, "subtitle", "") or ""),
            "meta": str(getattr(item, "meta", "") or ""),
            "price": _format_currency(getattr(item, "price", Decimal("0.00"))),
            "compare_price": _format_currency(compare_price) if compare_price else "",
            "quantity": quantity,
            "quantity_readonly": bool(getattr(item, "quantity_readonly", True)),
            "mutation_actions": mutation_actions,
        }


@dataclass
class CheckoutPageQueryService:
    orm_repository: CheckoutReadRepository
    fallback_repository: CheckoutReadRepository

    def using_persisted_source(self, *, tenant_id: int | None = None) -> bool:
        try:
            if tenant_id:
                return self.orm_repository.get_checkout_page_data(tenant_id=tenant_id) is not None
            return self.orm_repository.get_checkout_page_data(session_key="11111111-1111-1111-1111-111111111111") is not None
        except Exception:
            return False

    def get_checkout_page_data(
        self,
        tenant_id: int | None = None,
        session_key: str | None = None,
        requested_stage: str | None = None,
    ) -> dict[str, object]:
        real_payload = self.orm_repository.get_checkout_page_data(
            tenant_id=tenant_id,
            session_key=session_key,
            requested_stage=requested_stage,
        )
        if not tenant_id and not session_key:
            return real_payload or {}
        if session_key and not real_payload:
            return _build_unavailable_session_payload(reason="missing")
        return real_payload or self.fallback_repository.get_checkout_page_data(
            tenant_id=tenant_id,
            session_key=session_key,
            requested_stage=requested_stage,
        )


checkout_page_queries = CheckoutPageQueryService(
    orm_repository=DjangoOrmCheckoutRepository(),
    fallback_repository=FallbackCheckoutRepository(),
)
