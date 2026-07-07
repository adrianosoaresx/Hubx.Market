from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.modules.subscriptions.models import SubscriptionPlan
from app.modules.tenants.models import Tenant, TenantOnboarding


ONBOARDING_STEPS: tuple[dict[str, str], ...] = (
    {"key": "store", "label": "Dados da loja"},
    {"key": "plan", "label": "Plano interno"},
    {"key": "owner", "label": "Owner inicial"},
    {"key": "branding", "label": "Branding mínimo"},
    {"key": "domain", "label": "Domínio"},
    {"key": "review", "label": "Revisão final"},
)


def _status_variant(status: str) -> str:
    return {
        TenantOnboarding.Status.COMPLETED: "success",
        TenantOnboarding.Status.BLOCKED: "danger",
        TenantOnboarding.Status.READY_FOR_REVIEW: "warning",
        TenantOnboarding.Status.IN_PROGRESS: "warning",
    }.get(status, "neutral")


def _money(value: object) -> str:
    try:
        return f"R$ {Decimal(str(value or '0.00')):.2f}".replace(".", ",")
    except Exception:
        return "R$ 0,00"


@dataclass
class TenantOnboardingQueryService:
    def list_onboardings(self) -> list[dict[str, object]]:
        return [self._serialize_onboarding(onboarding) for onboarding in TenantOnboarding.objects.select_related("tenant")]

    def get_onboarding(self, *, onboarding_id: int | str | None) -> dict[str, object] | None:
        try:
            normalized_id = int(onboarding_id or 0)
        except (TypeError, ValueError):
            return None
        onboarding = TenantOnboarding.objects.select_related("tenant").filter(pk=normalized_id).first()
        if onboarding is None:
            return None
        return self._serialize_onboarding(onboarding)

    def list_active_plans(self) -> list[dict[str, object]]:
        return [
            {
                "code": plan.code,
                "name": plan.name,
                "monthly_price": f"R$ {plan.monthly_price:.2f}".replace(".", ","),
                "included_api_quota": plan.included_api_quota,
            }
            for plan in SubscriptionPlan.objects.filter(status=SubscriptionPlan.Status.ACTIVE).order_by("monthly_price", "code")
        ]

    def _serialize_onboarding(self, onboarding: TenantOnboarding) -> dict[str, object]:
        completed_steps = self._completed_steps(onboarding)
        blockers = self._blockers(onboarding)
        next_step = next((step["key"] for step in ONBOARDING_STEPS if step["key"] not in completed_steps), "review")
        return {
            "id": onboarding.id,
            "status": onboarding.status,
            "status_label": onboarding.get_status_display(),
            "status_variant": _status_variant(onboarding.status),
            "tenant_id": onboarding.tenant_id,
            "tenant_slug": onboarding.tenant.slug if onboarding.tenant else "",
            "tenant_detail_href": f"/ops/platform/tenants/{onboarding.tenant.slug}/" if onboarding.tenant else "",
            "store_name": onboarding.store_name,
            "store_slug": onboarding.store_slug,
            "store_subdomain": onboarding.store_subdomain,
            "custom_domain": onboarding.custom_domain,
            "plan_code": onboarding.plan_code,
            "coupon_code_snapshot": onboarding.coupon_code_snapshot,
            "coupon_discount_type_snapshot": onboarding.coupon_discount_type_snapshot,
            "coupon_discount_value_snapshot": str(onboarding.coupon_discount_value_snapshot),
            "coupon_discount_total_snapshot": str(onboarding.coupon_discount_total_snapshot),
            "coupon_discount_total_label": _money(onboarding.coupon_discount_total_snapshot),
            "effective_monthly_price_snapshot": str(onboarding.effective_monthly_price_snapshot),
            "effective_monthly_price_label": _money(onboarding.effective_monthly_price_snapshot),
            "promotion_snapshot": onboarding.promotion_snapshot,
            "has_coupon_snapshot": bool(onboarding.coupon_code_snapshot),
            "owner_email": onboarding.owner_email,
            "owner_name": onboarding.owner_name,
            "owner_role": onboarding.owner_role or "owner",
            "store_display_name": onboarding.store_display_name,
            "primary_color": onboarding.primary_color or "#9a6410",
            "created_by_label": onboarding.created_by_label,
            "created_at": onboarding.created_at.strftime("%d/%m/%Y %H:%M"),
            "updated_at": onboarding.updated_at.strftime("%d/%m/%Y %H:%M"),
            "completed_at": onboarding.completed_at.strftime("%d/%m/%Y %H:%M") if onboarding.completed_at else "",
            "progress": int((len(completed_steps) / (len(ONBOARDING_STEPS) - 1)) * 100),
            "completed_steps": completed_steps,
            "steps": self._steps(completed_steps=completed_steps, blockers=blockers, next_step=next_step),
            "blockers": blockers,
            "next_step": next_step,
            "ready_for_completion": not blockers and {"store", "plan", "owner", "branding", "domain"}.issubset(completed_steps),
        }

    def _completed_steps(self, onboarding: TenantOnboarding) -> tuple[str, ...]:
        completed: list[str] = []
        if onboarding.store_name and onboarding.store_slug and onboarding.store_subdomain:
            completed.append("store")
        if onboarding.plan_code:
            completed.append("plan")
        if onboarding.owner_email and onboarding.owner_role:
            completed.append("owner")
        if onboarding.store_display_name and onboarding.primary_color:
            completed.append("branding")
        if onboarding.store_subdomain:
            completed.append("domain")
        return tuple(completed)

    def _blockers(self, onboarding: TenantOnboarding) -> tuple[str, ...]:
        blockers: list[str] = list(onboarding.blockers or [])
        if onboarding.status == TenantOnboarding.Status.COMPLETED:
            return tuple(blockers)
        if onboarding.store_slug and Tenant.objects.filter(slug=onboarding.store_slug).exists():
            blockers.append("store_slug_already_exists")
        if onboarding.store_subdomain and Tenant.objects.filter(subdomain=onboarding.store_subdomain).exists():
            blockers.append("store_subdomain_already_exists")
        if onboarding.custom_domain and Tenant.objects.filter(custom_domain__iexact=onboarding.custom_domain).exists():
            blockers.append("custom_domain_already_exists")
        if onboarding.plan_code and not SubscriptionPlan.objects.filter(code=onboarding.plan_code, status=SubscriptionPlan.Status.ACTIVE).exists():
            blockers.append("active_plan_not_found")
        return tuple(dict.fromkeys(blockers))

    def _steps(self, *, completed_steps: tuple[str, ...], blockers: tuple[str, ...], next_step: str) -> tuple[dict[str, object], ...]:
        return tuple(
            {
                **step,
                "completed": step["key"] in completed_steps,
                "current": step["key"] == next_step and not blockers,
            }
            for step in ONBOARDING_STEPS
        )


tenant_onboarding_queries = TenantOnboardingQueryService()
