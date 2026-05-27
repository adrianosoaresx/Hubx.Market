from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.owner_mfa_hashicorp_vault_tenant_expansion_queries import (
    owner_mfa_hashicorp_vault_tenant_expansion_queries,
)


def _string(value: object, *, limit: int = 255) -> str:
    return str(value or "").strip()[:limit]


@dataclass(frozen=True)
class OwnerMfaHashicorpVaultTenantExpansionEvidenceDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaHashicorpVaultTenantExpansionEvidenceQueryService:
    confirmations = (
        "target_flags_enabled",
        "target_activation_evidence_captured",
        "target_monitoring_scheduled",
        "target_owner_login_challenge_passed",
        "target_provider_health_ready",
        "rollback_not_required",
        "evidence_redacted",
    )

    def get_evidence(
        self,
        *,
        canary_tenant_id: int | str | None,
        target_tenant_id: int | str | None,
        probe_reference: object = "owners/vault-kms/hashicorp-vault-probe",
        canary_owner_email: object = "",
        monitoring_window_elapsed: bool = False,
        provider_health_stable: bool = False,
        owner_login_error_spike_absent: bool = False,
        support_incidents_absent: bool = False,
        rollback_signal_absent: bool = False,
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
        evidence_redacted: bool = False,
    ) -> dict[str, object]:
        target_id = _string(target_tenant_id, limit=64)
        review = owner_mfa_hashicorp_vault_tenant_expansion_queries.get_review(
            canary_tenant_id=canary_tenant_id,
            target_tenant_ids=target_id,
            probe_reference=_string(probe_reference),
            canary_owner_email=canary_owner_email,
            monitoring_window_elapsed=monitoring_window_elapsed,
            provider_health_stable=provider_health_stable,
            owner_login_error_spike_absent=owner_login_error_spike_absent,
            support_incidents_absent=support_incidents_absent,
            rollback_signal_absent=rollback_signal_absent,
            evidence_redacted=canary_evidence_redacted,
            rollback_runbook_confirmed=rollback_runbook_confirmed,
            residual_risks_accepted=residual_risks_accepted,
            tenant_expansion_plan_documented=tenant_expansion_plan_documented,
            expansion_window_confirmed=expansion_window_confirmed,
            per_tenant_evidence_required=per_tenant_evidence_required,
            support_standby_confirmed=support_standby_confirmed,
            rollback_window_confirmed=rollback_window_confirmed,
            max_parallel_tenants=1,
        )
        confirmation_values = {
            "target_flags_enabled": bool(target_flags_enabled),
            "target_activation_evidence_captured": bool(target_activation_evidence_captured),
            "target_monitoring_scheduled": bool(target_monitoring_scheduled),
            "target_owner_login_challenge_passed": bool(target_owner_login_challenge_passed),
            "target_provider_health_ready": bool(target_provider_health_ready),
            "rollback_not_required": bool(rollback_not_required),
            "evidence_redacted": bool(evidence_redacted),
        }
        blockers = self._blockers(review=review, confirmations=confirmation_values)
        status = "ready" if not blockers else "blocked"
        target = review["target_tenants"][0] if review["target_tenants"] else {}
        return {
            "result": f"owner-mfa-hashicorp-vault-tenant-expansion-evidence-{status}",
            "ready": status == "ready",
            "status": status,
            "canary_tenant_id": review["canary_tenant_id"],
            "target_tenant_id": target_id,
            "target_tenant": target,
            "target_provider": "hashicorp-vault",
            "review": review,
            "confirmations": confirmation_values,
            "evidence_pack": self._evidence_pack(review=review, confirmations=confirmation_values, target=target),
            "decisions": self._decisions(review=review, confirmations=confirmation_values, status=status),
            "rollback": self._rollback(),
            "blockers": blockers,
            "next_tracks": self._next_tracks(status=status),
        }

    def _blockers(
        self,
        *,
        review: dict[str, object],
        confirmations: dict[str, bool],
    ) -> tuple[str, ...]:
        blockers: list[str] = []
        if not review["ready"]:
            blockers.extend(f"review:{blocker}" for blocker in review["blockers"])
            blockers.append(f"review:{review['status']}")
        for key, confirmed in confirmations.items():
            if not confirmed:
                blockers.append(f"confirmation-missing:{key}")
        return tuple(dict.fromkeys(blockers))

    def _evidence_pack(
        self,
        *,
        review: dict[str, object],
        confirmations: dict[str, bool],
        target: dict[str, object],
    ) -> tuple[str, ...]:
        return (
            f"review_status={review['status']}",
            f"canary_tenant_id={review['canary_tenant_id']}",
            f"target_tenant_id={target.get('tenant_id', '')}",
            f"target_tenant_slug={target.get('tenant_slug', '')}",
            f"target_flags_enabled={confirmations['target_flags_enabled']}",
            f"target_activation_evidence_captured={confirmations['target_activation_evidence_captured']}",
            f"target_monitoring_scheduled={confirmations['target_monitoring_scheduled']}",
            f"target_owner_login_challenge_passed={confirmations['target_owner_login_challenge_passed']}",
            f"target_provider_health_ready={confirmations['target_provider_health_ready']}",
            f"rollback_not_required={confirmations['rollback_not_required']}",
            f"evidence_redacted={confirmations['evidence_redacted']}",
        )

    def _decisions(
        self,
        *,
        review: dict[str, object],
        confirmations: dict[str, bool],
        status: str,
    ) -> tuple[OwnerMfaHashicorpVaultTenantExpansionEvidenceDecision, ...]:
        return (
            OwnerMfaHashicorpVaultTenantExpansionEvidenceDecision(
                key="tenant-expansion-review",
                status=str(review["status"]),
                summary="evidence execution só segue quando a review de expansão está READY",
            ),
            OwnerMfaHashicorpVaultTenantExpansionEvidenceDecision(
                key="target-activation",
                status=(
                    "ready"
                    if confirmations["target_flags_enabled"] and confirmations["target_activation_evidence_captured"]
                    else "blocked"
                ),
                summary="flags e activation evidence do target precisam ser confirmadas fora do command",
            ),
            OwnerMfaHashicorpVaultTenantExpansionEvidenceDecision(
                key="target-runtime-validation",
                status=(
                    "ready"
                    if confirmations["target_owner_login_challenge_passed"]
                    and confirmations["target_provider_health_ready"]
                    and confirmations["target_monitoring_scheduled"]
                    else "blocked"
                ),
                summary="target precisa ter login/challenge, provider health e monitoring agendado",
            ),
            OwnerMfaHashicorpVaultTenantExpansionEvidenceDecision(
                key="rollback-redaction",
                status=(
                    "ready"
                    if confirmations["rollback_not_required"] and confirmations["evidence_redacted"]
                    else "blocked"
                ),
                summary="rollback não pode ser necessário e evidence precisa permanecer redigida",
            ),
            OwnerMfaHashicorpVaultTenantExpansionEvidenceDecision(
                key="classification",
                status=status,
                summary="evidence registra execução declarativa sem promover expansão global",
            ),
        )

    def _rollback(self) -> tuple[str, ...]:
        return (
            "se target falhar, desabilitar flags Hashicorp Vault apenas para o tenant-alvo",
            "interromper expansão para próximos tenants",
            "preservar canário se monitoring permanecer HEALTHY",
            "reexecutar tenant expansion review antes de nova tentativa",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "Owner MFA Hashicorp Vault Target Post-Expansion Monitoring Review",
                "Owner MFA Vault/KMS Rotation Runbook Review",
            )
        return (
            "Owner MFA Hashicorp Vault Tenant Expansion Review",
            "Owner MFA Vault/KMS Production Closure Review",
        )


owner_mfa_hashicorp_vault_tenant_expansion_evidence_queries = (
    OwnerMfaHashicorpVaultTenantExpansionEvidenceQueryService()
)
