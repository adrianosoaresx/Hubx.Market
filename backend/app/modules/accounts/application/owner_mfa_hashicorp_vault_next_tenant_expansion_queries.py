from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.owner_mfa_hashicorp_vault_target_post_expansion_monitoring_queries import (
    owner_mfa_hashicorp_vault_target_post_expansion_monitoring_queries,
)
from app.modules.tenants.models import Tenant


def _parse_tenant_ids(value: object) -> tuple[str, ...]:
    if isinstance(value, (list, tuple, set)):
        raw_items = value
    else:
        raw_items = str(value or "").split(",")
    return tuple(dict.fromkeys(str(item).strip() for item in raw_items if str(item).strip()))


@dataclass(frozen=True)
class OwnerMfaHashicorpVaultNextTenantExpansionDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaHashicorpVaultNextTenantExpansionQueryService:
    def get_review(
        self,
        *,
        canary_tenant_id: int | str | None,
        current_target_tenant_id: int | str | None,
        next_target_tenant_ids: object,
        probe_reference: object = "owners/vault-kms/hashicorp-vault-probe",
        canary_owner_email: object = "",
        canary_monitoring_window_elapsed: bool = False,
        canary_provider_health_stable: bool = False,
        canary_owner_login_error_spike_absent: bool = False,
        canary_support_incidents_absent: bool = False,
        canary_rollback_signal_absent: bool = False,
        canary_evidence_redacted: bool = False,
        rollback_runbook_confirmed: bool = False,
        residual_risks_accepted: bool = False,
        tenant_expansion_plan_documented: bool = False,
        expansion_window_confirmed: bool = False,
        per_tenant_evidence_required: bool = False,
        support_standby_confirmed: bool = False,
        rollback_window_confirmed: bool = False,
        target_flags_enabled: bool = False,
        target_activation_evidence_captured: bool = False,
        target_monitoring_scheduled: bool = False,
        target_owner_login_challenge_passed: bool = False,
        target_provider_health_ready: bool = False,
        rollback_not_required: bool = False,
        expansion_evidence_redacted: bool = False,
        target_monitoring_window_elapsed: bool = False,
        target_provider_health_stable: bool = False,
        target_owner_login_error_spike_absent: bool = False,
        target_support_incidents_absent: bool = False,
        target_rollback_signal_absent: bool = False,
        evidence_redacted: bool = False,
        next_window_confirmed: bool = False,
        operator_capacity_confirmed: bool = False,
        previous_target_evidence_archived: bool = False,
        stop_after_current_target: bool = False,
        max_parallel_tenants: int = 1,
    ) -> dict[str, object]:
        monitoring = owner_mfa_hashicorp_vault_target_post_expansion_monitoring_queries.get_review(
            canary_tenant_id=canary_tenant_id,
            target_tenant_id=current_target_tenant_id,
            probe_reference=probe_reference,
            canary_owner_email=canary_owner_email,
            canary_monitoring_window_elapsed=canary_monitoring_window_elapsed,
            canary_provider_health_stable=canary_provider_health_stable,
            canary_owner_login_error_spike_absent=canary_owner_login_error_spike_absent,
            canary_support_incidents_absent=canary_support_incidents_absent,
            canary_rollback_signal_absent=canary_rollback_signal_absent,
            canary_evidence_redacted=canary_evidence_redacted,
            rollback_runbook_confirmed=rollback_runbook_confirmed,
            residual_risks_accepted=residual_risks_accepted,
            tenant_expansion_plan_documented=tenant_expansion_plan_documented,
            expansion_window_confirmed=expansion_window_confirmed,
            per_tenant_evidence_required=per_tenant_evidence_required,
            support_standby_confirmed=support_standby_confirmed,
            rollback_window_confirmed=rollback_window_confirmed,
            target_flags_enabled=target_flags_enabled,
            target_activation_evidence_captured=target_activation_evidence_captured,
            target_monitoring_scheduled=target_monitoring_scheduled,
            target_owner_login_challenge_passed=target_owner_login_challenge_passed,
            target_provider_health_ready=target_provider_health_ready,
            rollback_not_required=rollback_not_required,
            expansion_evidence_redacted=expansion_evidence_redacted,
            target_monitoring_window_elapsed=target_monitoring_window_elapsed,
            target_provider_health_stable=target_provider_health_stable,
            target_owner_login_error_spike_absent=target_owner_login_error_spike_absent,
            target_support_incidents_absent=target_support_incidents_absent,
            target_rollback_signal_absent=target_rollback_signal_absent,
            evidence_redacted=evidence_redacted,
        )
        cadence_signals = {
            "next_window_confirmed": bool(next_window_confirmed),
            "operator_capacity_confirmed": bool(operator_capacity_confirmed),
            "previous_target_evidence_archived": bool(previous_target_evidence_archived),
            "single_tenant_window": int(max_parallel_tenants or 0) == 1,
            "stop_after_current_target": bool(stop_after_current_target),
        }
        next_ids = _parse_tenant_ids(next_target_tenant_ids)
        next_targets = self._targets(target_ids=next_ids)
        blockers = self._blockers(
            monitoring=monitoring,
            cadence_signals=cadence_signals,
            next_ids=next_ids,
            next_targets=next_targets,
            canary_tenant_id=str(canary_tenant_id or "").strip(),
            current_target_tenant_id=str(current_target_tenant_id or "").strip(),
        )
        status = self._status(blockers=blockers, stop_after_current_target=cadence_signals["stop_after_current_target"])
        return {
            "result": f"owner-mfa-hashicorp-vault-next-tenant-expansion-{status}",
            "ready": status == "ready",
            "status": status,
            "canary_tenant_id": monitoring["canary_tenant_id"],
            "current_target_tenant_id": monitoring["target_tenant_id"],
            "target_provider": "hashicorp-vault",
            "monitoring": monitoring,
            "next_target_tenant_ids": next_ids,
            "next_target_tenants": next_targets,
            "max_parallel_tenants": int(max_parallel_tenants or 0),
            "cadence_signals": cadence_signals,
            "decisions": self._decisions(
                monitoring=monitoring,
                cadence_signals=cadence_signals,
                next_targets=next_targets,
                status=status,
            ),
            "blockers": blockers,
            "runbook": self._runbook(status=status),
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
        monitoring: dict[str, object],
        cadence_signals: dict[str, bool],
        next_ids: tuple[str, ...],
        next_targets: tuple[dict[str, object], ...],
        canary_tenant_id: str,
        current_target_tenant_id: str,
    ) -> tuple[str, ...]:
        blockers: list[str] = []
        if not monitoring["ready"]:
            blockers.extend(f"monitoring:{blocker}" for blocker in monitoring["blockers"])
            blockers.append(f"monitoring:{monitoring['status']}")
        if cadence_signals["stop_after_current_target"]:
            return tuple(dict.fromkeys(blockers))
        if not next_ids:
            blockers.append("next-targets:empty")
        found_ids = {str(target["tenant_id"]) for target in next_targets}
        for target_id in next_ids:
            if target_id not in found_ids:
                blockers.append(f"next-target:{target_id}:not-found")
            if target_id == canary_tenant_id:
                blockers.append(f"next-target:{target_id}:is-canary")
            if target_id == current_target_tenant_id:
                blockers.append(f"next-target:{target_id}:is-current-target")
        for target in next_targets:
            for blocker in target["blockers"]:
                blockers.append(f"next-target:{target['tenant_id']}:{blocker}")
        for key, ready in cadence_signals.items():
            if key == "stop_after_current_target":
                continue
            if not ready:
                blockers.append(f"cadence:{key}:missing")
        return tuple(dict.fromkeys(blockers))

    def _status(self, *, blockers: tuple[str, ...], stop_after_current_target: bool) -> str:
        if blockers:
            return "blocked"
        if stop_after_current_target:
            return "paused"
        return "ready"

    def _decisions(
        self,
        *,
        monitoring: dict[str, object],
        cadence_signals: dict[str, bool],
        next_targets: tuple[dict[str, object], ...],
        status: str,
    ) -> tuple[OwnerMfaHashicorpVaultNextTenantExpansionDecision, ...]:
        return (
            OwnerMfaHashicorpVaultNextTenantExpansionDecision(
                key="current-target-monitoring",
                status=str(monitoring["status"]),
                summary="próximo ciclo só pode ser considerado após monitoring HEALTHY do target atual",
            ),
            OwnerMfaHashicorpVaultNextTenantExpansionDecision(
                key="next-targets",
                status="ready" if next_targets and all(target["ready"] for target in next_targets) else "blocked",
                summary="próximos tenants precisam existir, estar ativos e fora de maintenance mode",
            ),
            OwnerMfaHashicorpVaultNextTenantExpansionDecision(
                key="cadence-control",
                status="paused" if cadence_signals["stop_after_current_target"] else status,
                summary="a cadência pode ser pausada explicitamente mesmo com sinais saudáveis",
            ),
            OwnerMfaHashicorpVaultNextTenantExpansionDecision(
                key="single-tenant-window",
                status="ready" if cadence_signals["single_tenant_window"] else "blocked",
                summary="cada ciclo continua limitado a um tenant por janela",
            ),
            OwnerMfaHashicorpVaultNextTenantExpansionDecision(
                key="classification",
                status=status,
                summary="review libera apenas iniciar nova review de expansão, não ativa o próximo tenant",
            ),
        )

    def _runbook(self, *, status: str) -> tuple[str, ...]:
        if status == "paused":
            return (
                "manter provider ativo nos tenants já saudáveis",
                "não selecionar novo tenant até nova decisão operacional",
                "preservar evidências do canário e do target atual",
            )
        return (
            "selecionar apenas um próximo tenant aprovado",
            "executar tenant expansion review para o próximo tenant",
            "não ativar flags/env nesta review",
            "repetir evidence e monitoring próprios para o próximo tenant",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "Owner MFA Hashicorp Vault Tenant Expansion Review",
                "Owner MFA Hashicorp Vault Expansion Cadence Closure Review",
            )
        if status == "paused":
            return (
                "Owner MFA Hashicorp Vault Expansion Cadence Closure Review",
                "Owner MFA Vault/KMS Rotation Runbook Review",
            )
        return (
            "Owner MFA Hashicorp Vault Target Post-Expansion Monitoring Review",
            "Owner MFA Hashicorp Vault Tenant Expansion Review",
        )


owner_mfa_hashicorp_vault_next_tenant_expansion_queries = (
    OwnerMfaHashicorpVaultNextTenantExpansionQueryService()
)
