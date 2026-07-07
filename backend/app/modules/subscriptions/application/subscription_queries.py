from __future__ import annotations

from dataclasses import dataclass

from app.modules.subscriptions.models import SubscriptionAcquisitionLead, SubscriptionPlan, TenantSubscription


def _money(value) -> str:
    return f"R$ {value:.2f}".replace(".", ",")


def _plan_feature_lines(plan: SubscriptionPlan) -> tuple[str, ...]:
    return tuple(line.strip() for line in str(plan.feature_list or "").splitlines() if line.strip())


def _lead_status_variant(status: str) -> str:
    return {
        SubscriptionAcquisitionLead.Status.NEW: "warning",
        SubscriptionAcquisitionLead.Status.CONVERTED: "success",
        SubscriptionAcquisitionLead.Status.DISCARDED: "neutral",
    }.get(status, "neutral")


def _plan_features(plan: SubscriptionPlan) -> tuple[str, ...]:
    configured_features = _plan_feature_lines(plan)
    if configured_features:
        return configured_features
    features = ["Loja em subdomínio Hubx", "Admin tenant-owned", "Checkout e catálogo modular"]
    if plan.trial_days:
        features.append(f"{plan.trial_days} dias grátis para validar a loja")
    if plan.requires_payment_method:
        features.append("Cartão obrigatório na ativação do trial")
    if plan.included_api_quota:
        features.append(f"{plan.included_api_quota:,}".replace(",", ".") + " chamadas de API incluídas")
    if "pro" in plan.code:
        features.append("Domínio customizado contract-ready")
    if "enterprise" in plan.code:
        features.append("Acompanhamento prioritário de implantação")
    return tuple(features)


def _price_label(plan: SubscriptionPlan) -> str:
    if plan.monthly_price == 0 and plan.trial_days:
        return f"Grátis por {plan.trial_days} dias"
    if plan.monthly_price == 0:
        return "Grátis"
    return _money(plan.monthly_price)


def _billing_note(plan: SubscriptionPlan) -> str:
    if plan.requires_payment_method and plan.trial_days:
        return "Cartão obrigatório para iniciar o trial; cobrança SaaS recorrente segue fora deste MVP."
    if plan.requires_payment_method:
        return "Cartão obrigatório na ativação comercial assistida."
    if plan.trial_days:
        return f"Trial interno de {plan.trial_days} dias sem cobrança SaaS automática."
    return "Aquisição assistida sem cobrança automática nesta etapa."


def _price_caption(plan: SubscriptionPlan) -> str:
    if plan.monthly_price == 0:
        return ""
    if plan.trial_days:
        return f"/mês após {plan.trial_days} dias"
    return "/mês"


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
            }
            for plan in SubscriptionPlan.objects.order_by("monthly_price", "code")
        ]

    def list_public_plans(self) -> list[dict[str, object]]:
        plans = list(SubscriptionPlan.objects.filter(status=SubscriptionPlan.Status.ACTIVE).order_by("monthly_price", "code"))
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
                "trial_badge": f"{plan.trial_days} dias grátis" if plan.trial_days else "",
                "payment_badge": "Cartão obrigatório" if plan.requires_payment_method else "",
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
            }
            for subscription in queryset
        ]

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
