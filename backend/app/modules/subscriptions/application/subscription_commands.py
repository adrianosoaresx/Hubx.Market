from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.utils import timezone

from app.modules.audit.application.audit_log_commands import audit_log_commands
from app.modules.subscriptions.models import SubscriptionPlan, TenantSubscription


def _string(value: object, *, limit: int = 180) -> str:
    return str(value or "").strip()[:limit]


def _money(value: object) -> Decimal:
    try:
        return max(Decimal(str(value or "0.00")), Decimal("0.00"))
    except Exception:
        return Decimal("0.00")


@dataclass
class SubscriptionCommandService:
    def upsert_plan(
        self,
        *,
        code: object,
        name: object,
        monthly_price: object = "0.00",
        included_api_quota: object = 0,
        status: object = SubscriptionPlan.Status.ACTIVE,
        actor_label: object = "",
    ) -> dict[str, object]:
        normalized_code = _string(code, limit=80).lower()
        normalized_name = _string(name, limit=120)
        normalized_status = _string(status, limit=16) or SubscriptionPlan.Status.ACTIVE
        if not normalized_code or not normalized_name:
            return {"result": "subscription-plan-invalid", "errors": {"code": "required", "name": "required"}}
        if normalized_status not in SubscriptionPlan.Status.values:
            return {"result": "subscription-plan-invalid", "errors": {"status": "invalid"}}
        plan, created = SubscriptionPlan.objects.update_or_create(
            code=normalized_code,
            defaults={
                "name": normalized_name,
                "monthly_price": _money(monthly_price),
                "included_api_quota": max(int(included_api_quota or 0), 0),
                "status": normalized_status,
            },
        )
        audit_log_commands.record_event(
            tenant_id=None,
            module="subscriptions",
            action="subscription.plan_upserted",
            entity_type="SubscriptionPlan",
            entity_id=str(plan.id),
            actor_label=_string(actor_label),
            summary=f"Plano SaaS atualizado: {plan.code}",
            metadata={"code": plan.code, "status": plan.status, "monthly_price": str(plan.monthly_price)},
            allow_platform_scope=True,
        )
        return {"result": "subscription-plan-created" if created else "subscription-plan-updated", "plan": self._plan(plan)}

    def set_tenant_subscription(
        self,
        *,
        tenant_id: int | str | None,
        plan_code: object,
        status: object = TenantSubscription.Status.TRIALING,
        external_reference: object = "",
        actor_label: object = "",
    ) -> dict[str, object]:
        normalized_status = _string(status, limit=16) or TenantSubscription.Status.TRIALING
        if not tenant_id:
            return {"result": "tenant-subscription-tenant-required", "errors": {"tenant_id": "required"}}
        if normalized_status not in TenantSubscription.Status.values:
            return {"result": "tenant-subscription-invalid", "errors": {"status": "invalid"}}
        plan = SubscriptionPlan.objects.filter(code=_string(plan_code, limit=80).lower()).first()
        if plan is None:
            return {"result": "tenant-subscription-plan-not-found", "errors": {"plan_code": "not-found"}}
        subscription, created = TenantSubscription.objects.update_or_create(
            tenant_id=tenant_id,
            defaults={
                "plan": plan,
                "status": normalized_status,
                "external_reference": _string(external_reference),
                "started_at": timezone.now(),
            },
        )
        audit_log_commands.record_event(
            tenant_id=tenant_id,
            module="subscriptions",
            action="tenant_subscription.updated",
            entity_type="TenantSubscription",
            entity_id=str(subscription.id),
            actor_label=_string(actor_label),
            summary=f"Assinatura SaaS atualizada para plano {plan.code}",
            metadata={"plan_code": plan.code, "status": subscription.status},
        )
        return {
            "result": "tenant-subscription-created" if created else "tenant-subscription-updated",
            "subscription": self._subscription(subscription),
        }

    def _plan(self, plan: SubscriptionPlan) -> dict[str, object]:
        return {"id": plan.id, "code": plan.code, "name": plan.name, "monthly_price": str(plan.monthly_price), "status": plan.status}

    def _subscription(self, subscription: TenantSubscription) -> dict[str, object]:
        return {
            "id": subscription.id,
            "tenant_id": subscription.tenant_id,
            "plan_code": subscription.plan.code,
            "status": subscription.status,
        }


subscription_commands = SubscriptionCommandService()
