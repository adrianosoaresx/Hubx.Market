from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from app.modules.audit.application.audit_log_commands import audit_log_commands
from app.modules.payments.infrastructure.provider_adapters import (
    AsaasProviderAdapter,
    PlatformBillingChargeContract,
    PlatformBillingCustomerContract,
    ProviderAdapterError,
)
from app.modules.payments.models import PlatformFeeLedger
from app.modules.subscriptions.models import SubscriptionPlan, TenantSubscription


PLATFORM_FEE_EXTERNAL_REFERENCE_PREFIX = "hubx-platform-fee:"


def _string(value: object, *, limit: int = 180) -> str:
    return str(value or "").strip()[:limit]


def _money(value: object) -> Decimal:
    try:
        return Decimal(str(value or "0.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal("0.00")


def _int(value: object, *, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _platform_fee_external_reference(*, ledger_key: str) -> str:
    return f"{PLATFORM_FEE_EXTERNAL_REFERENCE_PREFIX}{_string(ledger_key)}"[:120]


def _extract_platform_fee_ledger_key(value: object) -> str:
    normalized = _string(value)
    if not normalized.startswith(PLATFORM_FEE_EXTERNAL_REFERENCE_PREFIX):
        return ""
    return normalized[len(PLATFORM_FEE_EXTERNAL_REFERENCE_PREFIX) :]


def _dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _owner_contact_email(*, tenant_id: int) -> str:
    try:
        from app.modules.accounts.models import OwnerUser
    except Exception:
        return ""
    owner = (
        OwnerUser.objects.filter(tenant_id=tenant_id, is_active=True)
        .order_by("-receives_notifications", "id")
        .first()
    )
    return _string(getattr(owner, "email", ""), limit=254)


def _asaas_platform_billing_enabled() -> bool:
    return bool(getattr(settings, "PAYMENTS_PLATFORM_BILLING_ASAAS_ENABLED", False)) and bool(
        _string(getattr(settings, "ASAAS_API_KEY", ""))
    )


def _asaas_adapter() -> AsaasProviderAdapter:
    return AsaasProviderAdapter()


@dataclass
class PlatformBillingCommandService:
    def register_external_billing_method(
        self,
        *,
        tenant_id: int | None,
        provider_customer_reference: str = "",
        provider_method_reference: str = "",
        checkout_url: str = "",
        status: str = TenantSubscription.BillingMethodStatus.PENDING,
        actor_label: str = "platform-billing",
        trusted_activation: bool = False,
    ) -> dict[str, object]:
        if not tenant_id:
            return {"result": "platform-billing-tenant-required", "errors": {"tenant_id": "required"}}
        normalized_status = _string(status, limit=16) or TenantSubscription.BillingMethodStatus.ACTIVE
        if normalized_status not in TenantSubscription.BillingMethodStatus.values:
            return {"result": "platform-billing-method-invalid", "errors": {"status": "invalid"}}
        subscription = TenantSubscription.objects.select_related("plan").filter(tenant_id=tenant_id).first()
        if subscription is None:
            return {"result": "platform-billing-subscription-not-found", "errors": {"tenant_id": "not-found"}}
        if not subscription.plan.requires_billing_method:
            return {
                "result": "platform-billing-method-not-required",
                "errors": {"__all__": "O plano atual não exige método de cobrança."},
            }
        if not trusted_activation and normalized_status == TenantSubscription.BillingMethodStatus.ACTIVE:
            return {
                "result": "platform-billing-method-unverified",
                "errors": {"status": "Método ativo exige confirmação segura do provider."},
            }
        if not trusted_activation and _string(provider_method_reference):
            return {
                "result": "platform-billing-method-reference-blocked",
                "errors": {"provider_method_reference": "Referência tokenizada não deve ser enviada por formulário livre."},
            }
        if trusted_activation and normalized_status == TenantSubscription.BillingMethodStatus.ACTIVE:
            if not _string(provider_customer_reference):
                return {
                    "result": "platform-billing-method-invalid",
                    "errors": {"provider_customer_reference": "required"},
                }
            if not _string(provider_method_reference):
                return {
                    "result": "platform-billing-method-invalid",
                    "errors": {"provider_method_reference": "required"},
                }

        updates = {
            "billing_provider_code": subscription.billing_provider_code or "asaas",
            "billing_provider_label": subscription.billing_provider_label or "Asaas",
            "billing_method_status": normalized_status,
            "billing_checkout_url": _string(checkout_url, limit=500),
        }
        if trusted_activation:
            updates["billing_method_reference"] = _string(provider_method_reference)
        customer_reference = _string(provider_customer_reference)
        if customer_reference:
            updates["billing_external_reference"] = customer_reference
        if normalized_status == TenantSubscription.BillingMethodStatus.ACTIVE:
            updates["billing_method_verified_at"] = timezone.now()
        else:
            updates["billing_method_verified_at"] = None

        for field, value in updates.items():
            setattr(subscription, field, value)
        subscription.save(update_fields=[*updates.keys(), "updated_at"])
        self._record_subscription_audit(
            subscription=subscription,
            action="tenant_subscription.billing_method_registered",
            actor_label=actor_label,
            summary="Método de cobrança externo registrado para billing SaaS.",
        )
        return {"result": "platform-billing-method-registered", "subscription_id": subscription.id}

    def ensure_tenant_billing_customer(
        self,
        *,
        tenant_id: int | None,
        actor_label: str = "platform-billing",
    ) -> tuple[str, TenantSubscription | None]:
        if not tenant_id:
            return "platform-billing-tenant-required", None
        subscription = (
            TenantSubscription.objects.select_related("tenant", "plan")
            .filter(tenant_id=tenant_id)
            .first()
        )
        if subscription is None:
            return "platform-billing-subscription-not-found", None
        if not subscription.plan.requires_billing_method:
            return "platform-billing-method-not-required", subscription
        if _string(subscription.billing_external_reference):
            return "platform-billing-customer-existing", subscription
        if not _asaas_platform_billing_enabled():
            return "platform-billing-provider-disabled", subscription

        tenant = subscription.tenant
        contract = PlatformBillingCustomerContract(
            tenant_id=int(tenant_id),
            tenant_slug=_string(getattr(tenant, "slug", ""), limit=150),
            tenant_name=_string(getattr(tenant, "name", ""), limit=150),
            contact_email=_owner_contact_email(tenant_id=int(tenant_id)),
        )
        try:
            response = _asaas_adapter().create_platform_billing_customer(contract=contract)
        except ProviderAdapterError as exc:
            self._record_subscription_audit(
                subscription=subscription,
                action="tenant_subscription.billing_customer_failed",
                actor_label=actor_label,
                summary="Falha ao criar cliente de billing no Asaas.",
                metadata={"reason_code": str(exc)},
            )
            return "platform-billing-customer-failed", subscription

        subscription.billing_provider_code = response.provider_code
        subscription.billing_provider_label = response.provider_label
        subscription.billing_external_reference = response.customer_reference
        if subscription.billing_method_status == TenantSubscription.BillingMethodStatus.MISSING:
            subscription.billing_method_status = TenantSubscription.BillingMethodStatus.PENDING
        subscription.save(
            update_fields=[
                "billing_provider_code",
                "billing_provider_label",
                "billing_external_reference",
                "billing_method_status",
                "updated_at",
            ]
        )
        self._record_subscription_audit(
            subscription=subscription,
            action="tenant_subscription.billing_customer_created",
            actor_label=actor_label,
            summary="Cliente de billing criado no Asaas para cobrança SaaS.",
            metadata={"provider_response": response.payload_snapshot},
        )
        return "platform-billing-customer-created", subscription

    def create_complementary_charge_for_ledger(
        self,
        *,
        ledger_id: int | None = None,
        ledger_key: str = "",
        actor_label: str = "platform-billing",
        force: bool = False,
    ) -> tuple[str, PlatformFeeLedger | None]:
        if not _asaas_platform_billing_enabled() and not force:
            return "platform-billing-provider-disabled", None
        ledger = self._get_collectable_ledger(ledger_id=ledger_id, ledger_key=ledger_key)
        if ledger is None:
            return "platform-billing-ledger-not-found", None
        if ledger.kind != PlatformFeeLedger.Kind.PRO_MINIMUM_ADJUSTMENT:
            return "platform-billing-ledger-not-collectable", ledger
        if ledger.status == PlatformFeeLedger.Status.PAID:
            return "platform-billing-ledger-paid", ledger
        if _string(ledger.provider_payment_reference):
            return "platform-billing-charge-existing", ledger
        if _money(ledger.fee_amount) <= Decimal("0.00"):
            return "platform-billing-ledger-empty", ledger

        customer_result, subscription = self.ensure_tenant_billing_customer(
            tenant_id=ledger.tenant_id,
            actor_label=actor_label,
        )
        if subscription is None:
            return customer_result, ledger
        customer_reference = _string(subscription.billing_external_reference)
        if not customer_reference:
            return customer_result, ledger
        if not _asaas_platform_billing_enabled() and force:
            return "platform-billing-provider-disabled", ledger

        due_days = max(_int(getattr(settings, "ASAAS_PLATFORM_BILLING_DUE_DAYS", 3), default=3), 0)
        due_date = timezone.localdate() + timedelta(days=due_days)
        contract = PlatformBillingChargeContract(
            tenant_id=ledger.tenant_id,
            tenant_slug=_string(getattr(subscription.tenant, "slug", ""), limit=150),
            ledger_key=ledger.ledger_key,
            customer_reference=customer_reference,
            amount=f"{_money(ledger.fee_amount):.2f}",
            currency_code=ledger.currency_code or "BRL",
            due_date=due_date.isoformat(),
            description=f"Complemento mensal Hubx Market - {ledger.billing_period_start:%m/%Y}",
            external_reference=_platform_fee_external_reference(ledger_key=ledger.ledger_key),
            billing_method_reference=(
                _string(subscription.billing_method_reference)
                if subscription.billing_method_status == TenantSubscription.BillingMethodStatus.ACTIVE
                else ""
            ),
            remote_ip=_string(getattr(settings, "ASAAS_PLATFORM_BILLING_REMOTE_IP", "")),
        )
        try:
            response = _asaas_adapter().create_platform_billing_charge(contract=contract)
        except ProviderAdapterError as exc:
            metadata = dict(ledger.metadata or {})
            metadata["provider_call"] = "failed"
            metadata["provider_error"] = str(exc)
            ledger.metadata = metadata
            ledger.save(update_fields=["metadata", "updated_at"])
            self._record_ledger_audit(
                ledger=ledger,
                action="platform_fee.complementary_charge_failed",
                actor_label=actor_label,
                summary="Falha ao criar cobrança complementar Asaas.",
            )
            return "platform-billing-charge-failed", ledger

        metadata = dict(ledger.metadata or {})
        metadata.update(
            {
                "collection_mode": "asaas_complementary_charge",
                "provider_call": "executed",
                "billing_checkout_url": response.action_url,
                "provider_response": response.payload_snapshot,
                "billing_method_status": subscription.billing_method_status,
            }
        )
        with transaction.atomic():
            locked_ledger = PlatformFeeLedger.objects.select_for_update().get(pk=ledger.pk)
            if _string(locked_ledger.provider_payment_reference):
                return "platform-billing-charge-existing", locked_ledger
            locked_ledger.provider_code = response.provider_code
            locked_ledger.provider_payment_reference = response.payment_reference
            locked_ledger.metadata = metadata
            locked_ledger.status = PlatformFeeLedger.Status.PENDING_COLLECTION
            locked_ledger.save(
                update_fields=[
                    "provider_code",
                    "provider_payment_reference",
                    "metadata",
                    "status",
                    "updated_at",
                ]
            )
            subscription.billing_checkout_url = response.action_url
            if subscription.billing_method_status == TenantSubscription.BillingMethodStatus.MISSING:
                subscription.billing_method_status = TenantSubscription.BillingMethodStatus.PENDING
            subscription.save(
                update_fields=[
                    "billing_checkout_url",
                    "billing_method_status",
                    "updated_at",
                ]
            )
        self._record_ledger_audit(
            ledger=locked_ledger,
            action="platform_fee.complementary_charge_created",
            actor_label=actor_label,
            summary="Cobrança complementar Asaas criada para mínimo Pro.",
        )
        return "platform-billing-charge-created", locked_ledger

    def process_platform_fee_webhook(
        self,
        *,
        payload: dict[str, object],
        actor_label: str = "payments-webhook",
    ) -> tuple[str, int] | None:
        event_type = _string(payload.get("event") or payload.get("type")).upper()
        payment = _dict(payload.get("payment"))
        ledger_key = _extract_platform_fee_ledger_key(payment.get("externalReference"))
        if not ledger_key:
            return None
        paid_events = {"PAYMENT_RECEIVED", "PAYMENT_CONFIRMED"}
        failed_events = {"PAYMENT_OVERDUE", "PAYMENT_DELETED", "PAYMENT_REFUNDED", "PAYMENT_CHARGEBACK_REQUESTED"}
        if event_type not in paid_events | failed_events:
            return "platform-billing-webhook-unsupported-event", 400
        ledger = PlatformFeeLedger.objects.filter(ledger_key=ledger_key).first()
        if ledger is None:
            return "platform-billing-webhook-ledger-not-found", 404
        metadata = dict(ledger.metadata or {})
        metadata["last_provider_event"] = event_type
        metadata["last_provider_payment"] = {
            "id": _string(payment.get("id"), limit=120),
            "status": _string(payment.get("status"), limit=64),
            "received_at": timezone.now().isoformat(),
        }
        if event_type in paid_events:
            ledger.status = PlatformFeeLedger.Status.PAID
            result = "platform-billing-charge-paid"
            action = "platform_fee.complementary_charge_paid"
            summary = "Cobrança complementar Asaas confirmada."
        else:
            ledger.status = PlatformFeeLedger.Status.PENDING_COLLECTION
            result = "platform-billing-charge-pending"
            action = "platform_fee.complementary_charge_pending"
            summary = "Cobrança complementar Asaas exige tratativa."
        if _string(payment.get("id")) and not ledger.provider_payment_reference:
            ledger.provider_payment_reference = _string(payment.get("id"), limit=120)
        ledger.metadata = metadata
        ledger.save(update_fields=["status", "provider_payment_reference", "metadata", "updated_at"])
        self._record_ledger_audit(
            ledger=ledger,
            action=action,
            actor_label=actor_label,
            summary=summary,
        )
        return result, 200

    def apply_pro_delinquency_policy(
        self,
        *,
        tenant_id: int | None = None,
        reference_at=None,
        actor_label: str = "platform-billing-delinquency",
    ) -> dict[str, int]:
        now = reference_at or timezone.now()
        grace_days = max(_int(getattr(settings, "SUBSCRIPTIONS_PRO_DELINQUENCY_GRACE_DAYS", 5), default=5), 0)
        suspend_days = max(_int(getattr(settings, "SUBSCRIPTIONS_PRO_DELINQUENCY_SUSPEND_DAYS", 15), default=15), grace_days)
        queryset = TenantSubscription.objects.select_related("plan").filter(
            plan__billing_model=SubscriptionPlan.BillingModel.MINIMUM_COMMITMENT,
            status__in=[
                TenantSubscription.Status.ACTIVE,
                TenantSubscription.Status.PAST_DUE,
                TenantSubscription.Status.SUSPENDED,
            ],
        )
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)

        results = {
            "evaluated": 0,
            "unchanged": 0,
            "marked_past_due": 0,
            "suspended": 0,
            "reactivated": 0,
        }
        for subscription in queryset.order_by("tenant_id"):
            results["evaluated"] += 1
            unpaid = self._oldest_unpaid_minimum_ledger(tenant_id=subscription.tenant_id)
            if unpaid is None:
                if subscription.status in {TenantSubscription.Status.PAST_DUE, TenantSubscription.Status.SUSPENDED}:
                    previous_status = subscription.status
                    subscription.status = TenantSubscription.Status.ACTIVE
                    subscription.save(update_fields=["status", "updated_at"])
                    self._record_subscription_audit(
                        subscription=subscription,
                        action="tenant_subscription.delinquency_cleared",
                        actor_label=actor_label,
                        summary="Assinatura Pro reativada após regularização financeira.",
                        metadata={"previous_status": previous_status},
                    )
                    results["reactivated"] += 1
                else:
                    results["unchanged"] += 1
                continue

            due_anchor = unpaid.billing_period_end or unpaid.created_at
            past_due_at = due_anchor + timedelta(days=grace_days)
            suspend_at = due_anchor + timedelta(days=suspend_days)
            target_status = subscription.status
            action = ""
            if now >= suspend_at:
                target_status = TenantSubscription.Status.SUSPENDED
                action = "tenant_subscription.suspended_for_delinquency"
            elif now >= past_due_at:
                target_status = TenantSubscription.Status.PAST_DUE
                action = "tenant_subscription.marked_past_due"

            if target_status == subscription.status:
                results["unchanged"] += 1
                continue

            previous_status = subscription.status
            subscription.status = target_status
            subscription.save(update_fields=["status", "updated_at"])
            self._record_subscription_audit(
                subscription=subscription,
                action=action,
                actor_label=actor_label,
                summary="Assinatura Pro atualizada por inadimplência de complemento mensal.",
                metadata={
                    "previous_status": previous_status,
                    "ledger_key": unpaid.ledger_key,
                    "ledger_status": unpaid.status,
                    "billing_period_end": unpaid.billing_period_end.isoformat() if unpaid.billing_period_end else "",
                    "grace_days": grace_days,
                    "suspend_days": suspend_days,
                },
            )
            if target_status == TenantSubscription.Status.PAST_DUE:
                results["marked_past_due"] += 1
            elif target_status == TenantSubscription.Status.SUSPENDED:
                results["suspended"] += 1
        return results

    @staticmethod
    def _get_collectable_ledger(*, ledger_id: int | None, ledger_key: str) -> PlatformFeeLedger | None:
        queryset = PlatformFeeLedger.objects.select_related("tenant")
        if ledger_id:
            return queryset.filter(pk=ledger_id).first()
        normalized_key = _string(ledger_key)
        if normalized_key:
            return queryset.filter(ledger_key=normalized_key).first()
        return None

    @staticmethod
    def _oldest_unpaid_minimum_ledger(*, tenant_id: int) -> PlatformFeeLedger | None:
        return (
            PlatformFeeLedger.objects.filter(
                tenant_id=tenant_id,
                kind=PlatformFeeLedger.Kind.PRO_MINIMUM_ADJUSTMENT,
            )
            .exclude(status__in=[PlatformFeeLedger.Status.PAID, PlatformFeeLedger.Status.CANCELED])
            .order_by("billing_period_end", "created_at", "id")
            .first()
        )

    @staticmethod
    def _record_subscription_audit(
        *,
        subscription: TenantSubscription,
        action: str,
        actor_label: str,
        summary: str,
        metadata: dict[str, object] | None = None,
    ) -> None:
        audit_log_commands.record_event(
            tenant_id=subscription.tenant_id,
            module="subscriptions",
            action=action,
            entity_type="TenantSubscription",
            entity_id=str(subscription.id),
            actor_label=_string(actor_label),
            summary=summary,
            metadata={
                "billing_provider_code": subscription.billing_provider_code,
                "billing_method_status": subscription.billing_method_status,
                "has_billing_customer_reference": bool(subscription.billing_external_reference),
                "has_billing_method_reference": bool(subscription.billing_method_reference),
                **(metadata or {}),
            },
        )

    @staticmethod
    def _record_ledger_audit(
        *,
        ledger: PlatformFeeLedger,
        action: str,
        actor_label: str,
        summary: str,
    ) -> None:
        audit_log_commands.record_event(
            tenant_id=ledger.tenant_id,
            module="payments",
            action=action,
            entity_type="PlatformFeeLedger",
            entity_id=str(ledger.id),
            actor_label=_string(actor_label),
            summary=summary,
            metadata={
                "ledger_key": ledger.ledger_key,
                "status": ledger.status,
                "provider_code": ledger.provider_code,
                "provider_payment_reference": ledger.provider_payment_reference,
                "fee_amount": str(ledger.fee_amount),
            },
        )


platform_billing_commands = PlatformBillingCommandService()
