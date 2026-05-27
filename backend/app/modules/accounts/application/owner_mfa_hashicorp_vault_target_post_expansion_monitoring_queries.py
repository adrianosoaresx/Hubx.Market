from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.owner_mfa_hashicorp_vault_tenant_expansion_evidence_queries import (
    owner_mfa_hashicorp_vault_tenant_expansion_evidence_queries,
)


def _string(value: object, *, limit: int = 255) -> str:
    return str(value or "").strip()[:limit]


@dataclass(frozen=True)
class OwnerMfaHashicorpVaultTargetPostExpansionMonitoringDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaHashicorpVaultTargetPostExpansionMonitoringQueryService:
    def get_review(
        self,
        *,
        canary_tenant_id: int | str | None,
        target_tenant_id: int | str | None,
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
    ) -> dict[str, object]:
        evidence = owner_mfa_hashicorp_vault_tenant_expansion_evidence_queries.get_evidence(
            canary_tenant_id=canary_tenant_id,
            target_tenant_id=target_tenant_id,
            probe_reference=_string(probe_reference),
            canary_owner_email=canary_owner_email,
            monitoring_window_elapsed=canary_monitoring_window_elapsed,
            provider_health_stable=canary_provider_health_stable,
            owner_login_error_spike_absent=canary_owner_login_error_spike_absent,
            support_incidents_absent=canary_support_incidents_absent,
            rollback_signal_absent=canary_rollback_signal_absent,
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
            evidence_redacted=expansion_evidence_redacted,
        )
        signals = {
            "target_monitoring_window_elapsed": bool(target_monitoring_window_elapsed),
            "target_provider_health_stable": bool(target_provider_health_stable),
            "target_owner_login_error_spike_absent": bool(target_owner_login_error_spike_absent),
            "target_support_incidents_absent": bool(target_support_incidents_absent),
            "target_rollback_signal_absent": bool(target_rollback_signal_absent),
            "evidence_redacted": bool(evidence_redacted),
        }
        blockers = self._blockers(evidence=evidence, signals=signals)
        status = self._status(evidence_ready=bool(evidence["ready"]), signals=signals, blockers=blockers)
        return {
            "result": f"owner-mfa-hashicorp-vault-target-post-expansion-monitoring-{status}",
            "ready": status == "healthy",
            "status": status,
            "classification": status.upper(),
            "canary_tenant_id": evidence["canary_tenant_id"],
            "target_tenant_id": evidence["target_tenant_id"],
            "target_tenant": evidence["target_tenant"],
            "target_provider": "hashicorp-vault",
            "expansion_evidence": evidence,
            "signals": signals,
            "decisions": self._decisions(evidence=evidence, signals=signals, status=status),
            "watch_items": self._watch_items(signals=signals),
            "rollback": self._rollback(status=status),
            "blockers": blockers,
            "next_tracks": self._next_tracks(status=status),
        }

    def _status(
        self,
        *,
        evidence_ready: bool,
        signals: dict[str, bool],
        blockers: tuple[str, ...],
    ) -> str:
        if not evidence_ready:
            return "blocked"
        if not signals["target_rollback_signal_absent"]:
            return "rollback"
        if blockers:
            return "blocked"
        if all(signals.values()):
            return "healthy"
        return "watch"

    def _blockers(self, *, evidence: dict[str, object], signals: dict[str, bool]) -> tuple[str, ...]:
        blockers: list[str] = []
        if not evidence["ready"]:
            blockers.extend(f"evidence:{blocker}" for blocker in evidence["blockers"])
            blockers.append(f"evidence:{evidence['status']}")
        if not signals["target_rollback_signal_absent"]:
            blockers.append("target-rollback-signal-present")
        if not signals["evidence_redacted"]:
            blockers.append("evidence-redaction-missing")
        return tuple(dict.fromkeys(blockers))

    def _decisions(
        self,
        *,
        evidence: dict[str, object],
        signals: dict[str, bool],
        status: str,
    ) -> tuple[OwnerMfaHashicorpVaultTargetPostExpansionMonitoringDecision, ...]:
        return (
            OwnerMfaHashicorpVaultTargetPostExpansionMonitoringDecision(
                key="target-expansion-evidence",
                status=str(evidence["status"]),
                summary="monitoring do target só segue quando a evidence de expansão está READY",
            ),
            OwnerMfaHashicorpVaultTargetPostExpansionMonitoringDecision(
                key="target-provider-health",
                status="ready" if signals["target_provider_health_stable"] else "watch",
                summary="provider health do target precisa permanecer estável durante a janela",
            ),
            OwnerMfaHashicorpVaultTargetPostExpansionMonitoringDecision(
                key="target-login-support",
                status=(
                    "ready"
                    if signals["target_owner_login_error_spike_absent"] and signals["target_support_incidents_absent"]
                    else "watch"
                ),
                summary="login/challenge owner e suporte do target não podem indicar regressão",
            ),
            OwnerMfaHashicorpVaultTargetPostExpansionMonitoringDecision(
                key="target-rollback-signal",
                status="ready" if signals["target_rollback_signal_absent"] else "rollback",
                summary="rollback signal no target interrompe expansão para próximos tenants",
            ),
            OwnerMfaHashicorpVaultTargetPostExpansionMonitoringDecision(
                key="classification",
                status=status,
                summary="classificação final decide se próximo tenant pode ser considerado",
            ),
        )

    def _watch_items(self, *, signals: dict[str, bool]) -> tuple[str, ...]:
        items = []
        if not signals["target_monitoring_window_elapsed"]:
            items.append("target-monitoring-window-not-elapsed")
        if not signals["target_provider_health_stable"]:
            items.append("target-provider-health-not-stable")
        if not signals["target_owner_login_error_spike_absent"]:
            items.append("target-owner-login-error-spike-present")
        if not signals["target_support_incidents_absent"]:
            items.append("target-support-incidents-present")
        if not signals["evidence_redacted"]:
            items.append("evidence-redaction-missing")
        return tuple(items)

    def _rollback(self, *, status: str) -> tuple[str, ...]:
        if status == "rollback":
            return (
                "desabilitar flags Hashicorp Vault apenas para o tenant-alvo",
                "interromper expansão para próximos tenants",
                "reexecutar tenant expansion evidence após rollback do target",
                "manter canário separado se seus sinais continuarem HEALTHY",
            )
        return (
            "não expandir para próximo tenant enquanto status for WATCH/BLOCKED",
            "se sinais piorarem, executar rollback operacional limitado ao target",
            "após HEALTHY, repetir review antes de escolher próximo tenant",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "healthy":
            return (
                "Owner MFA Hashicorp Vault Next Tenant Expansion Review",
                "Owner MFA Vault/KMS Rotation Runbook Review",
            )
        if status == "rollback":
            return (
                "Owner MFA Hashicorp Vault Target Rollback Evidence",
                "Owner MFA Hashicorp Vault Tenant Expansion Review",
            )
        return (
            "Owner MFA Hashicorp Vault Target Extended Monitoring Evidence",
            "Owner MFA Hashicorp Vault Tenant Expansion Evidence Execution",
        )


owner_mfa_hashicorp_vault_target_post_expansion_monitoring_queries = (
    OwnerMfaHashicorpVaultTargetPostExpansionMonitoringQueryService()
)
