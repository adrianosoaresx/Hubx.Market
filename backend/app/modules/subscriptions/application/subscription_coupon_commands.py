from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from django.db import connection
from django.utils.dateparse import parse_datetime

from app.modules.accounts.application.admin_permissions import (
    PERMISSION_SUBSCRIPTIONS_MANAGE,
    admin_permissions,
    normalize_admin_role,
)
from app.modules.audit.application.audit_log_commands import audit_log_commands
from app.modules.subscriptions.application.subscription_coupon_queries import normalize_subscription_coupon_code


def _string(value: object, *, limit: int = 180) -> str:
    return str(value or "").strip()[:limit]


def _decimal(value: object) -> Decimal | None:
    try:
        return max(Decimal(str(value or "").replace(",", ".")), Decimal("0.00")).quantize(Decimal("0.01"))
    except Exception:
        return None


def _datetime(value: object):
    raw_value = str(value or "").strip()
    if not raw_value:
        return None
    return parse_datetime(raw_value)


class SubscriptionCouponCommandRepository(Protocol):
    def create_coupon(
        self,
        *,
        payload: dict[str, object],
        actor_label: object = "",
        actor_role: object = "",
    ) -> dict[str, object]:
        ...

    def set_coupon_status(
        self,
        *,
        coupon_id: int | str | None,
        status: object,
        actor_label: object = "",
        actor_role: object = "",
    ) -> dict[str, object]:
        ...


class DjangoOrmSubscriptionCouponCommandRepository:
    def __init__(self) -> None:
        try:
            from app.modules.subscriptions.models import SubscriptionCoupon, SubscriptionPlan
        except Exception:
            self.coupon_model = None
            self.plan_model = None
            return
        self.coupon_model = SubscriptionCoupon
        self.plan_model = SubscriptionPlan

    def is_ready(self) -> bool:
        try:
            table_names = {self.coupon_model._meta.db_table, self.plan_model._meta.db_table}
        except Exception:
            return False
        try:
            with connection.cursor() as cursor:
                tables = set(connection.introspection.table_names(cursor))
        except Exception:
            return False
        return table_names.issubset(tables)

    def _permission_denied(self, *, actor_role: object) -> dict[str, object] | None:
        normalized_role = normalize_admin_role(actor_role)
        if not normalized_role:
            return {
                "result": "subscription-coupon-permission-denied",
                "errors": {"__all__": "Permissão platform obrigatória para gerenciar cupons SaaS."},
            }
        permission = admin_permissions.check(role=normalized_role, permission=PERMISSION_SUBSCRIPTIONS_MANAGE)
        if permission.allowed:
            return None
        return {
            "result": "subscription-coupon-permission-denied",
            "errors": {"__all__": "Permissão insuficiente para gerenciar cupons SaaS."},
        }

    def create_coupon(
        self,
        *,
        payload: dict[str, object],
        actor_label: object = "",
        actor_role: object = "",
    ) -> dict[str, object]:
        denied = self._permission_denied(actor_role=actor_role)
        if denied:
            return denied
        if not self.is_ready():
            return {"result": "subscription-coupon-admin-unavailable", "errors": {"__all__": "Admin de cupons SaaS indisponível."}}

        code = normalize_subscription_coupon_code(payload.get("code"))
        name = _string(payload.get("name"), limit=120)
        status = _string(payload.get("status"), limit=16) or self.coupon_model.Status.ACTIVE
        discount_type = _string(payload.get("discount_type"), limit=16) or self.coupon_model.DiscountType.PERCENT
        discount_value = _decimal(payload.get("discount_value"))
        starts_at = _datetime(payload.get("starts_at"))
        ends_at = _datetime(payload.get("ends_at"))
        plan_code = _string(payload.get("plan_code"), limit=80).lower()
        errors: dict[str, str] = {}
        plan = None

        if not code:
            errors["code"] = "Informe o código do cupom SaaS."
        elif self.coupon_model._default_manager.filter(code=code).exists():
            errors["code"] = "Já existe um cupom SaaS com este código."
        if status not in self.coupon_model.Status.values:
            errors["status"] = "Status inválido."
        if discount_type not in self.coupon_model.DiscountType.values:
            errors["discount_type"] = "Tipo de desconto inválido."
        if discount_value is None or discount_value <= 0:
            errors["discount_value"] = "Informe um desconto maior que zero."
        elif discount_type == self.coupon_model.DiscountType.PERCENT and discount_value > Decimal("100.00"):
            errors["discount_value"] = "Desconto percentual deve ser no máximo 100."
        if starts_at and ends_at and starts_at >= ends_at:
            errors["ends_at"] = "A data final deve ser posterior à inicial."
        if plan_code:
            plan = self.plan_model._default_manager.filter(code=plan_code).first()
            if plan is None:
                errors["plan_code"] = "Plano informado não existe."

        if errors:
            return {"result": "subscription-coupon-invalid", "errors": errors}

        coupon = self.coupon_model._default_manager.create(
            code=code,
            name=name,
            status=status,
            discount_type=discount_type,
            discount_value=discount_value,
            starts_at=starts_at,
            ends_at=ends_at,
            plan=plan,
        )
        audit_log_commands.record_event(
            tenant_id=None,
            module="subscriptions",
            action="subscription.coupon_created",
            entity_type="SubscriptionCoupon",
            entity_id=str(coupon.id),
            actor_label=_string(actor_label),
            summary=f"Cupom SaaS {coupon.code} criado.",
            metadata={
                "code": coupon.code,
                "status": coupon.status,
                "discount_type": coupon.discount_type,
                "discount_value": str(coupon.discount_value),
                "plan_code": coupon.plan.code if coupon.plan_id else "",
            },
            allow_platform_scope=True,
        )
        return {"result": "subscription-coupon-created", "coupon": {"id": coupon.id, "code": coupon.code}}

    def set_coupon_status(
        self,
        *,
        coupon_id: int | str | None,
        status: object,
        actor_label: object = "",
        actor_role: object = "",
    ) -> dict[str, object]:
        denied = self._permission_denied(actor_role=actor_role)
        if denied:
            return denied
        if not self.is_ready():
            return {"result": "subscription-coupon-admin-unavailable", "errors": {"__all__": "Admin de cupons SaaS indisponível."}}
        normalized_status = _string(status, limit=16)
        if normalized_status not in self.coupon_model.Status.values:
            return {"result": "subscription-coupon-invalid", "errors": {"status": "Status inválido."}}
        try:
            coupon = self.coupon_model._default_manager.get(pk=int(coupon_id or 0))
        except (TypeError, ValueError, self.coupon_model.DoesNotExist):
            return {"result": "subscription-coupon-not-found", "errors": {"coupon_id": "Cupom SaaS não encontrado."}}
        if coupon.status == normalized_status:
            return {"result": "subscription-coupon-status-unchanged", "coupon": {"id": coupon.id, "code": coupon.code}}

        previous_status = coupon.status
        coupon.status = normalized_status
        coupon.save(update_fields=["status", "updated_at"])
        audit_log_commands.record_event(
            tenant_id=None,
            module="subscriptions",
            action="subscription.coupon_status_changed",
            entity_type="SubscriptionCoupon",
            entity_id=str(coupon.id),
            actor_label=_string(actor_label),
            summary=f"Cupom SaaS {coupon.code} mudou para {coupon.status}.",
            metadata={"code": coupon.code, "from": previous_status, "to": coupon.status},
            allow_platform_scope=True,
        )
        return {"result": "subscription-coupon-status-updated", "coupon": {"id": coupon.id, "code": coupon.code, "status": coupon.status}}


@dataclass
class SubscriptionCouponCommandService:
    repository: SubscriptionCouponCommandRepository

    def create_coupon(self, *, payload: dict[str, object], actor_label: object = "", actor_role: object = "") -> dict[str, object]:
        return self.repository.create_coupon(payload=payload, actor_label=actor_label, actor_role=actor_role)

    def set_coupon_status(
        self,
        *,
        coupon_id: int | str | None,
        status: object,
        actor_label: object = "",
        actor_role: object = "",
    ) -> dict[str, object]:
        return self.repository.set_coupon_status(coupon_id=coupon_id, status=status, actor_label=actor_label, actor_role=actor_role)


subscription_coupon_commands = SubscriptionCouponCommandService(repository=DjangoOrmSubscriptionCouponCommandRepository())
