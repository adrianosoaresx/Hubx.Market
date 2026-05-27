from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.owner_mfa_local_secret_retirement_execution_queries import owner_mfa_local_secret_retirement_execution_queries
from app.modules.accounts.application.owner_mfa_provider_health_closure_queries import owner_mfa_provider_health_closure_queries


@dataclass(frozen=True)
class OwnerMfaLocalSecretCodeRetirementDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaLocalSecretCodeRetirementQueryService:
    def get_readiness(self, *, tenant_id: int | str | None) -> dict[str, object]:
        retirement_after = owner_mfa_local_secret_retirement_execution_queries.get_evidence(tenant_id=tenant_id, phase="after")
        provider_closure = owner_mfa_provider_health_closure_queries.get_closure(tenant_id=tenant_id)
        blockers = []
        if not retirement_after["ready"]:
            blockers.extend(f"retirement-after:{blocker}" for blocker in retirement_after["blockers"])
        if provider_closure["status"] == "blocked":
            blockers.extend(f"provider-closure:{blocker}" for blocker in provider_closure["blockers"])
        if retirement_after["allow_local_plain"]:
            blockers.append("local-secret-setting-enabled")
        if int(retirement_after["local_plain_count"]) > 0:
            blockers.append("local-plain-factors-present")
        if int(retirement_after["external_reference_count"]) == 0:
            blockers.append("external-reference-factors-missing")
        unique_blockers = tuple(dict.fromkeys(blockers))
        status = "ready"
        if provider_closure["status"] == "watch" and not unique_blockers:
            status = "watch"
        if unique_blockers:
            status = "blocked"
        return {
            "result": f"owner-mfa-local-secret-code-retirement-{status}",
            "ready": status == "ready",
            "status": status,
            "tenant_id": str(tenant_id or "").strip(),
            "retirement_after": retirement_after,
            "provider_closure": provider_closure,
            "decisions": self._decisions(retirement_after=retirement_after, provider_closure=provider_closure),
            "blockers": unique_blockers,
            "code_surfaces": self._code_surfaces(),
            "residual_risks": self._residual_risks(),
            "next_tracks": self._next_tracks(),
        }

    def _decisions(
        self,
        *,
        retirement_after: dict[str, object],
        provider_closure: dict[str, object],
    ) -> tuple[OwnerMfaLocalSecretCodeRetirementDecision, ...]:
        return (
            OwnerMfaLocalSecretCodeRetirementDecision(
                key="setting-disabled",
                status="ready" if not retirement_after["allow_local_plain"] else "blocked",
                summary="OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET deve estar false antes de remover tolerância de código",
            ),
            OwnerMfaLocalSecretCodeRetirementDecision(
                key="no-local-factors",
                status="ready" if int(retirement_after["local_plain_count"]) == 0 else "blocked",
                summary="nenhum fator TOTP ativo deve permanecer em local/plain",
            ),
            OwnerMfaLocalSecretCodeRetirementDecision(
                key="provider-health-closure",
                status=str(provider_closure["status"]),
                summary="provider health, métricas, alertas e dashboard precisam estar fechados ou em watch consciente",
            ),
            OwnerMfaLocalSecretCodeRetirementDecision(
                key="code-removal",
                status="review-only",
                summary="esta wave não remove suporte local; apenas decide se uma execution posterior é segura",
            ),
        )

    def _code_surfaces(self) -> tuple[str, ...]:
        return (
            "accounts.application.owner_mfa_secret_storage.LOCAL_PREFIX",
            "accounts.application.owner_mfa_secret_storage.OwnerMfaSecretStorageResolver.can_accept_local_plain",
            "accounts.application.owner_mfa_secret_storage_readiness_queries local-secret-disabled",
            "settings.OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET",
            "tests que cobrem plain:/legado e rollback local",
        )

    def _residual_risks(self) -> tuple[str, ...]:
        return (
            "remover suporte local reduz rollback rápido se provider externo falhar",
            "fixtures ou dados legados fora do tenant avaliado ainda podem depender de plain:/legado",
            "ambientes sem Prometheus/Grafana ativados ainda dependem de comandos manuais",
            "vault/KMS real ainda não substituiu o provider env mínimo",
        )

    def _next_tracks(self) -> tuple[str, ...]:
        return (
            "Owner MFA Local Secret Code Retirement Execution Review",
            "Owner MFA Vault/KMS Provider Review",
            "Owner MFA Legacy Data Global Sweep Review",
        )


owner_mfa_local_secret_code_retirement_queries = OwnerMfaLocalSecretCodeRetirementQueryService()
