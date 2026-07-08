from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.modules.subscriptions.models import SubscriptionAcquisitionLead, SubscriptionPlan, TenantSubscription


def _money(value) -> str:
    return f"R$ {value:.2f}".replace(".", ",")


def _percent(value) -> str:
    amount = Decimal(str(value or "0.00"))
    if amount == amount.to_integral():
        return f"{int(amount)}%"
    return f"{amount:.2f}%".replace(".", ",")


def _limit_label(value: int, noun: str) -> str:
    if not value:
        return f"{noun.capitalize()} sob consulta"
    return f"Até {value:,}".replace(",", ".") + f" {noun}"


def _plan_order(plan: SubscriptionPlan) -> tuple[int, str]:
    preferred_order = {"starter": 0, "essencial": 0, "pro": 1, "enterprise": 2}
    return preferred_order.get(plan.code, 50), plan.code


def _plan_feature_lines(plan: SubscriptionPlan) -> tuple[str, ...]:
    return tuple(line.strip() for line in str(plan.feature_list or "").splitlines() if line.strip())


def _lead_status_variant(status: str) -> str:
    return {
        SubscriptionAcquisitionLead.Status.NEW: "warning",
        SubscriptionAcquisitionLead.Status.CONVERTED: "success",
        SubscriptionAcquisitionLead.Status.DISCARDED: "neutral",
    }.get(status, "neutral")


def _billing_method_label(status: str) -> str:
    return {
        TenantSubscription.BillingMethodStatus.MISSING: "Não informado",
        TenantSubscription.BillingMethodStatus.PENDING: "Pendente",
        TenantSubscription.BillingMethodStatus.ACTIVE: "Ativo",
        TenantSubscription.BillingMethodStatus.FAILED: "Falhou",
    }.get(status, "Não informado")


def _billing_method_variant(status: str) -> str:
    return {
        TenantSubscription.BillingMethodStatus.MISSING: "warning",
        TenantSubscription.BillingMethodStatus.PENDING: "warning",
        TenantSubscription.BillingMethodStatus.ACTIVE: "success",
        TenantSubscription.BillingMethodStatus.FAILED: "danger",
    }.get(status, "neutral")


def _tenant_billing_method_label(subscription: TenantSubscription) -> str:
    if not subscription.plan.requires_billing_method:
        return "Não exigido"
    return _billing_method_label(subscription.billing_method_status)


def _tenant_billing_method_variant(subscription: TenantSubscription) -> str:
    if not subscription.plan.requires_billing_method:
        return "neutral"
    return _billing_method_variant(subscription.billing_method_status)


def _plan_features(plan: SubscriptionPlan) -> tuple[str, ...]:
    configured_features = _plan_feature_lines(plan)
    if configured_features:
        return configured_features
    features = [
        _limit_label(plan.product_limit, "produtos"),
        _limit_label(plan.monthly_paid_order_limit, "pedidos pagos/mês"),
    ]
    if plan.requires_hubx_checkout:
        features.append("Checkout Hubx com taxa descontada automaticamente")
    if plan.included_api_quota:
        features.append("API de catálogo e operação incluída")
    else:
        features.append("API pública disponível a partir do Pro")
    if "pro" in plan.code:
        features.append("Domínio e customização ampliados")
        features.append("Relatórios e suporte prioritário")
    if "enterprise" in plan.code:
        features.append("Limites, SLA e implantação negociados")
    return tuple(features)


def _price_label(plan: SubscriptionPlan) -> str:
    if plan.billing_model == SubscriptionPlan.BillingModel.CUSTOM:
        return "Sob consulta"
    if plan.billing_model == SubscriptionPlan.BillingModel.MINIMUM_COMMITMENT:
        return f"{_money(plan.minimum_monthly_fee)} mínimo"
    return "R$ 0/mês"


def _billing_note(plan: SubscriptionPlan) -> str:
    if plan.billing_model == SubscriptionPlan.BillingModel.CUSTOM:
        return "Contrato, percentual, limites e implantação definidos com o time Hubx."
    fee_label = _percent(plan.platform_fee_percent)
    if plan.billing_model == SubscriptionPlan.BillingModel.MINIMUM_COMMITMENT:
        return f"Cobra o maior valor entre {_money(plan.minimum_monthly_fee)} no mês e {fee_label} dos pedidos pagos."
    return f"A Hubx recebe {fee_label} somente quando a loja vende pelo checkout integrado."


def _price_caption(plan: SubscriptionPlan) -> str:
    if plan.billing_model == SubscriptionPlan.BillingModel.CUSTOM:
        return ""
    if plan.billing_model == SubscriptionPlan.BillingModel.MINIMUM_COMMITMENT:
        return f" ou {_percent(plan.platform_fee_percent)} dos pedidos pagos"
    return f" + {_percent(plan.platform_fee_percent)} dos pedidos pagos"


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
                "trial_days": plan.trial_days,
                "requires_payment_method": plan.requires_payment_method,
                "billing_model": plan.billing_model,
                "platform_fee_percent": str(plan.platform_fee_percent),
                "minimum_monthly_fee": _money(plan.minimum_monthly_fee),
                "product_limit": plan.product_limit,
                "monthly_paid_order_limit": plan.monthly_paid_order_limit,
                "requires_hubx_checkout": plan.requires_hubx_checkout,
                "requires_billing_method": plan.requires_billing_method,
            }
            for plan in SubscriptionPlan.objects.order_by("monthly_price", "code")
        ]

    def list_public_plans(self) -> list[dict[str, object]]:
        plans = sorted(
            list(SubscriptionPlan.objects.filter(status=SubscriptionPlan.Status.ACTIVE)),
            key=_plan_order,
        )
        recommended_code = "starter" if any(plan.code == "starter" for plan in plans) else (plans[min(1, len(plans) - 1)].code if plans else "")
        return [
            {
                "code": plan.code,
                "name": plan.name,
                "description": plan.description or "Plano SaaS para operar uma loja Hubx Market com isolamento por tenant.",
                "monthly_price": _money(plan.monthly_price),
                "price_label": _price_label(plan),
                "price_caption": _price_caption(plan),
                "billing_note": _billing_note(plan),
                "currency_code": plan.currency_code,
                "included_api_quota": plan.included_api_quota,
                "trial_days": plan.trial_days,
                "requires_payment_method": plan.requires_payment_method,
                "billing_model": plan.billing_model,
                "platform_fee_percent": str(plan.platform_fee_percent),
                "minimum_monthly_fee": _money(plan.minimum_monthly_fee),
                "product_limit": plan.product_limit,
                "monthly_paid_order_limit": plan.monthly_paid_order_limit,
                "requires_hubx_checkout": plan.requires_hubx_checkout,
                "requires_billing_method": plan.requires_billing_method,
                "self_service_eligible": (
                    not plan.requires_billing_method
                    and plan.billing_model != SubscriptionPlan.BillingModel.CUSTOM
                ),
                "trial_badge": "",
                "payment_badge": "Mínimo abatível" if plan.billing_model == SubscriptionPlan.BillingModel.MINIMUM_COMMITMENT else "",
                "usage_badge": (
                    f"{_percent(plan.platform_fee_percent)} por pedido pago"
                    if plan.billing_model != SubscriptionPlan.BillingModel.CUSTOM
                    else "Contrato consultivo"
                ),
                "commercial_summary": (
                    "Sob consulta"
                    if plan.billing_model == SubscriptionPlan.BillingModel.CUSTOM
                    else f"{_money(plan.minimum_monthly_fee)} mínimo ou {_percent(plan.platform_fee_percent)} dos pedidos pagos"
                    if plan.billing_model == SubscriptionPlan.BillingModel.MINIMUM_COMMITMENT
                    else f"R$ 0/mês + {_percent(plan.platform_fee_percent)} dos pedidos pagos"
                ),
                "features": _plan_features(plan),
                "is_recommended": plan.code == recommended_code,
            }
            for plan in plans
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
                "plan_display": subscription.plan.name,
                "requires_billing_method": subscription.plan.requires_billing_method,
                "plan_billing_model": subscription.plan.billing_model,
                "status": subscription.status,
                "status_label": subscription.get_status_display(),
                "monthly_price": f"R$ {subscription.plan.monthly_price:.2f}".replace(".", ","),
                "coupon_code": subscription.coupon_code_snapshot,
                "coupon_discount_total": _money(subscription.coupon_discount_total_snapshot),
                "effective_monthly_price": _money(subscription.effective_monthly_price_snapshot or subscription.plan.monthly_price),
                "promotion_snapshot": subscription.promotion_snapshot,
                "current_period_ends_at": subscription.current_period_ends_at.strftime("%Y-%m-%d") if subscription.current_period_ends_at else "não definido",
                "external_reference": subscription.external_reference or "manual",
                "billing_provider_label": subscription.billing_provider_label or subscription.billing_provider_code or "não definido",
                "billing_method_status": subscription.billing_method_status,
                "billing_method_label": _tenant_billing_method_label(subscription),
                "billing_method_variant": _tenant_billing_method_variant(subscription),
                "has_billing_customer_reference": bool(subscription.billing_external_reference),
                "has_billing_method_reference": bool(subscription.billing_method_reference),
                "billing_checkout_url": subscription.billing_checkout_url,
                "billing_method_verified_at": subscription.billing_method_verified_at.strftime("%d/%m/%Y %H:%M") if subscription.billing_method_verified_at else "",
            }
            for subscription in queryset
        ]

    def get_tenant_subscription(self, *, tenant_id: int | str | None) -> dict[str, object] | None:
        if not tenant_id:
            return None
        subscription = (
            TenantSubscription.objects.select_related("tenant", "plan")
            .filter(tenant_id=tenant_id)
            .first()
        )
        if subscription is None:
            return None
        item = self.list_tenant_subscriptions(tenant_id=tenant_id)
        serialized = item[0] if item else {}
        serialized.update(
            {
                "billing_external_reference": subscription.billing_external_reference,
                "requires_billing_method": subscription.plan.requires_billing_method,
                "plan_billing_model": subscription.plan.billing_model,
                "minimum_monthly_fee": _money(subscription.plan.minimum_monthly_fee),
            }
        )
        return serialized

    def list_acquisition_leads(self) -> list[dict[str, object]]:
        return [
            self._serialize_acquisition_lead(lead)
            for lead in SubscriptionAcquisitionLead.objects.select_related("plan", "onboarding").order_by("-created_at", "-id")
        ]

    def get_acquisition_lead(self, *, lead_id: int | str | None) -> dict[str, object] | None:
        try:
            normalized_id = int(lead_id or 0)
        except (TypeError, ValueError):
            return None
        lead = SubscriptionAcquisitionLead.objects.select_related("plan", "onboarding").filter(pk=normalized_id).first()
        if lead is None:
            return None
        return self._serialize_acquisition_lead(lead)

    def _serialize_acquisition_lead(self, lead: SubscriptionAcquisitionLead) -> dict[str, object]:
        onboarding_id = lead.onboarding_id
        return {
            "id": lead.id,
            "status": lead.status,
            "status_label": lead.get_status_display(),
            "status_variant": _lead_status_variant(lead.status),
            "plan_code": lead.plan_code_snapshot,
            "plan_name": lead.plan_name_snapshot,
            "plan_monthly_price": _money(lead.plan_monthly_price_snapshot),
            "plan_currency": lead.plan_currency_snapshot,
            "coupon_code": lead.coupon_code_snapshot,
            "coupon_discount_type": lead.coupon_discount_type_snapshot,
            "coupon_discount_value": str(lead.coupon_discount_value_snapshot),
            "coupon_discount_total": _money(lead.coupon_discount_total_snapshot),
            "coupon_discount_total_raw": str(lead.coupon_discount_total_snapshot),
            "effective_monthly_price": _money(lead.effective_monthly_price_snapshot or lead.plan_monthly_price_snapshot),
            "effective_monthly_price_raw": str(lead.effective_monthly_price_snapshot),
            "promotion_snapshot": lead.promotion_snapshot,
            "coupon_visible": bool(lead.coupon_code_snapshot),
            "store_name": lead.store_name,
            "desired_subdomain": lead.desired_subdomain,
            "store_url_preview": f"{lead.desired_subdomain}.hubx.market",
            "contact_name": lead.contact_name,
            "contact_email": lead.contact_email,
            "contact_phone": lead.contact_phone,
            "message": lead.message,
            "source": lead.source,
            "created_at": lead.created_at.strftime("%d/%m/%Y %H:%M"),
            "updated_at": lead.updated_at.strftime("%d/%m/%Y %H:%M"),
            "converted_at": lead.converted_at.strftime("%d/%m/%Y %H:%M") if lead.converted_at else "",
            "discarded_at": lead.discarded_at.strftime("%d/%m/%Y %H:%M") if lead.discarded_at else "",
            "onboarding_id": onboarding_id,
            "onboarding_href": f"/ops/platform/onboarding/{onboarding_id}/" if onboarding_id else "",
            "detail_href": f"/ops/platform/acquisitions/{lead.id}/",
            "can_convert": lead.status == SubscriptionAcquisitionLead.Status.NEW,
            "can_discard": lead.status == SubscriptionAcquisitionLead.Status.NEW,
        }


subscription_queries = SubscriptionQueryService()
