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
        return {
            "page_title": "Entrar",
            "page_description": "Acesse sua conta para acompanhar pedidos, perfil e preferências.",
            "login_value": "cliente@hubx.market",
            "remember_me": True,
        }

    def get_register_page_data(self) -> dict[str, object]:
        return {
            "page_title": "Criar conta",
            "page_description": "Cadastre-se para comprar, acompanhar pedidos e salvar seus dados.",
            "full_name": "Ana Souza",
            "email": "ana@hubx.market",
        }

    def get_forgot_password_page_data(self) -> dict[str, object]:
        return {
            "page_title": "Recuperar senha",
            "page_description": "Informe seu e-mail para receber instruções de redefinição.",
            "email": "cliente@hubx.market",
        }

    def get_reset_password_page_data(self) -> dict[str, object]:
        return {
            "page_title": "Redefinir senha",
            "page_description": "Defina uma nova senha para concluir o acesso à sua conta.",
        }

    def get_account_overview_data(self) -> dict[str, object]:
        profile = self._profile()
        full_name = " ".join(part for part in [profile["first_name"], profile["last_name"]] if part).strip() or profile["email"]
        summary = f"{full_name} com conta {'ativa' if profile['is_active'] else 'inativa'} e preferências sincronizadas."

        return {
            "page_title": "Minha conta",
            "page_description": "Acompanhe seus dados, pedidos recentes e acessos rápidos da área do cliente.",
            "summary_content": summary,
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
