from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.owner_mfa_vault_kms_production_closure_queries import (
    owner_mfa_vault_kms_production_closure_queries,
)
from app.modules.tenants.models import Tenant


def _string(value: object, *, limit: int = 255) -> str:
    return str(value or "").strip()[:limit]


def _parse_tenant_ids(value: object) -> tuple[str, ...]:
    if isinstance(value, (list, tuple, set)):
        raw_items = value
    else:
        raw_items = str(value or "").split(",")
    return tuple(dict.fromkeys(str(item).strip() for item in raw_items if str(item).strip()))


@dataclass(frozen=True)
class OwnerMfaHashicorpVaultTenantExpansionDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaHashicorpVaultTenantExpansionQueryService:
    def get_review(
        self,
        *,
        canary_tenant_id: int | str | None,
        target_tenant_ids: object,
        probe_reference: object = "owners/vault-kms/hashicorp-vault-probe",
        canary_owner_email: object = "",
        monitoring_window_elapsed: bool = False,
        provider_health_stable: bool = False,
        owner_login_error_spike_absent: bool = False,
        support_incidents_absent: bool = False,
        rollback_signal_absent: bool = False,
        evidence_redacted: bool = False,
        rollback_runbook_confirmed: bool = False,
        residual_risks_accepted: bool = False,
        tenant_expansion_plan_documented: bool = False,
        expansion_window_confirmed: bool = False,
        per_tenant_evidence_required: bool = False,
        support_standby_confirmed: bool = False,
        rollback_window_confirmed: bool = False,
        max_parallel_tenants: int = 1,
    ) -> dict[str, object]:
        closure = owner_mfa_vault_kms_production_closure_queries.get_closure(
            tenant_id=canary_tenant_id,
            probe_reference=_string(probe_reference),
            canary_owner_email=canary_owner_email,
            monitoring_window_elapsed=monitoring_window_elapsed,
            provider_health_stable=provider_health_stable,
            owner_login_error_spike_absent=owner_login_error_spike_absent,
            support_incidents_absent=support_incidents_absent,
            rollback_signal_absent=rollback_signal_absent,
            evidence_redacted=evidence_redacted,
            rollback_runbook_confirmed=rollback_runbook_confirmed,
            residual_risks_accepted=residual_risks_accepted,
            tenant_expansion_plan_documented=tenant_expansion_plan_documented,
        )
        expansion_signals = {
            "expansion_window_confirmed": bool(expansion_window_confirmed),
            "per_tenant_evidence_required": bool(per_tenant_evidence_required),
            "support_standby_confirmed": bool(support_standby_confirmed),
            "rollback_window_confirmed": bool(rollback_window_confirmed),
            "single_tenant_window": int(max_parallel_tenants or 0) == 1,
        }
        target_ids = _parse_tenant_ids(target_tenant_ids)
        targets = self._targets(target_ids=target_ids)
        blockers = self._blockers(
            closure=closure,
            expansion_signals=expansion_signals,
            target_ids=target_ids,
            targets=targets,
            canary_tenant_id=str(canary_tenant_id or "").strip(),
        )
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"owner-mfa-hashicorp-vault-tenant-expansion-{status}",
            "ready": status == "ready",
            "status": status,
            "canary_tenant_id": closure["tenant_id"],
            "target_provider": "hashicorp-vault",
            "closure": closure,
            "target_tenant_ids": target_ids,
            "target_tenants": targets,
            "max_parallel_tenants": int(max_parallel_tenants or 0),
            "expansion_signals": expansion_signals,
            "decisions": self._decisions(closure=closure, expansion_signals=expansion_signals, targets=targets, status=status),
            "blockers": blockers,
            "runbook": self._runbook(),
            "evidence_requirements": self._evidence_requirements(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _targets(self, *, target_ids: tuple[str, ...]) -> tuple[dict[str, object], ...]:
        if not target_ids:
            return ()
        tenants = Tenant.objects.filter(id__in=target_ids).order_by("id")
        return tuple(
            {
                "tenant_id": str(tenant.id),
                "tenant_slug": tenant.slug,
                "subdomain": tenant.subdomain,
                "is_active": tenant.is_active,
                "maintenance_mode": tenant.maintenance_mode,
                "ready": tenant.is_active and not tenant.maintenance_mode,
                "blockers": self._target_blockers(tenant=tenant),
            }
            for tenant in tenants
        )

    def _target_blockers(self, *, tenant: Tenant) -> tuple[str, ...]:
        blockers = []
        if not tenant.is_active:
            blockers.append("tenant-inactive")
        if tenant.maintenance_mode:
            blockers.append("tenant-maintenance-mode")
        return tuple(blockers)

    def _blockers(
        self,
        *,
        closure: dict[str, object],
        expansion_signals: dict[str, bool],
        target_ids: tuple[str, ...],
        targets: tuple[dict[str, object], ...],
        canary_tenant_id: str,
    ) -> tuple[str, ...]:
        blockers: list[str] = []
        if not closure["ready"]:
            blockers.extend(f"closure:{blocker}" for blocker in closure["blockers"])
            blockers.append(f"closure:{closure['status']}")
        if not target_ids:
            blockers.append("targets:empty")
        found_ids = {str(target["tenant_id"]) for target in targets}
        for target_id in target_ids:
            if target_id not in found_ids:
                blockers.append(f"target:{target_id}:not-found")
            if target_id == canary_tenant_id:
                blockers.append(f"target:{target_id}:is-canary")
        for target in targets:
            for blocker in target["blockers"]:
                blockers.append(f"target:{target['tenant_id']}:{blocker}")
        for key, ready in expansion_signals.items():
            if not ready:
                blockers.append(f"expansion:{key}:missing")
        return tuple(dict.fromkeys(blockers))

    def _decisions(
        self,
        *,
        closure: dict[str, object],
        expansion_signals: dict[str, bool],
        targets: tuple[dict[str, object], ...],
        status: str,
    ) -> tuple[OwnerMfaHashicorpVaultTenantExpansionDecision, ...]:
        return (
            OwnerMfaHashicorpVaultTenantExpansionDecision(
                key="canary-closure",
                status=str(closure["status"]),
                summary="expansão só pode iniciar após closure READY do tenant canário",
            ),
            OwnerMfaHashicorpVaultTenantExpansionDecision(
                key="target-tenants",
                status="ready" if targets and all(target["ready"] for target in targets) else "blocked",
                summary="tenants-alvo precisam existir, estar ativos e fora de maintenance mode",
            ),
            OwnerMfaHashicorpVaultTenantExpansionDecision(
                key="single-tenant-window",
                status="ready" if expansion_signals["single_tenant_window"] else "blocked",
                summary="primeira expansão real deve ocorrer um tenant por janela",
            ),
            OwnerMfaHashicorpVaultTenantExpansionDecision(
                key="per-tenant-evidence",
                status="ready" if expansion_signals["per_tenant_evidence_required"] else "blocked",
                summary="cada tenant precisa repetir activation evidence e monitoring próprios",
            ),
            OwnerMfaHashicorpVaultTenantExpansionDecision(
                key="classification",
                status=status,
                summary="review libera apenas plano de expansão, não ativa provider para tenants",
            ),
        )

    def _runbook(self) -> tuple[str, ...]:
        return (
            "selecionar um único tenant-alvo por janela operacional",
            "ativar flags/env fora do command apenas para o tenant aprovado",
            "executar production activation evidence para o tenant-alvo",
            "executar post-activation monitoring para o tenant-alvo",
            "parar expansão se qualquer tenant entrar em WATCH, BLOCKED ou ROLLBACK",
        )

    def _evidence_requirements(self) -> tuple[str, ...]:
        return (
            "closure READY do tenant canário",
            "lista explícita de tenant_ids alvo",
            "evidência redigida por tenant",
            "rollback window e suporte confirmados por janela",
            "sem reuso de secret/path/token no output",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "Owner MFA Hashicorp Vault Tenant Expansion Evidence Execution",
                "Owner MFA Vault/KMS Rotation Runbook Review",
            )
        return (
            "Owner MFA Vault/KMS Production Closure Review",
            "Owner MFA Hashicorp Vault Post-Activation Monitoring Review",
        )


owner_mfa_hashicorp_vault_tenant_expansion_queries = OwnerMfaHashicorpVaultTenantExpansionQueryService()
