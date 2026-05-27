from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.owner_mfa_vault_kms_provider_production_activation_evidence_queries import (
    owner_mfa_vault_kms_provider_production_activation_evidence_queries,
)


def _string(value: object, *, limit: int = 255) -> str:
    return str(value or "").strip()[:limit]


@dataclass(frozen=True)
class OwnerMfaHashicorpVaultPostActivationMonitoringDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaHashicorpVaultPostActivationMonitoringQueryService:
    def get_review(
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
    ) -> dict[str, object]:
        normalized_probe = _string(probe_reference, limit=255)
        activation = owner_mfa_vault_kms_provider_production_activation_evidence_queries.get_evidence(
            tenant_id=tenant_id,
            probe_reference=normalized_probe,
            canary_owner_email=canary_owner_email,
            deployment_completed=True,
            flags_enabled_for_tenant=True,
            post_deploy_probe_passed=True,
            owner_login_challenge_passed=True,
            provider_health_ready=True,
            rollback_not_required=True,
            evidence_redacted=True,
        )
        signals = {
            "monitoring_window_elapsed": bool(monitoring_window_elapsed),
            "provider_health_stable": bool(provider_health_stable),
            "owner_login_error_spike_absent": bool(owner_login_error_spike_absent),
            "support_incidents_absent": bool(support_incidents_absent),
            "rollback_signal_absent": bool(rollback_signal_absent),
            "evidence_redacted": bool(evidence_redacted),
        }
        blockers = list(activation.get("blockers", ()))
        if not activation.get("ready"):
            blockers.append("production-activation-evidence-not-ready")
        status = self._status(activation_ready=bool(activation.get("ready")), signals=signals)
        if not signals["rollback_signal_absent"]:
            blockers.append("rollback-signal-present")
        if not signals["evidence_redacted"]:
            blockers.append("evidence-redaction-missing")
        unique_blockers = tuple(dict.fromkeys(blockers))
        if unique_blockers and status != "rollback":
            status = "blocked"
        return {
            "result": f"owner-mfa-hashicorp-vault-post-activation-monitoring-{status}",
            "ready": status == "healthy",
            "status": status,
            "tenant_id": activation["tenant_id"],
            "target_provider": "hashicorp-vault",
            "canary_owner_email": activation["canary_owner_email"],
            "activation_evidence": activation,
            "signals": signals,
            "classification": status.upper(),
            "decisions": self._decisions(activation=activation, signals=signals, status=status),
            "watch_items": self._watch_items(signals=signals),
            "rollback": self._rollback(status=status),
            "blockers": unique_blockers,
            "next_tracks": self._next_tracks(status=status),
        }

    def _status(self, *, activation_ready: bool, signals: dict[str, bool]) -> str:
        if not activation_ready:
            return "blocked"
        if not signals["rollback_signal_absent"]:
            return "rollback"
        if all(signals.values()):
            return "healthy"
        return "watch"

    def _decisions(
        self,
        *,
        activation: dict[str, object],
        signals: dict[str, bool],
        status: str,
    ) -> tuple[OwnerMfaHashicorpVaultPostActivationMonitoringDecision, ...]:
        return (
            OwnerMfaHashicorpVaultPostActivationMonitoringDecision(
                key="activation-evidence",
                status=str(activation.get("status", "blocked")),
                summary="monitoramento pós-ativação só classifica produção após activation evidence ready",
            ),
            OwnerMfaHashicorpVaultPostActivationMonitoringDecision(
                key="provider-health",
                status="ready" if signals["provider_health_stable"] else "watch",
                summary="provider health precisa permanecer estável durante a janela pós-ativação",
            ),
            OwnerMfaHashicorpVaultPostActivationMonitoringDecision(
                key="owner-login-support",
                status=(
                    "ready"
                    if signals["owner_login_error_spike_absent"] and signals["support_incidents_absent"]
                    else "watch"
                ),
                summary="login/challenge owner e suporte não podem indicar regressão",
            ),
            OwnerMfaHashicorpVaultPostActivationMonitoringDecision(
                key="rollback-signal",
                status="ready" if signals["rollback_signal_absent"] else "rollback",
                summary="qualquer rollback signal forte exige parar expansão e executar rollback operacional",
            ),
            OwnerMfaHashicorpVaultPostActivationMonitoringDecision(
                key="classification",
                status=status,
                summary="classificação final orienta expansão, observação ou rollback",
            ),
        )

    def _watch_items(self, *, signals: dict[str, bool]) -> tuple[str, ...]:
        items = []
        if not signals["monitoring_window_elapsed"]:
            items.append("monitoring-window-not-elapsed")
        if not signals["provider_health_stable"]:
            items.append("provider-health-not-stable")
        if not signals["owner_login_error_spike_absent"]:
            items.append("owner-login-error-spike-present")
        if not signals["support_incidents_absent"]:
            items.append("support-incidents-present")
        if not signals["evidence_redacted"]:
            items.append("evidence-redaction-missing")
        return tuple(items)

    def _rollback(self, *, status: str) -> tuple[str, ...]:
        if status == "rollback":
            return (
                "desabilitar OWNER_MFA_HASHICORP_VAULT_ENDPOINT_ENABLED imediatamente",
                "desabilitar OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED se login/challenge estiver afetado",
                "interromper expansão para novos tenants",
                "reexecutar production activation evidence após rollback",
            )
        return (
            "manter rollback pronto durante a janela de observação",
            "não expandir para novos tenants enquanto status for WATCH/BLOCKED",
            "se sinais piorarem, executar rollback operacional documentado",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "healthy":
            return (
                "Owner MFA Vault/KMS Production Closure Review",
                "Owner MFA Hashicorp Vault Tenant Expansion Review",
            )
        if status == "watch":
            return (
                "Owner MFA Hashicorp Vault Extended Monitoring Evidence",
                "Owner MFA Hashicorp Vault Production Gate Review",
            )
        if status == "rollback":
            return (
                "Owner MFA Hashicorp Vault Rollback Evidence",
                "Owner MFA Vault/KMS Provider Production Readiness Review",
            )
        return (
            "Owner MFA Vault/KMS Provider Production Activation Evidence",
            "Owner MFA Hashicorp Vault Production Gate Review",
        )


owner_mfa_hashicorp_vault_post_activation_monitoring_queries = OwnerMfaHashicorpVaultPostActivationMonitoringQueryService()
