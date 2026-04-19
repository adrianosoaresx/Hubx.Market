from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from django.db import connection
from django.utils import timezone


class AccountProfileReadRepository(Protocol):
    def get_primary_profile(self) -> dict[str, object] | None:
        ...


class FallbackAccountProfileRepository:
    def get_primary_profile(self) -> dict[str, object]:
        return {
            "email": "ana@hubx.market",
            "first_name": "Ana",
            "last_name": "Souza",
            "phone": "(11) 99999-0000",
            "newsletter_opt_in": True,
            "order_updates_opt_in": True,
            "last_login_at": None,
            "last_seen_at": None,
            "is_active": True,
        }


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

    def get_primary_profile(self) -> dict[str, object] | None:
        if not self.is_ready():
            return None
        try:
            profile = self.profile_model._default_manager.filter(is_active=True).order_by("-updated_at", "-id").first()
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
        }


def _format_account_activity(profile: dict[str, object]) -> str:
    last_seen = profile.get("last_seen_at")
    last_login = profile.get("last_login_at")

    if last_seen:
        local_seen = timezone.localtime(last_seen)
        return f"Última atividade registrada em {local_seen.strftime('%d/%m/%Y às %H:%M')}."
    if last_login:
        local_login = timezone.localtime(last_login)
        return f"Último login registrado em {local_login.strftime('%d/%m/%Y às %H:%M')}."
    return "Conta pronta para começar a acompanhar pedidos, endereços e preferências."


def _display_name(profile: dict[str, object]) -> str:
    return " ".join(part for part in [profile.get("first_name", ""), profile.get("last_name", "")] if part).strip()


def _profile_trust_summary(profile: dict[str, object]) -> str:
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


def _overview_reengagement_copy() -> dict[str, str]:
    try:
        from app.modules.accounts.application.account_customer_area_queries import account_customer_area_queries
    except Exception:
        return {
            "summary_suffix": " Sua conta segue pronta para acompanhar compras e voltar quando quiser.",
            "quick_links_content": "Use estes atalhos para continuar compras, revisar endereços e manter sua conta em dia sem precisar procurar cada fluxo.",
        }

    if not account_customer_area_queries.using_persisted_orders_source():
        return {
            "summary_suffix": " Sua conta segue pronta para acompanhar compras e voltar quando quiser.",
            "quick_links_content": "Use estes atalhos para continuar compras, revisar endereços e manter sua conta em dia sem precisar procurar cada fluxo.",
        }

    orders = account_customer_area_queries.list_orders()
    total_orders = len(orders)
    latest_recent_hint = str((orders[0] if orders else {}).get("recent_update_hint") or "").lower()
    if total_orders > 1:
        recency_copy = f" Última movimentação: {latest_recent_hint}." if latest_recent_hint else ""
        return {
            "summary_suffix": f" Você já comprou mais de uma vez por aqui e sua conta está pronta para a próxima visita.{recency_copy}",
            "quick_links_content": "Use estes atalhos para revisar pedidos anteriores, conferir endereços salvos e voltar a explorar a loja com mais rapidez.",
        }
    if total_orders == 1:
        recency_copy = f" {latest_recent_hint.capitalize()}." if latest_recent_hint else ""
        return {
            "summary_suffix": f" Seu histórico já começou e a conta está pronta para facilitar a próxima compra.{recency_copy}",
            "quick_links_content": "Use estes atalhos para acompanhar seu pedido atual, revisar endereços salvos e retomar a navegação quando quiser voltar à loja.",
        }
    return {
        "summary_suffix": " Sua conta segue pronta para acompanhar compras e voltar quando quiser.",
        "quick_links_content": "Use estes atalhos para continuar compras, revisar endereços e manter sua conta em dia sem precisar procurar cada fluxo.",
    }


@dataclass
class AccountPageQueryService:
    orm_repository: AccountProfileReadRepository
    fallback_repository: AccountProfileReadRepository

    def using_persisted_source(self) -> bool:
        try:
            return self.orm_repository.get_primary_profile() is not None
        except Exception:
            return False

    def _profile(self) -> dict[str, object]:
        return self.orm_repository.get_primary_profile() or self.fallback_repository.get_primary_profile()

    def get_login_page_data(self) -> dict[str, object]:
        profile = self._profile()
        display_name = _display_name(profile)
        return {
            "page_title": "Entrar",
            "page_description": "Acesse sua conta para acompanhar pedidos, endereços salvos e preferências com segurança.",
            "login_value": profile.get("email") or "cliente@hubx.market",
            "login_label": "E-mail da conta",
            "remember_me": True,
            "helper_text": (
                f"Entre como {display_name} e continue de onde parou."
                if display_name
                else "Use o e-mail cadastrado para entrar na área do cliente."
            ),
            "primary_label": "Acessar conta",
        }

    def get_register_page_data(self) -> dict[str, object]:
        profile = self._profile()
        display_name = _display_name(profile)
        return {
            "page_title": "Criar conta",
            "page_description": "Crie sua conta para finalizar compras mais rápido, acompanhar pedidos e salvar endereços.",
            "full_name": display_name or "Ana Souza",
            "email": profile.get("email") or "ana@hubx.market",
            "primary_label": "Criar minha conta",
        }

    def get_forgot_password_page_data(self) -> dict[str, object]:
        profile = self._profile()
        return {
            "page_title": "Recuperar senha",
            "page_description": "Informe o e-mail da sua conta para receber instruções de redefinição com segurança.",
            "email": profile.get("email") or "cliente@hubx.market",
            "primary_label": "Enviar link de recuperação",
        }

    def get_reset_password_page_data(self) -> dict[str, object]:
        return {
            "page_title": "Redefinir senha",
            "page_description": "Defina uma nova senha para voltar a acessar sua conta com tranquilidade.",
            "primary_label": "Salvar e entrar",
        }

    def get_account_overview_data(self) -> dict[str, object]:
        profile = self._profile()
        reengagement_copy = _overview_reengagement_copy()
        return {
            "page_title": "Minha conta",
            "page_description": "Acompanhe seus dados, pedidos recentes e acessos rápidos da área do cliente.",
            "summary_title": "Resumo da conta",
            "summary_subtitle": "Veja rapidamente como sua conta está preparada para acompanhar compras e entregas.",
            "summary_content": f'{_profile_trust_summary(profile)}{reengagement_copy["summary_suffix"]}',
            "quick_links_content": reengagement_copy["quick_links_content"],
            "recent_orders_title": "Pedidos recentes",
            "quick_links_title": "Ações rápidas",
            "quick_links_subtitle": "Atalhos úteis para resolver o que você mais usa no dia a dia.",
            "activity_title": "Atividade recente",
            "activity_subtitle": "Sinais simples para mostrar que sua conta está pronta para acompanhar pedidos e preferências.",
            "recent_order_columns": [
                {"label": "Pedido"},
                {"label": "Status"},
                {"label": "Total"},
                {"label": "Data"},
            ],
            "recent_orders": [
                {"cells": ["#1048", "Pago", "R$ 324,80", "12/04/2026"]},
                {"cells": ["#1041", "Entregue", "R$ 189,90", "02/04/2026"]},
            ],
            "activity_content": _format_account_activity(profile),
        }


account_page_queries = AccountPageQueryService(
    orm_repository=DjangoOrmAccountProfileRepository(),
    fallback_repository=FallbackAccountProfileRepository(),
)
