from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from django.db import connection
from django.utils import timezone


class AccountProfileReadRepository(Protocol):
    def get_primary_profile(self, *, tenant_id: int | None = None) -> dict[str, object] | None:
        ...


class DjangoOrmAccountProfileRepository:
    def __init__(self) -> None:
        try:
            from app.modules.accounts import models as account_models
        except Exception:
            self.profile_model = None
            return

        self.profile_model = getattr(account_models, "AccountProfile", None)

    def is_ready(self) -> bool:
        if self.profile_model is None:
            return False
        try:
            table_name = self.profile_model._meta.db_table
            with connection.cursor() as cursor:
                tables = connection.introspection.table_names(cursor)
        except Exception:
            return False
        return table_name in set(tables)

    def get_primary_profile(self, *, tenant_id: int | None = None) -> dict[str, object] | None:
        if not self.is_ready():
            return None
        try:
            queryset = self.profile_model._default_manager.filter(is_active=True).order_by("-updated_at", "-id")
            if tenant_id:
                queryset = queryset.filter(tenant_id=tenant_id)
            profile = queryset.first()
        except Exception:
            return None
        if not profile:
            return None
        return {
            "email": str(getattr(profile, "email", "") or ""),
            "first_name": str(getattr(profile, "first_name", "") or ""),
            "last_name": str(getattr(profile, "last_name", "") or ""),
            "phone": str(getattr(profile, "phone", "") or ""),
            "newsletter_opt_in": bool(getattr(profile, "newsletter_opt_in", False)),
            "order_updates_opt_in": bool(getattr(profile, "order_updates_opt_in", True)),
            "last_login_at": getattr(profile, "last_login_at", None),
            "last_seen_at": getattr(profile, "last_seen_at", None),
            "is_active": bool(getattr(profile, "is_active", True)),
            "profile_mode": "persisted",
        }


def _empty_profile() -> dict[str, object]:
    return {
        "email": "",
        "first_name": "",
        "last_name": "",
        "phone": "",
        "newsletter_opt_in": False,
        "order_updates_opt_in": False,
        "last_login_at": None,
        "last_seen_at": None,
        "is_active": False,
        "profile_mode": "missing",
    }


def _profile_is_missing(profile: dict[str, object]) -> bool:
    if str(profile.get("profile_mode") or "").strip() == "missing":
        return True
    return not any(
        str(profile.get(field) or "").strip()
        for field in ("email", "first_name", "last_name", "phone")
    )


def _format_account_activity(profile: dict[str, object]) -> str:
    if _profile_is_missing(profile):
        return "Assim que um perfil persistido estiver disponível, esta área mostrará atividade recente da conta."
    last_seen = profile.get("last_seen_at")
    last_login = profile.get("last_login_at")

    if last_seen:
        local_seen = timezone.localtime(last_seen)
        return f"Última atividade registrada em {local_seen.strftime('%d/%m/%Y às %H:%M')}."
    if last_login:
        local_login = timezone.localtime(last_login)
        return f"Último login registrado em {local_login.strftime('%d/%m/%Y às %H:%M')}."
    return "Sua conta continua útil para retomar pedidos, revisar endereços e acompanhar os próximos passos quando você voltar."


def _display_name(profile: dict[str, object]) -> str:
    return " ".join(part for part in [profile.get("first_name", ""), profile.get("last_name", "")] if part).strip()


def _profile_trust_summary(profile: dict[str, object]) -> str:
    if _profile_is_missing(profile):
        return "Ainda não encontramos um perfil persistido para esta conta. Quando ele existir, esta área ficará pronta para acompanhar identidade, preferências e próximos passos."
    name = _display_name(profile) or str(profile.get("email") or "Sua conta")
    preferences = []
    if profile.get("newsletter_opt_in"):
        preferences.append("newsletter ativa")
    if profile.get("order_updates_opt_in"):
        preferences.append("atualizações de pedido ativas")
    if not preferences:
        preferences.append("preferências prontas para personalização")
    status_label = "ativa" if profile.get("is_active", True) else "inativa"
    return f"{name} com conta {status_label} e {', '.join(preferences)}."


def _overview_reengagement_copy(*, tenant_id: int | None = None) -> dict[str, str]:
    try:
        from app.modules.accounts.application.account_customer_area_queries import account_customer_area_queries
    except Exception:
        return {
            "summary_suffix": " Sua conta continua disponível para retomar pedidos, revisar detalhes e voltar à loja quando fizer sentido.",
            "quick_links_content": "Use estes atalhos para acompanhar o que importa agora, revisar sua conta e voltar à loja sem perder contexto.",
        }

    if not account_customer_area_queries.using_persisted_orders_source(tenant_id=tenant_id):
        return {
            "summary_suffix": " Sua conta continua disponível para retomar pedidos, revisar detalhes e voltar à loja quando fizer sentido.",
            "quick_links_content": "Use estes atalhos para acompanhar o que importa agora, revisar sua conta e voltar à loja sem perder contexto.",
        }

    orders = account_customer_area_queries.list_orders(tenant_id=tenant_id)
    total_orders = len(orders)
    latest_recent_hint = str((orders[0] if orders else {}).get("recent_update_hint") or "").lower()
    if total_orders > 1:
        recency_copy = f" Última movimentação: {latest_recent_hint}." if latest_recent_hint else ""
        return {
            "summary_suffix": f" Você já comprou mais de uma vez por aqui e a conta ajuda a retomar rapidamente o pedido ou o próximo retorno.{recency_copy}",
            "quick_links_content": "Use estes atalhos para revisar pedidos anteriores, conferir sua conta e voltar à loja com mais rapidez.",
        }
    if total_orders == 1:
        recency_copy = f" {latest_recent_hint.capitalize()}." if latest_recent_hint else ""
        return {
            "summary_suffix": f" Seu histórico já começou e a conta ajuda a retomar o pedido atual e a próxima visita.{recency_copy}",
            "quick_links_content": "Use estes atalhos para acompanhar seu pedido atual, revisar sua conta e retomar a navegação quando quiser voltar à loja.",
        }
    return {
        "summary_suffix": " Sua conta continua disponível para retomar pedidos, revisar detalhes e voltar à loja quando fizer sentido.",
        "quick_links_content": "Use estes atalhos para acompanhar o que importa agora, revisar sua conta e voltar à loja sem perder contexto.",
    }


def _overview_return_to_buy_copy(*, total_orders: int, status_label: str, shipping_status: str) -> dict[str, str]:
    lowered_status = str(status_label or "").lower()
    lowered_shipping = str(shipping_status or "").lower()
    if "entreg" in lowered_shipping:
        return {
            "title": "Pronta para voltar ao catálogo",
            "description": "Seu pedido já foi concluído e o catálogo continua disponível para uma próxima compra quando você quiser voltar.",
        }
    if "trânsito" in lowered_shipping or "enviado" in lowered_status:
        return {
            "title": "Catálogo segue disponível",
            "description": "Enquanto esta entrega avança, o catálogo continua disponível para a próxima compra sem perder o histórico da conta.",
        }
    if total_orders > 1:
        return {
            "title": "Conta pronta para uma nova compra",
            "description": "Seu histórico já está organizado nesta conta, e o catálogo continua disponível quando você quiser explorar a próxima compra.",
        }
    return {
        "title": "Primeira compra já registrada",
        "description": "Seu primeiro pedido já deixou a conta pronta para um próximo retorno, e o catálogo continua disponível quando você quiser comprar de novo.",
    }


def _overview_orders_context(*, tenant_id: int | None = None) -> dict[str, object]:
    fallback = {
        "page_description": "Volte à sua conta para localizar pedidos recentes, revisar sua área e retomar a loja com mais contexto.",
        "summary_subtitle": "Veja rapidamente qual é o melhor ponto de retorno da sua conta neste momento.",
        "page_meta": "Conta pronta para acompanhar pedidos e voltar ao catálogo quando fizer sentido.",
        "quick_links_subtitle": "Atalhos úteis para acompanhar pedidos, revisar sua conta e voltar à loja sem perder contexto.",
        "recent_orders": [
            {"cells": ["#1048", "Pago", "R$ 324,80", "12/04/2026"]},
            {"cells": ["#1041", "Entregue", "R$ 189,90", "02/04/2026"]},
        ],
        "activity_content": None,
    }
    try:
        from app.modules.accounts.application.account_customer_area_queries import account_customer_area_queries
    except Exception:
        return fallback

    if not account_customer_area_queries.using_persisted_orders_source(tenant_id=tenant_id):
        return fallback

    orders = account_customer_area_queries.list_orders(tenant_id=tenant_id)
    if not orders:
        return fallback

    total_orders = len(orders)
    latest_order = orders[0]
    latest_status = str(latest_order.get("order_status_label") or "Pedido em andamento")
    latest_shipping_status = str(latest_order.get("shipping_status") or "")
    latest_hint = str(latest_order.get("recent_update_hint") or "")
    next_step_hint = str(latest_order.get("next_step_hint") or "")
    continuity_hint = str(latest_order.get("reengagement_hint") or "")
    return_to_buy = _overview_return_to_buy_copy(
        total_orders=total_orders,
        status_label=latest_status,
        shipping_status=latest_shipping_status,
    )
    page_description = (
        f"Você já acompanha {total_orders} pedido{'s' if total_orders > 1 else ''} por aqui, "
        "com o pedido certo e os próximos passos mais fáceis de retomar na sua conta."
    )
    if latest_hint:
        page_description = f"{page_description} {latest_hint}."

    summary_subtitle = (
        f"Seu pedido mais recente está {latest_status.lower()} e este overview ajuda a retomar rápido o que merece atenção agora."
        if total_orders > 1
        else f"Seu primeiro pedido já aparece aqui com status {latest_status.lower()} para facilitar o retorno certo à sua conta desde agora."
    )

    recent_orders = []
    for order in orders[:2]:
        status_parts = []
        if order.get("reengagement_hint"):
            status_parts.append(str(order["reengagement_hint"]).capitalize())
        if order.get("recent_update_hint"):
            status_parts.append(str(order["recent_update_hint"]).lower())
        if order.get("order_status_label"):
            status_parts.append(str(order["order_status_label"]).lower())
        recent_orders.append(
            {
                "cells": [
                    f'#{order["order_number"]}',
                    " · ".join(part for part in status_parts if part),
                    order["total"],
                    f'Atualizado em {order["updated_at"]}',
                ]
            }
        )
    activity_content = (
        f"O melhor acompanhamento agora está no pedido mais recente, que está {latest_status.lower()}."
        + (f" {latest_hint}." if latest_hint else "")
        + (f" {next_step_hint}" if next_step_hint else "")
        + (f" Contexto atual: {continuity_hint}." if continuity_hint else "")
    ).strip()
    page_meta = (
        f'{return_to_buy["title"]} · {return_to_buy["description"]}'
        if return_to_buy["title"] and return_to_buy["description"]
        else "Conta pronta para acompanhar pedidos e voltar ao catálogo quando fizer sentido."
    )
    quick_links_subtitle = (
        f'{return_to_buy["description"]} Use os atalhos para acompanhar pedidos, revisar sua conta e voltar à loja sem perder contexto.'
        if return_to_buy["description"]
        else "Atalhos úteis para acompanhar pedidos, revisar sua conta e voltar à loja sem perder contexto."
    )
    return {
        "page_description": page_description,
        "summary_subtitle": summary_subtitle,
        "page_meta": page_meta,
        "quick_links_subtitle": quick_links_subtitle,
        "recent_orders": recent_orders,
        "activity_content": activity_content,
    }


@dataclass
class AccountPageQueryService:
    orm_repository: AccountProfileReadRepository

    def using_persisted_source(self, *, tenant_id: int | None = None) -> bool:
        try:
            return self.orm_repository.get_primary_profile(tenant_id=tenant_id) is not None
        except Exception:
            return False

    def _profile(self, *, tenant_id: int | None = None) -> dict[str, object]:
        return self.orm_repository.get_primary_profile(tenant_id=tenant_id) or _empty_profile()

    def get_login_page_data(self, *, tenant_id: int | None = None) -> dict[str, object]:
        profile = self._profile(tenant_id=tenant_id)
        display_name = _display_name(profile)
        missing_profile = _profile_is_missing(profile)
        return {
            "page_title": "Entrar",
            "page_description": "Acesse sua conta para acompanhar pedidos, endereços salvos e preferências com segurança.",
            "login_value": profile.get("email") or "",
            "login_label": "E-mail da conta",
            "remember_me": False,
            "helper_text": (
                f"Entre como {display_name} e continue de onde parou."
                if display_name
                else (
                    "Use o e-mail cadastrado para entrar na área do cliente."
                    if not missing_profile
                    else "Quando sua conta estiver vinculada a um perfil persistido, o e-mail aparecerá aqui para facilitar o acesso."
                )
            ),
            "primary_label": "Acessar conta",
            "profile_mode": profile.get("profile_mode", "missing"),
        }

    def get_register_page_data(self, *, tenant_id: int | None = None) -> dict[str, object]:
        profile = self._profile(tenant_id=tenant_id)
        display_name = _display_name(profile)
        return {
            "page_title": "Criar conta",
            "page_description": "Crie sua conta para finalizar compras mais rápido, acompanhar pedidos e salvar endereços.",
            "full_name": display_name or "",
            "email": profile.get("email") or "",
            "primary_label": "Criar minha conta",
            "profile_mode": profile.get("profile_mode", "missing"),
        }

    def get_forgot_password_page_data(self, *, tenant_id: int | None = None) -> dict[str, object]:
        profile = self._profile(tenant_id=tenant_id)
        return {
            "page_title": "Recuperar senha",
            "page_description": "Informe o e-mail da sua conta para receber instruções de redefinição com segurança.",
            "email": profile.get("email") or "",
            "primary_label": "Enviar link de recuperação",
            "profile_mode": profile.get("profile_mode", "missing"),
        }

    def get_reset_password_page_data(self, *, tenant_id: int | None = None) -> dict[str, object]:
        return {
            "page_title": "Redefinir senha",
            "page_description": "Defina uma nova senha para voltar a acessar sua conta com tranquilidade.",
            "primary_label": "Salvar e entrar",
        }

    def get_account_overview_data(self, *, tenant_id: int | None = None) -> dict[str, object]:
        profile = self._profile(tenant_id=tenant_id)
        reengagement_copy = _overview_reengagement_copy(tenant_id=tenant_id)
        orders_context = _overview_orders_context(tenant_id=tenant_id)
        missing_profile = _profile_is_missing(profile)
        return {
            "page_title": "Minha conta",
            "page_description": orders_context["page_description"],
            "page_meta": orders_context["page_meta"],
            "summary_title": "Resumo da conta",
            "summary_subtitle": (
                "Assim que um perfil persistido estiver disponível, este resumo passa a mostrar melhor o ponto de retorno, as preferências e a continuidade da conta."
                if missing_profile
                else orders_context["summary_subtitle"]
            ),
            "summary_content": f'{_profile_trust_summary(profile)}{reengagement_copy["summary_suffix"]}',
            "quick_links_content": reengagement_copy["quick_links_content"],
            "recent_orders_title": "Pedidos para acompanhar",
            "quick_links_title": "Ações rápidas",
            "quick_links_subtitle": orders_context["quick_links_subtitle"],
            "activity_title": "O que acompanhar agora",
            "activity_subtitle": "Um resumo curto para mostrar o melhor próximo retorno dentro da sua conta.",
            "recent_order_columns": [
                {"label": "Pedido"},
                {"label": "Status"},
                {"label": "Total"},
                {"label": "Data"},
            ],
            "recent_orders": orders_context["recent_orders"],
            "activity_content": orders_context["activity_content"] or _format_account_activity(profile),
            "profile_mode": profile.get("profile_mode", "missing"),
        }


account_page_queries = AccountPageQueryService(
    orm_repository=DjangoOrmAccountProfileRepository(),
)
