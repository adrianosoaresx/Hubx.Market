from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from app.modules.accounts.application.admin_permissions import (
    PERMISSION_PLATFORM_TENANTS_MANAGE,
    admin_permissions,
    normalize_admin_role,
)
from app.modules.audit.application.audit_log_commands import audit_log_commands
from app.modules.subscriptions.application.subscription_coupon_queries import (
    normalize_subscription_coupon_code,
    subscription_coupon_queries,
)
from app.modules.subscriptions.models import SubscriptionAcquisitionLead, SubscriptionPlan, TenantSubscription
from app.modules.tenants.models import Tenant


def _string(value: object, *, limit: int = 180) -> str:
    return str(value or "").strip()[:limit]


def _money(value: object) -> Decimal:
    try:
        return max(Decimal(str(value or "0.00")), Decimal("0.00"))
    except Exception:
        return Decimal("0.00")


def _money_label(value: object) -> str:
    return f"R$ {_money(value):.2f}".replace(".", ",")


def _positive_int(value: object) -> int:
    try:
        return max(int(value or 0), 0)
    except (TypeError, ValueError):
        return 0


def _slug(value: object, *, limit: int) -> str:
    return slugify(_string(value, limit=limit)).strip("-")[:limit]


def _email(value: object) -> str:
    return _string(value, limit=254).lower()


def _bool(value: object) -> bool:
    return value in {True, "1", "true", "True", "on", "yes", "sim"}


def _features_text(value: object) -> str:
    if isinstance(value, (list, tuple, set)):
        lines = [_string(item, limit=220) for item in value]
    else:
        lines = [_string(line, limit=220) for line in str(value or "").splitlines()]
    return "\n".join(line for line in lines if line)[:4000]


def _billing_provider_label(provider_code: object) -> str:
    normalized = _string(provider_code, limit=64).lower()
    if normalized == "asaas":
        return "Asaas"
    if normalized == "pagarme":
        return "Pagar.me"
    return normalized.title() if normalized else ""


def _promotion_snapshot_from_validation(validation: dict[str, object] | None, *, source: str) -> dict[str, object]:
    snapshot = dict((validation or {}).get("promotion_snapshot") or {})
    if snapshot:
        snapshot["source"] = source
    return snapshot


def _promotion_snapshot_from_model(source: object, *, source_label: str) -> dict[str, object]:
    coupon_code = normalize_subscription_coupon_code(getattr(source, "coupon_code_snapshot", ""))
    if not coupon_code:
        return {}
    snapshot = dict(getattr(source, "promotion_snapshot", {}) or {})
    snapshot.update(
        {
            "coupon_code": coupon_code,
            "plan_code": _string(getattr(source, "plan_code_snapshot", "") or getattr(source, "plan_code", ""), limit=80),
            "discount_type": _string(getattr(source, "coupon_discount_type_snapshot", ""), limit=16),
            "discount_value": f"{_money(getattr(source, 'coupon_discount_value_snapshot', 0)):.2f}",
            "discount_total": f"{_money(getattr(source, 'coupon_discount_total_snapshot', 0)):.2f}",
            "effective_monthly_price": f"{_money(getattr(source, 'effective_monthly_price_snapshot', 0)):.2f}",
            "source": snapshot.get("source") or source_label,
        }
    )
    return snapshot


def _promotion_values(
    promotion_snapshot: dict[str, object] | None,
    *,
    plan: SubscriptionPlan,
    existing_subscription: TenantSubscription | None = None,
) -> dict[str, object]:
    if promotion_snapshot is None and existing_subscription is not None and existing_subscription.coupon_code_snapshot:
        return {
            "coupon_code_snapshot": existing_subscription.coupon_code_snapshot,
            "coupon_discount_type_snapshot": existing_subscription.coupon_discount_type_snapshot,
            "coupon_discount_value_snapshot": existing_subscription.coupon_discount_value_snapshot,
            "coupon_discount_total_snapshot": existing_subscription.coupon_discount_total_snapshot,
            "effective_monthly_price_snapshot": existing_subscription.effective_monthly_price_snapshot or plan.monthly_price,
            "promotion_snapshot": dict(existing_subscription.promotion_snapshot or {}),
        }

    snapshot = dict(promotion_snapshot or {})
    coupon_code = normalize_subscription_coupon_code(snapshot.get("coupon_code"))
    if not coupon_code:
        return {
            "coupon_code_snapshot": "",
            "coupon_discount_type_snapshot": "",
            "coupon_discount_value_snapshot": Decimal("0.00"),
            "coupon_discount_total_snapshot": Decimal("0.00"),
            "effective_monthly_price_snapshot": _money(plan.monthly_price),
            "promotion_snapshot": {},
        }

    monthly_price = _money(snapshot.get("monthly_price") or plan.monthly_price)
    discount_total = min(_money(snapshot.get("discount_total")), monthly_price)
    effective_price = _money(snapshot.get("effective_monthly_price") or monthly_price - discount_total)
    normalized_snapshot = {
        **snapshot,
        "coupon_code": coupon_code,
        "plan_code": _string(snapshot.get("plan_code") or plan.code, limit=80),
        "monthly_price": f"{monthly_price:.2f}",
        "discount_type": _string(snapshot.get("discount_type"), limit=16),
        "discount_value": f"{_money(snapshot.get('discount_value')):.2f}",
        "discount_total": f"{discount_total:.2f}",
        "effective_monthly_price": f"{effective_price:.2f}",
    }
    return {
        "coupon_code_snapshot": coupon_code,
        "coupon_discount_type_snapshot": normalized_snapshot["discount_type"],
        "coupon_discount_value_snapshot": _money(normalized_snapshot["discount_value"]),
        "coupon_discount_total_snapshot": discount_total,
        "effective_monthly_price_snapshot": effective_price,
        "promotion_snapshot": normalized_snapshot,
    }


def _check_platform_manage_permission(*, actor_role: object, denied_result: str) -> dict[str, object] | None:
    normalized_role = normalize_admin_role(actor_role)
    if not normalized_role:
        return {
            "result": denied_result,
            "errors": {"__all__": "Permissão platform obrigatória para gerenciar aquisições."},
        }
    permission = admin_permissions.check(role=normalized_role, permission=PERMISSION_PLATFORM_TENANTS_MANAGE)
    if not permission.allowed:
        return {
            "result": denied_result,
            "errors": {"__all__": "Permissão insuficiente para gerenciar aquisições."},
        }
    return None


class SubscriptionAcquisitionConversionBlocked(Exception):
    def __init__(self, result: str, errors: dict[str, str]):
        super().__init__(result)
        self.result = result
        self.errors = errors


@dataclass
class SubscriptionCommandService:
    def upsert_plan(
        self,
        *,
        code: object,
        name: object,
        description: object = "",
        monthly_price: object = "0.00",
        included_api_quota: object = 0,
        trial_days: object = 0,
        requires_payment_method: object = False,
        features: object = "",
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
                "description": _string(description, limit=2000),
                "monthly_price": _money(monthly_price),
                "included_api_quota": _positive_int(included_api_quota),
                "trial_days": _positive_int(trial_days),
                "requires_payment_method": _bool(requires_payment_method),
                "feature_list": _features_text(features),
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
            metadata={
                "code": plan.code,
                "status": plan.status,
                "monthly_price": str(plan.monthly_price),
                "trial_days": plan.trial_days,
                "requires_payment_method": plan.requires_payment_method,
            },
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
        promotion_snapshot: dict[str, object] | None = None,
    ) -> dict[str, object]:
        normalized_status = _string(status, limit=16) or TenantSubscription.Status.TRIALING
        if not tenant_id:
            return {"result": "tenant-subscription-tenant-required", "errors": {"tenant_id": "required"}}
        if normalized_status not in TenantSubscription.Status.values:
            return {"result": "tenant-subscription-invalid", "errors": {"status": "invalid"}}
        plan = SubscriptionPlan.objects.filter(code=_string(plan_code, limit=80).lower()).first()
        if plan is None:
            return {"result": "tenant-subscription-plan-not-found", "errors": {"plan_code": "not-found"}}
        started_at = timezone.now()
        billing_provider_code = _string(getattr(settings, "SUBSCRIPTIONS_BILLING_PROVIDER_DEFAULT", "asaas"), limit=64).lower()
        existing_subscription = TenantSubscription.objects.filter(tenant_id=tenant_id).first()
        existing_for_same_plan = existing_subscription if existing_subscription and existing_subscription.plan_id == plan.id else None
        promotion_values = _promotion_values(
            promotion_snapshot,
            plan=plan,
            existing_subscription=existing_for_same_plan,
        )
        subscription, created = TenantSubscription.objects.update_or_create(
            tenant_id=tenant_id,
            defaults={
                "plan": plan,
                "status": normalized_status,
                "external_reference": _string(external_reference),
                "billing_provider_code": billing_provider_code,
                "billing_provider_label": _billing_provider_label(billing_provider_code),
                **promotion_values,
                "started_at": started_at,
                "trial_ends_at": started_at + timedelta(days=plan.trial_days)
                if normalized_status == TenantSubscription.Status.TRIALING and plan.trial_days
                else None,
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
            metadata={
                "plan_code": plan.code,
                "status": subscription.status,
                "trial_ends_at": subscription.trial_ends_at.isoformat() if subscription.trial_ends_at else "",
                "billing_provider_code": subscription.billing_provider_code,
                "coupon_code": subscription.coupon_code_snapshot,
                "coupon_discount_total": str(subscription.coupon_discount_total_snapshot),
                "effective_monthly_price": str(subscription.effective_monthly_price_snapshot),
            },
        )
        return {
            "result": "tenant-subscription-created" if created else "tenant-subscription-updated",
            "subscription": self._subscription(subscription),
        }

    def create_public_acquisition_lead(
        self,
        *,
        payload: dict[str, object],
        actor_label: object = "public-plans",
    ) -> dict[str, object]:
        plan_code = _slug(payload.get("plan_code"), limit=80)
        store_name = _string(payload.get("store_name"), limit=150)
        desired_subdomain = _slug(payload.get("desired_subdomain") or payload.get("store_subdomain"), limit=63)
        contact_email = _email(payload.get("contact_email"))
        contact_name = _string(payload.get("contact_name"), limit=150)
        contact_phone = _string(payload.get("contact_phone"), limit=40)
        coupon_code = normalize_subscription_coupon_code(payload.get("coupon_code"))
        message = _string(payload.get("message"), limit=2000)

        errors: dict[str, str] = {}
        coupon_validation: dict[str, object] | None = None
        plan = SubscriptionPlan.objects.filter(code=plan_code, status=SubscriptionPlan.Status.ACTIVE).first()
        if plan is None:
            errors["plan_code"] = "Selecione um plano ativo."
        if not store_name:
            errors["store_name"] = "Informe o nome da loja."
        if not desired_subdomain:
            errors["desired_subdomain"] = "Informe o subdomínio desejado."
        elif Tenant.objects.filter(subdomain=desired_subdomain).exists():
            errors["desired_subdomain"] = "Este subdomínio já está em uso."
        if not contact_email or "@" not in contact_email:
            errors["contact_email"] = "Informe um e-mail válido."
        if not errors and coupon_code:
            coupon_validation = subscription_coupon_queries.validate_plan_coupon(plan_code=plan.code, coupon_code=coupon_code)
            if coupon_validation.get("result") != "subscription-coupon-valid":
                errors["coupon_code"] = str(coupon_validation.get("message") or "Cupom SaaS inválido para este plano.")
        if errors:
            return {"result": "subscription-acquisition-lead-invalid", "errors": errors}

        promotion_snapshot = _promotion_snapshot_from_validation(coupon_validation, source="public-plans")
        promotion_values = _promotion_values(promotion_snapshot, plan=plan)
        lead = SubscriptionAcquisitionLead.objects.create(
            plan=plan,
            plan_code_snapshot=plan.code,
            plan_name_snapshot=plan.name,
            plan_monthly_price_snapshot=plan.monthly_price,
            plan_currency_snapshot=plan.currency_code,
            **promotion_values,
            store_name=store_name,
            desired_subdomain=desired_subdomain,
            contact_name=contact_name,
            contact_email=contact_email,
            contact_phone=contact_phone,
            message=message,
            source=_string(payload.get("source"), limit=80) or "public-plans",
        )
        audit_result = self._record_acquisition_event(
            action="subscription.acquisition_requested",
            lead=lead,
            actor_label=actor_label,
            summary="Intenção pública de aquisição SaaS recebida.",
        )
        if audit_result.get("result") != "audit-recorded":
            lead.delete()
            return {
                "result": "subscription-acquisition-lead-audit-unavailable",
                "errors": {"__all__": "AuditLog platform-scope obrigatório para registrar aquisição."},
            }
        if lead.coupon_code_snapshot:
            coupon_audit = self._record_coupon_application_event(
                entity_type="SubscriptionAcquisitionLead",
                entity_id=lead.id,
                promotion_snapshot=lead.promotion_snapshot,
                actor_label=actor_label,
                summary="Cupom SaaS aplicado em lead público de plano.",
            )
            if coupon_audit.get("result") != "audit-recorded":
                lead.delete()
                return {
                    "result": "subscription-coupon-application-audit-unavailable",
                    "errors": {"__all__": "AuditLog platform-scope obrigatório para registrar aplicação de cupom SaaS."},
                }
        return {"result": "subscription-acquisition-lead-created", "lead": self._acquisition_lead(lead)}

    def convert_acquisition_lead_to_onboarding(
        self,
        *,
        lead_id: int | str | None,
        actor_label: object = "",
        actor_role: object = "",
    ) -> dict[str, object]:
        denied = _check_platform_manage_permission(
            actor_role=actor_role,
            denied_result="subscription-acquisition-convert-permission-denied",
        )
        if denied:
            return denied

        try:
            with transaction.atomic():
                lead = SubscriptionAcquisitionLead.objects.select_for_update().select_related("plan").filter(pk=int(lead_id or 0)).first()
                if lead is None:
                    return {"result": "subscription-acquisition-lead-not-found", "errors": {"lead_id": "Lead não encontrado."}}
                if lead.status != SubscriptionAcquisitionLead.Status.NEW:
                    return {"result": "subscription-acquisition-lead-not-convertible", "errors": {"status": "Lead não está novo."}}
                if lead.plan.status != SubscriptionPlan.Status.ACTIVE:
                    return {"result": "subscription-acquisition-lead-plan-inactive", "errors": {"plan_code": "Plano não está ativo."}}

                from app.modules.tenants.application.tenant_onboarding_commands import tenant_onboarding_commands

                onboarding_result = tenant_onboarding_commands.create_onboarding(
                    payload={
                        "store_name": lead.store_name,
                        "store_display_name": lead.store_name,
                        "primary_color": "#9a6410",
                    },
                    actor_label=actor_label,
                    actor_role=actor_role,
                )
                if onboarding_result.get("result") != "tenant-onboarding-created":
                    raise SubscriptionAcquisitionConversionBlocked(
                        str(onboarding_result.get("result") or "tenant-onboarding-create-failed"),
                        onboarding_result.get("errors") or {"__all__": "Não foi possível criar a jornada de onboarding."},
                    )
                onboarding = onboarding_result["onboarding"]
                onboarding_id = onboarding["id"]
                for step_key, step_payload in (
                    (
                        "store",
                        {
                            "store_name": lead.store_name,
                            "store_slug": lead.desired_subdomain,
                            "store_subdomain": lead.desired_subdomain,
                        },
                    ),
                    (
                        "plan",
                        {
                            "plan_code": lead.plan.code,
                            "promotion_snapshot": _promotion_snapshot_from_model(lead, source_label="public-plans"),
                        },
                    ),
                    (
                        "owner",
                        {
                            "owner_email": lead.contact_email,
                            "owner_name": lead.contact_name,
                            "owner_role": "owner",
                        },
                    ),
                    ("branding", {"store_display_name": lead.store_name, "primary_color": "#9a6410"}),
                ):
                    step_result = tenant_onboarding_commands.update_step(
                        onboarding_id=onboarding_id,
                        step_key=step_key,
                        payload=step_payload,
                        actor_label=actor_label,
                        actor_role=actor_role,
                    )
                    if step_result.get("result") != "tenant-onboarding-step-updated":
                        raise SubscriptionAcquisitionConversionBlocked(
                            str(step_result.get("result") or "tenant-onboarding-step-failed"),
                            step_result.get("errors") or {"__all__": "Não foi possível preencher a jornada de onboarding."},
                        )

                lead.status = SubscriptionAcquisitionLead.Status.CONVERTED
                lead.onboarding_id = onboarding_id
                lead.converted_at = timezone.now()
                lead.save(update_fields=["status", "onboarding", "converted_at", "updated_at"])
                audit_result = self._record_acquisition_event(
                    action="subscription.acquisition_converted",
                    lead=lead,
                    actor_label=actor_label,
                    summary="Intenção pública convertida em onboarding platform.",
                    metadata={"onboarding_id": onboarding_id},
                )
                if audit_result.get("result") != "audit-recorded":
                    raise SubscriptionAcquisitionConversionBlocked(
                        "subscription-acquisition-convert-audit-unavailable",
                        {"__all__": "AuditLog platform-scope obrigatório para converter aquisição."},
                    )
        except (TypeError, ValueError):
            return {"result": "subscription-acquisition-lead-not-found", "errors": {"lead_id": "Lead não encontrado."}}
        except SubscriptionAcquisitionConversionBlocked as error:
            return {"result": error.result, "errors": error.errors}

        return {"result": "subscription-acquisition-lead-converted", "lead": self._acquisition_lead(lead)}

    def discard_acquisition_lead(
        self,
        *,
        lead_id: int | str | None,
        actor_label: object = "",
        actor_role: object = "",
    ) -> dict[str, object]:
        denied = _check_platform_manage_permission(
            actor_role=actor_role,
            denied_result="subscription-acquisition-discard-permission-denied",
        )
        if denied:
            return denied
        try:
            lead = SubscriptionAcquisitionLead.objects.filter(pk=int(lead_id or 0)).first()
        except (TypeError, ValueError):
            lead = None
        if lead is None:
            return {"result": "subscription-acquisition-lead-not-found", "errors": {"lead_id": "Lead não encontrado."}}
        if lead.status == SubscriptionAcquisitionLead.Status.CONVERTED:
            return {"result": "subscription-acquisition-lead-not-discardable", "errors": {"status": "Lead já convertido."}}
        lead.status = SubscriptionAcquisitionLead.Status.DISCARDED
        lead.discarded_at = timezone.now()
        lead.save(update_fields=["status", "discarded_at", "updated_at"])
        audit_result = self._record_acquisition_event(
            action="subscription.acquisition_discarded",
            lead=lead,
            actor_label=actor_label,
            summary="Intenção pública de aquisição SaaS descartada.",
        )
        if audit_result.get("result") != "audit-recorded":
            return {
                "result": "subscription-acquisition-discard-audit-unavailable",
                "errors": {"__all__": "AuditLog platform-scope obrigatório para descartar aquisição."},
            }
        return {"result": "subscription-acquisition-lead-discarded", "lead": self._acquisition_lead(lead)}

    def _plan(self, plan: SubscriptionPlan) -> dict[str, object]:
        return {
            "id": plan.id,
            "code": plan.code,
            "name": plan.name,
            "monthly_price": str(plan.monthly_price),
            "trial_days": plan.trial_days,
            "requires_payment_method": plan.requires_payment_method,
            "status": plan.status,
        }

    def _subscription(self, subscription: TenantSubscription) -> dict[str, object]:
        return {
            "id": subscription.id,
            "tenant_id": subscription.tenant_id,
            "plan_code": subscription.plan.code,
            "status": subscription.status,
            "trial_ends_at": subscription.trial_ends_at.isoformat() if subscription.trial_ends_at else "",
            "billing_provider_code": subscription.billing_provider_code,
            "billing_provider_label": subscription.billing_provider_label,
            "coupon_code_snapshot": subscription.coupon_code_snapshot,
            "coupon_discount_type_snapshot": subscription.coupon_discount_type_snapshot,
            "coupon_discount_value_snapshot": str(subscription.coupon_discount_value_snapshot),
            "coupon_discount_total_snapshot": str(subscription.coupon_discount_total_snapshot),
            "effective_monthly_price_snapshot": str(subscription.effective_monthly_price_snapshot),
            "effective_monthly_price_label": _money_label(subscription.effective_monthly_price_snapshot),
            "promotion_snapshot": subscription.promotion_snapshot,
        }

    def _acquisition_lead(self, lead: SubscriptionAcquisitionLead) -> dict[str, object]:
        return {
            "id": lead.id,
            "status": lead.status,
            "plan_code": lead.plan_code_snapshot,
            "coupon_code_snapshot": lead.coupon_code_snapshot,
            "coupon_discount_type_snapshot": lead.coupon_discount_type_snapshot,
            "coupon_discount_value_snapshot": str(lead.coupon_discount_value_snapshot),
            "coupon_discount_total_snapshot": str(lead.coupon_discount_total_snapshot),
            "effective_monthly_price_snapshot": str(lead.effective_monthly_price_snapshot),
            "effective_monthly_price_label": _money_label(lead.effective_monthly_price_snapshot),
            "promotion_snapshot": lead.promotion_snapshot,
            "store_name": lead.store_name,
            "desired_subdomain": lead.desired_subdomain,
            "contact_email": lead.contact_email,
            "onboarding_id": lead.onboarding_id,
        }

    def _record_acquisition_event(
        self,
        *,
        action: str,
        lead: SubscriptionAcquisitionLead,
        actor_label: object,
        summary: str,
        metadata: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return audit_log_commands.record_event(
            tenant_id=None,
            module="subscriptions",
            action=action,
            entity_type="SubscriptionAcquisitionLead",
            entity_id=str(lead.id),
            actor_label=_string(actor_label),
            summary=summary,
            metadata={
                "lead_id": lead.id,
                "status": lead.status,
                "plan_code": lead.plan_code_snapshot,
                "desired_subdomain": lead.desired_subdomain,
                "coupon_code": lead.coupon_code_snapshot,
                "coupon_discount_total": str(lead.coupon_discount_total_snapshot),
                "effective_monthly_price": str(lead.effective_monthly_price_snapshot),
                **(metadata or {}),
            },
            allow_platform_scope=True,
        )

    def _record_coupon_application_event(
        self,
        *,
        entity_type: str,
        entity_id: int | str,
        promotion_snapshot: dict[str, object],
        actor_label: object,
        summary: str,
    ) -> dict[str, object]:
        snapshot = dict(promotion_snapshot or {})
        coupon_code = normalize_subscription_coupon_code(snapshot.get("coupon_code"))
        if not coupon_code:
            return {"result": "audit-skipped"}
        return audit_log_commands.record_event(
            tenant_id=None,
            module="subscriptions",
            action="subscription.coupon_applied",
            entity_type=entity_type,
            entity_id=str(entity_id),
            actor_label=_string(actor_label),
            summary=summary,
            metadata={
                "coupon_code": coupon_code,
                "plan_code": _string(snapshot.get("plan_code"), limit=80),
                "discount_type": _string(snapshot.get("discount_type"), limit=16),
                "discount_total": str(snapshot.get("discount_total") or ""),
                "effective_monthly_price": str(snapshot.get("effective_monthly_price") or ""),
                "source": _string(snapshot.get("source"), limit=80),
            },
            allow_platform_scope=True,
        )


subscription_commands = SubscriptionCommandService()
