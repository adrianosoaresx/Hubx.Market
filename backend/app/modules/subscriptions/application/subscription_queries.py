from __future__ import annotations

from dataclasses import dataclass

from app.modules.subscriptions.models import SubscriptionPlan, TenantSubscription


@dataclass
class SubscriptionQueryService:
    def list_plans(self) -> list[dict[str, object]]:
        return [
            {
                "code": plan.code,
                "name": plan.name,
                "status": plan.status,
                "status_label": plan.get_status_display(),
                "monthly_price": f"R$ {plan.monthly_price:.2f}".replace(".", ","),
                "included_api_quota": plan.included_api_quota,
            }
            for plan in SubscriptionPlan.objects.order_by("monthly_price", "code")
        ]

    def list_tenant_subscriptions(self, *, tenant_id: int | str | None = None) -> list[dict[str, object]]:
        queryset = TenantSubscription.objects.select_related("tenant", "plan").order_by("tenant__name", "id")
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)
        return [
            {
                "tenant_id": subscription.tenant_id,
                "tenant_name": subscription.tenant.name,
                "plan_code": subscription.plan.code,
                "plan_name": subscription.plan.name,
                "status": subscription.status,
                "status_label": subscription.get_status_display(),
                "monthly_price": f"R$ {subscription.plan.monthly_price:.2f}".replace(".", ","),
                "current_period_ends_at": subscription.current_period_ends_at.strftime("%Y-%m-%d") if subscription.current_period_ends_at else "não definido",
                "external_reference": subscription.external_reference or "manual",
            }
            for subscription in queryset
        ]


subscription_queries = SubscriptionQueryService()
