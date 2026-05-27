from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from django.db import connection
from django.utils.dateparse import parse_datetime

from app.modules.accounts.application.admin_permissions import PERMISSION_COUPONS_MANAGE, admin_permissions
from app.modules.audit.application.audit_log_commands import audit_log_commands
from app.modules.coupons.application.coupon_validation_queries import normalize_coupon_code


def _decimal(value: object) -> Decimal | None:
    try:
        numeric = Decimal(str(value or "").replace(",", "."))
    except Exception:
        return None
    return numeric.quantize(Decimal("0.01"))


def _datetime(value: object):
    raw_value = str(value or "").strip()
    if not raw_value:
        return None
    return parse_datetime(raw_value)


class AdminCouponCommandRepository(Protocol):
    def create_coupon(
        self,
        *,
        tenant_id: int | str | None,
        payload: dict[str, object],
        actor_label: str = "",
        actor_role: str = "",
    ) -> dict[str, object]:
        ...


class DjangoOrmAdminCouponCommandRepository:
    def __init__(self) -> None:
        try:
            from app.modules.coupons.models import Coupon
            from app.modules.tenants.models import Tenant
        except Exception:
            self.coupon_model = None
            self.tenant_model = None
            return
        self.coupon_model = Coupon
        self.tenant_model = Tenant

    def is_ready(self) -> bool:
        try:
            table_names = {self.coupon_model._meta.db_table, self.tenant_model._meta.db_table}
        except Exception:
            return False
        try:
            with connection.cursor() as cursor:
                tables = set(connection.introspection.table_names(cursor))
        except Exception:
            return False
        return table_names.issubset(tables)

    def create_coupon(
        self,
        *,
        tenant_id: int | str | None,
        payload: dict[str, object],
        actor_label: str = "",
        actor_role: str = "",
    ) -> dict[str, object]:
        permission = admin_permissions.check(role=actor_role, permission=PERMISSION_COUPONS_MANAGE)
        if not permission.allowed:
            return {
                "result": "coupon-permission-denied",
                "errors": {"__all__": "Permissão insuficiente para criar cupom."},
            }
        if not self.is_ready():
            return {"result": "coupon-admin-unavailable", "errors": {"__all__": "Admin de cupons indisponível."}}
        if not tenant_id:
            return {"result": "coupon-tenant-required", "errors": {"__all__": "Tenant obrigatório para criar cupom."}}

        tenant = self.tenant_model._default_manager.filter(pk=tenant_id).first()
        if tenant is None:
            return {"result": "coupon-tenant-required", "errors": {"__all__": "Tenant obrigatório para criar cupom."}}

        code = normalize_coupon_code(payload.get("code"))
        name = str(payload.get("name") or "").strip()[:120]
        status = str(payload.get("status") or self.coupon_model.Status.ACTIVE).strip()
        discount_type = str(payload.get("discount_type") or self.coupon_model.DiscountType.PERCENT).strip()
        discount_value = _decimal(payload.get("discount_value"))
        starts_at = _datetime(payload.get("starts_at"))
        ends_at = _datetime(payload.get("ends_at"))
        errors: dict[str, str] = {}

        if not code:
            errors["code"] = "Informe o código do cupom."
        if status not in {self.coupon_model.Status.ACTIVE, self.coupon_model.Status.INACTIVE}:
            errors["status"] = "Status inválido."
        if discount_type not in {self.coupon_model.DiscountType.PERCENT, self.coupon_model.DiscountType.FIXED}:
            errors["discount_type"] = "Tipo de desconto inválido."
        if discount_value is None or discount_value <= 0:
            errors["discount_value"] = "Informe um desconto maior que zero."
        elif discount_type == self.coupon_model.DiscountType.PERCENT and discount_value > Decimal("100.00"):
            errors["discount_value"] = "Desconto percentual deve ser no máximo 100."
        if starts_at and ends_at and starts_at >= ends_at:
            errors["ends_at"] = "A data final deve ser posterior à inicial."
        if code and self.coupon_model._default_manager.filter(tenant=tenant, code=code).exists():
            errors["code"] = "Já existe um cupom com este código neste tenant."

        if errors:
            return {"result": "coupon-invalid", "errors": errors}

        coupon = self.coupon_model._default_manager.create(
            tenant=tenant,
            code=code,
            name=name,
            status=status,
            discount_type=discount_type,
            discount_value=discount_value,
            starts_at=starts_at,
            ends_at=ends_at,
        )
        audit_log_commands.record_event(
            tenant_id=tenant.id,
            module="coupons",
            action="coupon.created",
            entity_type="Coupon",
            entity_id=str(coupon.id),
            actor_label=actor_label,
            summary=f"Cupom {coupon.code} criado",
            metadata={
                "code": coupon.code,
                "status": coupon.status,
                "discount_type": coupon.discount_type,
                "discount_value": str(coupon.discount_value),
            },
        )
        return {"result": "coupon-created", "coupon": {"id": coupon.id, "code": coupon.code}}


@dataclass
class AdminCouponCommandService:
    repository: AdminCouponCommandRepository

    def create_coupon(
        self,
        *,
        tenant_id: int | str | None,
        payload: dict[str, object],
        actor_label: str = "",
        actor_role: str = "",
    ) -> dict[str, object]:
        return self.repository.create_coupon(
            tenant_id=tenant_id,
            payload=payload,
            actor_label=actor_label,
            actor_role=actor_role,
        )


admin_coupon_commands = AdminCouponCommandService(repository=DjangoOrmAdminCouponCommandRepository())
