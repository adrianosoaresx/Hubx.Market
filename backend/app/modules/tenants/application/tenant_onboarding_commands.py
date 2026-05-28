from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from app.modules.accounts.application.admin_permissions import (
    PERMISSION_PLATFORM_TENANTS_MANAGE,
    admin_permissions,
    normalize_admin_role,
)
from app.modules.audit.application.audit_log_commands import audit_log_commands
from app.modules.subscriptions.application.subscription_commands import subscription_commands
from app.modules.subscriptions.models import SubscriptionPlan, TenantSubscription
from app.modules.tenants.application.platform_tenant_admin_commands import (
    _custom_domain_error,
    _normalize_custom_domain,
    _normalize_slug,
    _reserved_subdomains,
    _string,
    platform_tenant_admin_commands,
)
from app.modules.tenants.models import Tenant, TenantOnboarding


STEP_KEYS = ("store", "plan", "owner", "branding", "domain")


class TenantOnboardingCompletionBlocked(Exception):
    def __init__(self, result: str, errors: dict[str, str]):
        super().__init__(result)
        self.result = result
        self.errors = errors


def _check_manage_permission(*, actor_role: object, denied_result: str) -> dict[str, object] | None:
    normalized_role = normalize_admin_role(actor_role)
    if not normalized_role:
        return {
            "result": denied_result,
            "errors": {"__all__": "Permissão platform obrigatória para onboarding de lojas."},
        }
    permission = admin_permissions.check(role=normalized_role, permission=PERMISSION_PLATFORM_TENANTS_MANAGE)
    if not permission.allowed:
        return {
            "result": denied_result,
            "errors": {"__all__": "Permissão insuficiente para onboarding de lojas."},
        }
    return None


def _primary_color(value: object) -> str:
    color = _string(value, limit=7)
    if not color:
        return ""
    if len(color) == 7 and color.startswith("#") and all(character in "0123456789abcdefABCDEF" for character in color[1:]):
        return color.lower()
    return ""


@dataclass
class TenantOnboardingCommandService:
    def create_onboarding(
        self,
        *,
        payload: dict[str, object],
        actor_label: object = "",
        actor_role: object = "",
    ) -> dict[str, object]:
        denied = _check_manage_permission(actor_role=actor_role, denied_result="tenant-onboarding-create-permission-denied")
        if denied:
            return denied

        onboarding = TenantOnboarding.objects.create(
            status=TenantOnboarding.Status.DRAFT,
            store_name=_string(payload.get("store_name") or payload.get("name"), limit=150),
            store_display_name=_string(payload.get("store_display_name") or payload.get("store_name") or payload.get("name"), limit=150),
            primary_color=_primary_color(payload.get("primary_color")) or "#4f46e5",
            created_by_label=_string(actor_label, limit=180),
        )
        audit_result = self._record_platform_event(
            action="platform.tenant_onboarding.created",
            onboarding=onboarding,
            actor_label=actor_label,
            summary="Onboarding self-service de loja iniciado.",
        )
        if audit_result.get("result") != "audit-recorded":
            onboarding.delete()
            return {
                "result": "tenant-onboarding-create-audit-unavailable",
                "errors": {"__all__": "AuditLog platform-scope obrigatório para iniciar onboarding."},
            }
        return {"result": "tenant-onboarding-created", "onboarding": self._payload(onboarding)}

    def update_step(
        self,
        *,
        onboarding_id: int | str | None,
        step_key: object,
        payload: dict[str, object],
        actor_label: object = "",
        actor_role: object = "",
    ) -> dict[str, object]:
        denied = _check_manage_permission(actor_role=actor_role, denied_result="tenant-onboarding-step-permission-denied")
        if denied:
            return denied

        normalized_step = _string(step_key, limit=40)
        if normalized_step not in STEP_KEYS:
            return {"result": "tenant-onboarding-step-invalid", "errors": {"step": "Etapa inválida."}}

        onboarding = self._get_onboarding(onboarding_id)
        if onboarding is None:
            return {"result": "tenant-onboarding-not-found", "errors": {"onboarding_id": "Onboarding não encontrado."}}
        if onboarding.status == TenantOnboarding.Status.COMPLETED:
            return {"result": "tenant-onboarding-completed", "errors": {"__all__": "Onboarding já concluído."}}

        errors = self._apply_step(onboarding=onboarding, step_key=normalized_step, payload=payload)
        if errors:
            onboarding.status = TenantOnboarding.Status.BLOCKED
            onboarding.blockers = list(errors.values())
            onboarding.save(update_fields=["status", "blockers", "updated_at"])
            self._record_platform_event(
                action="platform.tenant_onboarding.blocked",
                onboarding=onboarding,
                actor_label=actor_label,
                summary="Etapa do onboarding bloqueada por validação.",
                metadata={"step": normalized_step, "errors": errors},
            )
            return {"result": "tenant-onboarding-step-invalid", "errors": errors, "onboarding": self._payload(onboarding)}

        onboarding.blockers = []
        onboarding.status = self._next_status(onboarding)
        onboarding.save()
        audit_result = self._record_platform_event(
            action="platform.tenant_onboarding.step_updated",
            onboarding=onboarding,
            actor_label=actor_label,
            summary="Etapa do onboarding atualizada.",
            metadata={"step": normalized_step},
        )
        if audit_result.get("result") != "audit-recorded":
            return {
                "result": "tenant-onboarding-step-audit-unavailable",
                "errors": {"__all__": "AuditLog platform-scope obrigatório para atualizar onboarding."},
            }
        return {"result": "tenant-onboarding-step-updated", "onboarding": self._payload(onboarding), "step": normalized_step}

    def complete_onboarding(
        self,
        *,
        onboarding_id: int | str | None,
        actor_label: object = "",
        actor_role: object = "",
    ) -> dict[str, object]:
        denied = _check_manage_permission(actor_role=actor_role, denied_result="tenant-onboarding-complete-permission-denied")
        if denied:
            return denied

        onboarding = self._get_onboarding(onboarding_id)
        if onboarding is None:
            return {"result": "tenant-onboarding-not-found", "errors": {"onboarding_id": "Onboarding não encontrado."}}
        if onboarding.status == TenantOnboarding.Status.COMPLETED:
            return {"result": "tenant-onboarding-already-completed", "onboarding": self._payload(onboarding)}

        errors = self._completion_errors(onboarding)
        if errors:
            self._mark_blocked(onboarding=onboarding, actor_label=actor_label, errors=errors)
            return {"result": "tenant-onboarding-complete-blocked", "errors": errors, "onboarding": self._payload(onboarding)}

        try:
            with transaction.atomic():
                locked = TenantOnboarding.objects.select_for_update().get(pk=onboarding.pk)
                tenant_result = platform_tenant_admin_commands.create_tenant(
                    payload={
                        "name": locked.store_name,
                        "slug": locked.store_slug,
                        "subdomain": locked.store_subdomain,
                        "custom_domain": locked.custom_domain,
                        "is_active": "1",
                        "maintenance_mode": "",
                    },
                    actor_label=actor_label,
                    actor_role=actor_role,
                )
                if tenant_result.get("result") != "platform-tenant-created":
                    raise TenantOnboardingCompletionBlocked(
                        str(tenant_result.get("result") or "tenant-create-failed"),
                        tenant_result.get("errors") or {"__all__": "Não foi possível criar a loja."},
                    )
                tenant = tenant_result["tenant"]

                subscription_result = subscription_commands.set_tenant_subscription(
                    tenant_id=tenant["id"],
                    plan_code=locked.plan_code,
                    status=TenantSubscription.Status.TRIALING,
                    external_reference=f"tenant-onboarding-{locked.id}",
                    actor_label=actor_label,
                )
                if subscription_result.get("result") not in {"tenant-subscription-created", "tenant-subscription-updated"}:
                    raise TenantOnboardingCompletionBlocked(
                        str(subscription_result.get("result") or "subscription-failed"),
                        subscription_result.get("errors") or {"__all__": "Não foi possível vincular assinatura interna."},
                    )

                owner_result = platform_tenant_admin_commands.bootstrap_owner(
                    tenant_slug=tenant["slug"],
                    payload={
                        "owner_email": locked.owner_email,
                        "owner_name": locked.owner_name,
                        "owner_role": locked.owner_role,
                    },
                    actor_label=actor_label,
                    actor_role=actor_role,
                )
                if owner_result.get("result") != "platform-tenant-owner-bootstrapped":
                    raise TenantOnboardingCompletionBlocked(
                        str(owner_result.get("result") or "owner-bootstrap-failed"),
                        owner_result.get("errors") or {"__all__": "Não foi possível provisionar owner inicial."},
                    )

                locked.tenant_id = tenant["id"]
                locked.status = TenantOnboarding.Status.COMPLETED
                locked.blockers = []
                locked.completed_at = timezone.now()
                locked.save(update_fields=["tenant", "status", "blockers", "completed_at", "updated_at"])
                audit_result = self._record_platform_event(
                    action="platform.tenant_onboarding.completed",
                    onboarding=locked,
                    actor_label=actor_label,
                    summary="Onboarding self-service de loja concluído.",
                    metadata={"tenant_id": tenant["id"], "tenant_slug": tenant["slug"], "plan_code": locked.plan_code},
                )
                if audit_result.get("result") != "audit-recorded":
                    raise TenantOnboardingCompletionBlocked(
                        "tenant-onboarding-complete-audit-unavailable",
                        {"__all__": "AuditLog platform-scope obrigatório para concluir onboarding."},
                    )
        except TenantOnboardingCompletionBlocked as error:
            onboarding.refresh_from_db()
            self._mark_blocked(onboarding=onboarding, actor_label=actor_label, errors=error.errors)
            return {"result": error.result, "errors": error.errors, "onboarding": self._payload(onboarding)}

        completed = self._get_onboarding(onboarding_id)
        return {"result": "tenant-onboarding-completed", "onboarding": self._payload(completed)}

    def _apply_step(self, *, onboarding: TenantOnboarding, step_key: str, payload: dict[str, object]) -> dict[str, str]:
        if step_key == "store":
            values = {
                "store_name": _string(payload.get("store_name"), limit=150),
                "store_slug": _normalize_slug(payload.get("store_slug"), limit=150),
                "store_subdomain": _normalize_slug(payload.get("store_subdomain"), limit=63),
            }
            errors = self._validate_store(values=values, onboarding=onboarding)
            if not errors:
                onboarding.store_name = values["store_name"]
                onboarding.store_slug = values["store_slug"]
                onboarding.store_subdomain = values["store_subdomain"]
                onboarding.store_display_name = onboarding.store_display_name or values["store_name"]
            return errors
        if step_key == "plan":
            plan_code = _normalize_slug(payload.get("plan_code"), limit=80)
            if not SubscriptionPlan.objects.filter(code=plan_code, status=SubscriptionPlan.Status.ACTIVE).exists():
                return {"plan_code": "Selecione um plano ativo."}
            onboarding.plan_code = plan_code
            return {}
        if step_key == "owner":
            owner_email = _string(payload.get("owner_email"), limit=254).lower()
            owner_role = _string(payload.get("owner_role"), limit=64).lower().replace("-", "_") or "owner"
            errors = {}
            if not owner_email or "@" not in owner_email:
                errors["owner_email"] = "Informe um e-mail válido para o owner inicial."
            if owner_role not in {"owner", "admin"}:
                errors["owner_role"] = "Owner inicial aceita apenas role owner ou admin."
            if not errors:
                onboarding.owner_email = owner_email
                onboarding.owner_name = _string(payload.get("owner_name"), limit=150)
                onboarding.owner_role = owner_role
            return errors
        if step_key == "branding":
            display_name = _string(payload.get("store_display_name"), limit=150)
            primary_color = _primary_color(payload.get("primary_color"))
            errors = {}
            if not display_name:
                errors["store_display_name"] = "Nome comercial é obrigatório."
            if not primary_color:
                errors["primary_color"] = "Cor primária deve usar formato hexadecimal, ex.: #4f46e5."
            if not errors:
                onboarding.store_display_name = display_name
                onboarding.primary_color = primary_color
            return errors
        normalized_domain = _normalize_custom_domain(payload.get("custom_domain"))
        domain_error = _custom_domain_error(normalized_domain)
        if domain_error:
            return {"custom_domain": domain_error}
        if normalized_domain and Tenant.objects.filter(custom_domain__iexact=normalized_domain).exists():
            return {"custom_domain": "Já existe uma loja com este domínio customizado."}
        onboarding.custom_domain = normalized_domain
        return {}

    def _completion_errors(self, onboarding: TenantOnboarding) -> dict[str, str]:
        errors: dict[str, str] = {}
        errors.update(self._validate_store(
            values={
                "store_name": onboarding.store_name,
                "store_slug": onboarding.store_slug,
                "store_subdomain": onboarding.store_subdomain,
            },
            onboarding=onboarding,
        ))
        if not onboarding.plan_code or not SubscriptionPlan.objects.filter(code=onboarding.plan_code, status=SubscriptionPlan.Status.ACTIVE).exists():
            errors["plan_code"] = "Selecione um plano ativo."
        if not onboarding.owner_email or "@" not in onboarding.owner_email:
            errors["owner_email"] = "Informe um e-mail válido para o owner inicial."
        if onboarding.owner_role not in {"owner", "admin"}:
            errors["owner_role"] = "Owner inicial aceita apenas role owner ou admin."
        if not onboarding.store_display_name:
            errors["store_display_name"] = "Nome comercial é obrigatório."
        if not _primary_color(onboarding.primary_color):
            errors["primary_color"] = "Cor primária deve usar formato hexadecimal."
        if onboarding.custom_domain and Tenant.objects.filter(custom_domain__iexact=onboarding.custom_domain).exists():
            errors["custom_domain"] = "Já existe uma loja com este domínio customizado."
        return errors

    def _validate_store(self, *, values: dict[str, object], onboarding: TenantOnboarding) -> dict[str, str]:
        errors: dict[str, str] = {}
        if not values["store_name"]:
            errors["store_name"] = "Nome da loja é obrigatório."
        if not values["store_slug"]:
            errors["store_slug"] = "Slug do tenant é obrigatório."
        elif Tenant.objects.filter(slug=values["store_slug"]).exists():
            errors["store_slug"] = "Já existe uma loja com este slug."
        if not values["store_subdomain"]:
            errors["store_subdomain"] = "Subdomínio é obrigatório."
        elif values["store_subdomain"] in _reserved_subdomains():
            errors["store_subdomain"] = "Este subdomínio é reservado para a plataforma."
        elif Tenant.objects.filter(subdomain=values["store_subdomain"]).exists():
            errors["store_subdomain"] = "Já existe uma loja com este subdomínio."
        return errors

    def _next_status(self, onboarding: TenantOnboarding) -> str:
        if all(
            (
                onboarding.store_name,
                onboarding.store_slug,
                onboarding.store_subdomain,
                onboarding.plan_code,
                onboarding.owner_email,
                onboarding.store_display_name,
                onboarding.primary_color,
            )
        ):
            return TenantOnboarding.Status.READY_FOR_REVIEW
        return TenantOnboarding.Status.IN_PROGRESS

    def _mark_blocked(self, *, onboarding: TenantOnboarding, actor_label: object, errors: dict[str, str]) -> None:
        onboarding.status = TenantOnboarding.Status.BLOCKED
        onboarding.blockers = list(errors.values())
        onboarding.save(update_fields=["status", "blockers", "updated_at"])
        self._record_platform_event(
            action="platform.tenant_onboarding.blocked",
            onboarding=onboarding,
            actor_label=actor_label,
            summary="Onboarding self-service bloqueado.",
            metadata={"errors": errors},
        )

    def _record_platform_event(
        self,
        *,
        action: str,
        onboarding: TenantOnboarding,
        actor_label: object,
        summary: str,
        metadata: dict[str, object] | None = None,
    ) -> dict[str, object]:
        safe_metadata = {
            "onboarding_id": onboarding.id,
            "status": onboarding.status,
            "store_slug": onboarding.store_slug,
            **(metadata or {}),
        }
        return audit_log_commands.record_event(
            tenant_id=None,
            module="tenants",
            action=action,
            entity_type="TenantOnboarding",
            entity_id=str(onboarding.id),
            actor_label=_string(actor_label, limit=180),
            summary=summary,
            metadata=safe_metadata,
            allow_platform_scope=True,
        )

    def _get_onboarding(self, onboarding_id: int | str | None) -> TenantOnboarding | None:
        try:
            normalized_id = int(onboarding_id or 0)
        except (TypeError, ValueError):
            return None
        return TenantOnboarding.objects.filter(pk=normalized_id).first()

    def _payload(self, onboarding: TenantOnboarding | None) -> dict[str, object]:
        if onboarding is None:
            return {}
        return {
            "id": onboarding.id,
            "status": onboarding.status,
            "tenant_id": onboarding.tenant_id,
            "store_slug": onboarding.store_slug,
            "store_subdomain": onboarding.store_subdomain,
            "plan_code": onboarding.plan_code,
            "owner_email": onboarding.owner_email,
        }


tenant_onboarding_commands = TenantOnboardingCommandService()
