from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.owner_mfa_hashicorp_vault_post_activation_monitoring_queries import (
    owner_mfa_hashicorp_vault_post_activation_monitoring_queries,
)


def _string(value: object, *, limit: int = 255) -> str:
    return str(value or "").strip()[:limit]


@dataclass(frozen=True)
class OwnerMfaVaultKmsProductionClosureDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaVaultKmsProductionClosureQueryService:
    def get_closure(
        self,
        *,
        tenant_id: int | str | None,
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
    ) -> dict[str, object]:
        monitoring = owner_mfa_hashicorp_vault_post_activation_monitoring_queries.get_review(
            tenant_id=tenant_id,
            probe_reference=_string(probe_reference),
            canary_owner_email=canary_owner_email,
            monitoring_window_elapsed=monitoring_window_elapsed,
            provider_health_stable=provider_health_stable,
            owner_login_error_spike_absent=owner_login_error_spike_absent,
            support_incidents_absent=support_incidents_absent,
            rollback_signal_absent=rollback_signal_absent,
            evidence_redacted=evidence_redacted,
        )
        closure_signals = {
            "rollback_runbook_confirmed": bool(rollback_runbook_confirmed),
            "residual_risks_accepted": bool(residual_risks_accepted),
            "tenant_expansion_plan_documented": bool(tenant_expansion_plan_documented),
        }
        blockers = self._blockers(monitoring=monitoring, closure_signals=closure_signals)
        status = self._status(monitoring=monitoring, blockers=blockers)
        return {
            "result": f"owner-mfa-vault-kms-production-closure-{status}",
            "ready": status == "ready",
            "status": status,
            "tenant_id": monitoring["tenant_id"],
            "target_provider": "hashicorp-vault",
            "canary_owner_email": monitoring["canary_owner_email"],
            "monitoring": monitoring,
            "closure_signals": closure_signals,
            "decisions": self._decisions(monitoring=monitoring, closure_signals=closure_signals, status=status),
            "blockers": blockers,
            "residual_risks": self._residual_risks(),
            "expansion_guardrails": self._expansion_guardrails(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _status(self, *, monitoring: dict[str, object], blockers: tuple[str, ...]) -> str:
        if blockers:
            return "blocked"
        if monitoring["status"] == "healthy":
            return "ready"
        if monitoring["status"] == "rollback":
            return "rollback"
        return "watch"

    def _blockers(
        self,
        *,
        monitoring: dict[str, object],
        closure_signals: dict[str, bool],
    ) -> tuple[str, ...]:
        blockers: list[str] = []
        if monitoring["status"] == "rollback":
            blockers.append("monitoring:rollback-signal-present")
        elif monitoring["status"] != "healthy":
            blockers.append(f"monitoring:{monitoring['status']}")
        for blocker in monitoring["blockers"]:
            blockers.append(f"monitoring:{blocker}")
        if not closure_signals["rollback_runbook_confirmed"]:
            blockers.append("closure:rollback-runbook-not-confirmed")
        if not closure_signals["residual_risks_accepted"]:
            blockers.append("closure:residual-risks-not-accepted")
        if not closure_signals["tenant_expansion_plan_documented"]:
            blockers.append("closure:tenant-expansion-plan-not-documented")
        return tuple(dict.fromkeys(blockers))

    def _decisions(
        self,
        *,
        monitoring: dict[str, object],
        closure_signals: dict[str, bool],
        status: str,
    ) -> tuple[OwnerMfaVaultKmsProductionClosureDecision, ...]:
        return (
            OwnerMfaVaultKmsProductionClosureDecision(
                key="post-activation-monitoring",
                status=str(monitoring["status"]),
                summary="closure só pode fechar quando o monitoramento pós-ativação estiver healthy",
            ),
            OwnerMfaVaultKmsProductionClosureDecision(
                key="rollback-runbook",
                status="ready" if closure_signals["rollback_runbook_confirmed"] else "blocked",
                summary="rollback permanece operacional e precisa estar confirmado antes de expansão",
            ),
            OwnerMfaVaultKmsProductionClosureDecision(
                key="residual-risks",
                status="accepted" if closure_signals["residual_risks_accepted"] else "blocked",
                summary="riscos residuais precisam ser explicitamente aceitos para encerrar a trilha",
            ),
            OwnerMfaVaultKmsProductionClosureDecision(
                key="tenant-expansion",
                status="ready" if closure_signals["tenant_expansion_plan_documented"] else "blocked",
                summary="expansão para novos tenants exige plano documentado; o closure não expande automaticamente",
            ),
            OwnerMfaVaultKmsProductionClosureDecision(
                key="classification",
                status=status,
                summary="classificação final decide closure, watch, rollback ou bloqueio",
            ),
        )

    def _residual_risks(self) -> tuple[str, ...]:
        return (
            "Hashicorp Vault segue dependência externa crítica para login owner/admin com MFA",
            "rotação de token/role e auditoria de acesso ao cofre permanecem responsabilidade operacional",
            "tenant expansion ainda precisa ocorrer em janelas menores com evidência própria",
            "rollback de flags/env permanece manual e externo ao command",
        )

    def _expansion_guardrails(self) -> tuple[str, ...]:
        return (
            "expandir um tenant por janela até acumular evidência estável",
            "reexecutar activation evidence e post-activation monitoring por tenant",
            "não reutilizar evidence do tenant canário como autorização global",
            "manter rollback window ativa durante cada expansão",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "Owner MFA Hashicorp Vault Tenant Expansion Review",
                "Owner MFA Vault/KMS Rotation Runbook Review",
                "Owner MFA Audit Evidence Export Review",
            )
        if status == "rollback":
            return (
                "Owner MFA Hashicorp Vault Rollback Evidence",
                "Owner MFA Vault/KMS Provider Production Readiness Review",
            )
        return (
            "Owner MFA Hashicorp Vault Post-Activation Monitoring Review",
            "Owner MFA Vault/KMS Provider Production Activation Evidence",
        )


owner_mfa_vault_kms_production_closure_queries = OwnerMfaVaultKmsProductionClosureQueryService()
