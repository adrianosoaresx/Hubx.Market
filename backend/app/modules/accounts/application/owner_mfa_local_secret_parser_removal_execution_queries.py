from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.owner_mfa_local_secret_parser_removal_queries import (
    owner_mfa_local_secret_parser_removal_queries,
)
from app.modules.accounts.application.owner_mfa_secret_storage import owner_mfa_secret_storage


@dataclass(frozen=True)
class OwnerMfaLocalSecretParserRemovalExecutionDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaLocalSecretParserRemovalExecutionQueryService:
    def get_evidence(self) -> dict[str, object]:
        review = owner_mfa_local_secret_parser_removal_queries.get_review()
        local_probe = owner_mfa_secret_storage.resolve("plain:GEZDGNBVGY3TQOJQ")
        legacy_probe = owner_mfa_secret_storage.resolve("GEZDGNBVGY3TQOJQ")
        probe_blocked = self._probe_blocked(local_probe) and self._probe_blocked(legacy_probe)
        blockers = list(review.get("blockers", ()))
        if not probe_blocked:
            blockers.append("local-parser-still-resolves-secret")
        unique_blockers = tuple(dict.fromkeys(blockers))
        status = "ready" if review["ready"] and probe_blocked and not unique_blockers else "blocked"
        return {
            "result": f"owner-mfa-local-secret-parser-removal-execution-{status}",
            "ready": status == "ready",
            "status": status,
            "review": review,
            "local_probe": {
                "storage_mode": local_probe.storage_mode,
                "ready": local_probe.ready,
                "result": local_probe.result,
                "secret_returned": bool(local_probe.secret),
            },
            "legacy_probe": {
                "storage_mode": legacy_probe.storage_mode,
                "ready": legacy_probe.ready,
                "result": legacy_probe.result,
                "secret_returned": bool(legacy_probe.secret),
            },
            "decisions": self._decisions(review=review, probe_blocked=probe_blocked),
            "blockers": unique_blockers,
            "rollback": self._rollback(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _probe_blocked(self, resolution) -> bool:
        return (
            resolution.storage_mode == "unsupported-local"
            and resolution.result == "owner-mfa-secret-local-unsupported"
            and not resolution.ready
            and not resolution.secret
        )

    def _decisions(
        self,
        *,
        review: dict[str, object],
        probe_blocked: bool,
    ) -> tuple[OwnerMfaLocalSecretParserRemovalExecutionDecision, ...]:
        return (
            OwnerMfaLocalSecretParserRemovalExecutionDecision(
                key="review-ready",
                status="ready" if review["ready"] else "blocked",
                summary="review global precisa estar ready antes de considerar execução concluída",
            ),
            OwnerMfaLocalSecretParserRemovalExecutionDecision(
                key="parser-local-blocked",
                status="ready" if probe_blocked else "blocked",
                summary="plain: e valor legado sem ref: devem retornar unsupported-local sem segredo",
            ),
            OwnerMfaLocalSecretParserRemovalExecutionDecision(
                key="rollback-mode",
                status="deploy-revert",
                summary="rollback agora exige revert/deploy de código; env não reativa parser local",
            ),
        )

    def _rollback(self) -> tuple[str, ...]:
        return (
            "reverter deploy que tornou local/plain unsupported-local",
            "rodar owner_mfa_local_secret_parser_removal_execute para confirmar parser restaurado se rollback for necessário",
            "executar owner_mfa_secret_storage_readiness por tenant afetado antes de novo rollout",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "Owner MFA Vault/KMS Provider Review",
                "Owner MFA Tenant Legacy Cleanup Plan",
            )
        return (
            "Owner MFA Legacy Data Global Sweep Review",
            "Owner MFA Local Secret Parser Removal Review",
        )


owner_mfa_local_secret_parser_removal_execution_queries = OwnerMfaLocalSecretParserRemovalExecutionQueryService()
