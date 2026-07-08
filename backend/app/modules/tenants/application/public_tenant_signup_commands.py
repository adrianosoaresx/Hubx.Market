from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.utils.crypto import constant_time_compare
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.text import slugify

from app.modules.accounts.application.initial_owner_provisioning_commands import (
    initial_owner_provisioning_commands,
)
from app.modules.accounts.models import OwnerUser
from app.modules.audit.application.audit_log_commands import audit_log_commands
from app.modules.subscriptions.application.subscription_commands import subscription_commands
from app.modules.subscriptions.application.subscription_coupon_queries import (
    normalize_subscription_coupon_code,
    subscription_coupon_queries,
)
from app.modules.subscriptions.models import SubscriptionPlan, TenantSubscription
from app.modules.tenants.models import Tenant, TenantOnboarding


DEFAULT_RESERVED_SUBDOMAINS = ("www", "app", "api", "docs", "cdn", "admin")


def _string(value: object, *, limit: int = 180) -> str:
    return str(value or "").strip()[:limit]


def _slug(value: object, *, limit: int) -> str:
    return slugify(_string(value, limit=limit)).strip("-")[:limit]


def _email(value: object) -> str:
    return _string(value, limit=254).lower()


def _truthy(value: object) -> bool:
    return value in {True, "1", "true", "True", "on", "yes", "sim"}


def _money(value: object) -> Decimal:
    try:
        return max(Decimal(str(value or "0.00")), Decimal("0.00"))
    except Exception:
        return Decimal("0.00")


def _reserved_subdomains() -> set[str]:
    configured = getattr(settings, "HUBX_MARKET_RESERVED_SUBDOMAINS", DEFAULT_RESERVED_SUBDOMAINS)
    return {str(item).strip().lower() for item in configured if str(item).strip()}


def _public_port() -> str:
    port = str(getattr(settings, "HUBX_MARKET_PUBLIC_PORT", "") or "").strip()
    return f":{port}" if port else ""


def _store_url(subdomain: str, path: str = "/") -> str:
    root_domain = str(getattr(settings, "HUBX_MARKET_ROOT_DOMAIN", "hubx.market") or "hubx.market").strip().lower()
    normalized_path = path if str(path or "").startswith("/") else f"/{path}"
    return f"http://{subdomain}.{root_domain}{_public_port()}{normalized_path}"


def _promotion_snapshot_from_validation(validation: dict[str, object] | None, *, source: str) -> dict[str, object]:
    snapshot = dict((validation or {}).get("promotion_snapshot") or {})
    if snapshot:
        snapshot["source"] = source
    return snapshot


def _promotion_fields(*, plan: SubscriptionPlan, promotion_snapshot: dict[str, object]) -> dict[str, object]:
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


def _record_coupon_application_event(
    *,
    entity_type: str,
    entity_id: int | str,
    promotion_snapshot: dict[str, object],
    actor_label: object,
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
        summary="Cupom SaaS aplicado em signup publico.",
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


def _rate_limit_key(identifier: str) -> str:
    digest = hashlib.sha256(identifier.encode("utf-8")).hexdigest()
    return f"hubx-public-signup:{digest}"


class PublicTenantSignupBlocked(Exception):
    def __init__(self, result: str, errors: dict[str, str]):
        super().__init__(result)
        self.result = result
        self.errors = errors


@dataclass
class PublicTenantSignupCommandService:
    def create_signup(
        self,
        *,
        payload: dict[str, object],
        ip_address: object = "",
        actor_label: object = "public-signup",
    ) -> dict[str, object]:
        values = self._normalize_payload(payload)
        rate_limit = self._consume_rate_limit(email=values["owner_email"], ip_address=ip_address)
        if rate_limit:
            return rate_limit

        existing = self._existing_signup(values=values)
        if existing:
            return {"result": "public-tenant-signup-already-created", **existing}
        errors = self._validate(values)
        if errors:
            return {"result": "public-tenant-signup-invalid", "errors": errors}

        plan = SubscriptionPlan.objects.get(code=values["plan_code"], status=SubscriptionPlan.Status.ACTIVE)
        if bool(getattr(plan, "requires_billing_method", False)):
            return {
                "result": "public-tenant-signup-invalid",
                "errors": {
                    "plan_code": "Este plano exige método de cobrança e deve seguir pelo onboarding assistido.",
                },
            }
        coupon_validation = None
        if values["coupon_code"]:
            coupon_validation = subscription_coupon_queries.validate_plan_coupon(
                plan_code=plan.code,
                coupon_code=values["coupon_code"],
            )
            if coupon_validation.get("result") != "subscription-coupon-valid":
                return {
                    "result": "public-tenant-signup-invalid",
                    "errors": {"coupon_code": str(coupon_validation.get("message") or "Cupom SaaS invalido para este plano.")},
                }
        promotion_snapshot = _promotion_snapshot_from_validation(coupon_validation, source="public-signup")
        promotion_fields = _promotion_fields(plan=plan, promotion_snapshot=promotion_snapshot)
        try:
            with transaction.atomic():
                tenant = Tenant.objects.create(
                    name=values["store_name"],
                    slug=values["desired_subdomain"],
                    subdomain=values["desired_subdomain"],
                    is_active=True,
                    maintenance_mode=True,
                )
                onboarding = TenantOnboarding.objects.create(
                    tenant=tenant,
                    status=TenantOnboarding.Status.COMPLETED,
                    store_name=values["store_name"],
                    store_slug=tenant.slug,
                    store_subdomain=tenant.subdomain,
                    plan_code=plan.code,
                    **promotion_fields,
                    owner_email=values["owner_email"],
                    owner_name=values["owner_name"],
                    owner_role="owner",
                    store_display_name=values["store_name"],
                    primary_color="#9a6410",
                    created_by_label=_string(actor_label, limit=180),
                    completed_at=timezone.now(),
                )
                audit_result = audit_log_commands.record_event(
                    tenant_id=tenant.id,
                    module="tenants",
                    action="tenant.self_service_created",
                    entity_type="Tenant",
                    entity_id=str(tenant.id),
                    actor_label=values["owner_email"],
                    summary="Tenant criado por signup publico self-service.",
                    metadata={
                        "tenant_slug": tenant.slug,
                        "tenant_subdomain": tenant.subdomain,
                        "plan_code": plan.code,
                        "trial_days": plan.trial_days,
                        "requires_payment_method": plan.requires_payment_method,
                        "maintenance_mode": tenant.maintenance_mode,
                        "coupon_code": promotion_fields["coupon_code_snapshot"],
                        "effective_monthly_price": str(promotion_fields["effective_monthly_price_snapshot"]),
                    },
                )
                if audit_result.get("result") != "audit-recorded":
                    raise PublicTenantSignupBlocked(
                        "public-tenant-signup-audit-unavailable",
                        {"__all__": "AuditLog tenant-scoped obrigatorio para criar loja self-service."},
                    )

                subscription_result = subscription_commands.set_tenant_subscription(
                    tenant_id=tenant.id,
                    plan_code=plan.code,
                    status=TenantSubscription.Status.TRIALING if plan.trial_days else TenantSubscription.Status.ACTIVE,
                    external_reference=f"public-signup-{onboarding.id}",
                    actor_label=values["owner_email"],
                    promotion_snapshot=promotion_snapshot,
                )
                if subscription_result.get("result") not in {"tenant-subscription-created", "tenant-subscription-updated"}:
                    raise PublicTenantSignupBlocked(
                        str(subscription_result.get("result") or "public-tenant-signup-subscription-failed"),
                        subscription_result.get("errors") or {"__all__": "Nao foi possivel criar assinatura comercial."},
                    )
                if promotion_snapshot:
                    coupon_audit = _record_coupon_application_event(
                        entity_type="TenantSubscription",
                        entity_id=(subscription_result.get("subscription") or {}).get("id", ""),
                        promotion_snapshot=promotion_snapshot,
                        actor_label=values["owner_email"],
                    )
                    if coupon_audit.get("result") != "audit-recorded":
                        raise PublicTenantSignupBlocked(
                            "subscription-coupon-application-audit-unavailable",
                            {"__all__": "AuditLog platform-scope obrigatorio para registrar aplicacao de cupom SaaS."},
                        )

                owner_result = initial_owner_provisioning_commands.provision_initial_owner(
                    tenant_id=tenant.id,
                    email=values["owner_email"],
                    full_name=values["owner_name"],
                    role="owner",
                    password=values["password"],
                    require_new_user=True,
                    actor_label=values["owner_email"],
                )
                if owner_result.get("result") != "initial-owner-provisioned":
                    raise PublicTenantSignupBlocked(
                        str(owner_result.get("result") or "public-tenant-signup-owner-failed"),
                        owner_result.get("errors") or {"__all__": "Nao foi possivel criar owner inicial."},
                    )

                completion_audit = audit_log_commands.record_event(
                    tenant_id=tenant.id,
                    module="tenants",
                    action="tenant.self_service_signup_completed",
                    entity_type="TenantOnboarding",
                    entity_id=str(onboarding.id),
                    actor_label=values["owner_email"],
                    summary="Signup publico self-service concluido em modo manutencao.",
                    metadata={
                        "plan_code": plan.code,
                        "trial_days": plan.trial_days,
                        "requires_payment_method": plan.requires_payment_method,
                        "owner_created": bool((owner_result.get("owner") or {}).get("created")),
                        "coupon_code": promotion_fields["coupon_code_snapshot"],
                        "effective_monthly_price": str(promotion_fields["effective_monthly_price_snapshot"]),
                    },
                )
                if completion_audit.get("result") != "audit-recorded":
                    raise PublicTenantSignupBlocked(
                        "public-tenant-signup-audit-unavailable",
                        {"__all__": "AuditLog tenant-scoped obrigatorio para concluir signup self-service."},
                    )
        except PublicTenantSignupBlocked as error:
            return {"result": error.result, "errors": error.errors}
        except IntegrityError:
            return {
                "result": "public-tenant-signup-invalid",
                "errors": {"desired_subdomain": "Este subdominio acabou de ser reservado. Escolha outro."},
            }

        return {
            "result": "public-tenant-signup-created",
            "tenant": self._tenant_payload(tenant),
            "onboarding": {"id": onboarding.id, "status": onboarding.status},
            "subscription": subscription_result.get("subscription") or {},
            "owner": owner_result.get("owner") or {},
        }

    def _normalize_payload(self, payload: dict[str, object]) -> dict[str, object]:
        return {
            "plan_code": _slug(payload.get("plan_code"), limit=80),
            "store_name": _string(payload.get("store_name"), limit=150),
            "desired_subdomain": _slug(payload.get("desired_subdomain") or payload.get("store_subdomain"), limit=63),
            "owner_name": _string(payload.get("owner_name") or payload.get("contact_name"), limit=150),
            "owner_email": _email(payload.get("owner_email") or payload.get("contact_email")),
            "contact_phone": _string(payload.get("contact_phone"), limit=40),
            "coupon_code": normalize_subscription_coupon_code(payload.get("coupon_code")),
            "access_token": _string(payload.get("access_token"), limit=180),
            "password": str(payload.get("password") or ""),
            "password_confirm": str(payload.get("password_confirm") or ""),
            "accept_terms": _truthy(payload.get("accept_terms")),
            "website": _string(payload.get("website"), limit=120),
        }

    def _validate(self, values: dict[str, object]) -> dict[str, str]:
        errors: dict[str, str] = {}
        if values["website"]:
            errors["__all__"] = "Nao foi possivel concluir o cadastro."
        expected_token = _string(getattr(settings, "HUBX_PUBLIC_SIGNUP_ACCESS_TOKEN", ""), limit=180)
        if bool(getattr(settings, "HUBX_PUBLIC_SIGNUP_REQUIRE_ACCESS_TOKEN", True)):
            if not expected_token:
                errors["access_token"] = "Signup self-service exige codigo de acesso configurado pela plataforma."
            elif not constant_time_compare(str(values["access_token"]), expected_token):
                errors["access_token"] = "Codigo de acesso invalido."
        if not SubscriptionPlan.objects.filter(code=values["plan_code"], status=SubscriptionPlan.Status.ACTIVE).exists():
            errors["plan_code"] = "Selecione um plano ativo."
        if not values["store_name"]:
            errors["store_name"] = "Informe o nome da loja."
        desired_subdomain = str(values["desired_subdomain"])
        if not desired_subdomain:
            errors["desired_subdomain"] = "Informe o subdominio desejado."
        elif desired_subdomain in _reserved_subdomains():
            errors["desired_subdomain"] = "Este subdominio e reservado para a plataforma."
        else:
            if Tenant.objects.filter(subdomain=desired_subdomain).exists():
                errors["desired_subdomain"] = "Este subdominio ja esta em uso."
            if Tenant.objects.filter(slug=desired_subdomain).exists():
                errors["desired_subdomain"] = "Este slug de loja ja esta em uso."
        owner_email = str(values["owner_email"])
        if not owner_email or "@" not in owner_email:
            errors["owner_email"] = "Informe um e-mail valido."
        elif User.objects.filter(email__iexact=owner_email).exists() or OwnerUser.objects.filter(email__iexact=owner_email).exists():
            errors["owner_email"] = "Este e-mail ja possui acesso. Use a aquisicao assistida."
        if not values["owner_name"]:
            errors["owner_name"] = "Informe o nome do owner inicial."
        if values["password"] != values["password_confirm"]:
            errors["password_confirm"] = "As senhas nao conferem."
        else:
            try:
                validate_password(str(values["password"]))
            except ValidationError as error:
                errors["password"] = " ".join(error.messages)
        if not values["accept_terms"]:
            errors["accept_terms"] = "Aceite os termos para criar a loja."
        return errors

    def _existing_signup(self, *, values: dict[str, object]) -> dict[str, object] | None:
        tenant = Tenant.objects.filter(subdomain=str(values["desired_subdomain"])).first()
        if tenant is None:
            return None
        owner = OwnerUser.objects.filter(tenant=tenant, email__iexact=str(values["owner_email"]), is_active=True).first()
        subscription = TenantSubscription.objects.filter(tenant=tenant, plan__code=str(values["plan_code"])).first()
        if owner is None or subscription is None:
            return None
        return {
            "tenant": self._tenant_payload(tenant),
            "subscription": {
                "id": subscription.id,
                "tenant_id": tenant.id,
                "plan_code": subscription.plan.code,
                "plan_name": subscription.plan.name,
                "status": subscription.status,
                "coupon_code_snapshot": subscription.coupon_code_snapshot,
                "effective_monthly_price_snapshot": str(subscription.effective_monthly_price_snapshot),
            },
            "owner": {"id": owner.id, "email": owner.email, "created": False},
        }

    def _consume_rate_limit(self, *, email: object, ip_address: object) -> dict[str, object] | None:
        max_attempts = max(int(getattr(settings, "HUBX_PUBLIC_SIGNUP_RATE_LIMIT_MAX_ATTEMPTS", 5) or 5), 1)
        window_seconds = max(int(getattr(settings, "HUBX_PUBLIC_SIGNUP_RATE_LIMIT_WINDOW_SECONDS", 900) or 900), 1)
        identifiers = [
            f"email:{_email(email)}" if _email(email) else "",
            f"ip:{_string(ip_address, limit=80)}" if _string(ip_address, limit=80) else "",
        ]
        keys = [_rate_limit_key(identifier) for identifier in identifiers if identifier]
        for key in keys:
            if int(cache.get(key, 0) or 0) >= max_attempts:
                return {
                    "result": "public-tenant-signup-rate-limited",
                    "errors": {"__all__": "Muitas tentativas de cadastro. Aguarde alguns minutos e tente novamente."},
                }
        for key in keys:
            if not cache.add(key, 1, timeout=window_seconds):
                try:
                    cache.incr(key)
                except ValueError:
                    cache.set(key, int(cache.get(key, 0) or 0) + 1, timeout=window_seconds)
        return None

    def _tenant_payload(self, tenant: Tenant) -> dict[str, object]:
        return {
            "id": tenant.id,
            "name": tenant.name,
            "slug": tenant.slug,
            "subdomain": tenant.subdomain,
            "maintenance_mode": tenant.maintenance_mode,
            "store_url": _store_url(tenant.subdomain, "/"),
            "login_url": _store_url(tenant.subdomain, "/accounts/login/"),
            "ops_url": _store_url(tenant.subdomain, "/ops/"),
        }


public_tenant_signup_commands = PublicTenantSignupCommandService()
