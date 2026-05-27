from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.owner_mfa_legacy_data_global_sweep_queries import owner_mfa_legacy_data_global_sweep_queries
from app.modules.accounts.application.owner_mfa_secret_storage import owner_mfa_secret_storage


@dataclass(frozen=True)
class OwnerMfaLocalSecretParserRemovalDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaLocalSecretParserRemovalQueryService:
    def get_review(self) -> dict[str, object]:
        sweep = owner_mfa_legacy_data_global_sweep_queries.get_sweep()
        allow_local_plain = owner_mfa_secret_storage.can_accept_local_plain()
        blockers = list(sweep.get("blockers", ()))
        if allow_local_plain:
            blockers.append("local-secret-env-enabled")
        if sweep["status"] == "watch":
            blockers.append("no-active-totp-factors-to-prove-parser-removal")
        unique_blockers = tuple(dict.fromkeys(blockers))
        status = "ready" if not unique_blockers and sweep["status"] == "ready" else "blocked"
        return {
            "result": f"owner-mfa-local-secret-parser-removal-{status}",
            "ready": status == "ready",
            "status": status,
            "allow_local_plain": allow_local_plain,
            "sweep": sweep,
            "decisions": self._decisions(sweep=sweep, allow_local_plain=allow_local_plain),
            "blockers": unique_blockers,
            "parser_surfaces": self._parser_surfaces(),
            "removal_plan": self._removal_plan(),
            "rollback": self._rollback(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _decisions(
        self,
        *,
        sweep: dict[str, object],
        allow_local_plain: bool,
    ) -> tuple[OwnerMfaLocalSecretParserRemovalDecision, ...]:
        return (
            OwnerMfaLocalSecretParserRemovalDecision(
                key="global-sweep",
                status=str(sweep["status"]),
                summary="sweep global precisa estar ready antes de remover parser local/legado",
            ),
            OwnerMfaLocalSecretParserRemovalDecision(
                key="local-env-disabled",
                status="ready" if not allow_local_plain else "blocked",
                summary="OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET não pode estar habilitado durante remoção do parser",
            ),
            OwnerMfaLocalSecretParserRemovalDecision(
                key="rollback-mode",
                status="reduced",
                summary="rollback via env deixa de bastar depois da remoção do parser; rollback vira deploy/revert",
            ),
            OwnerMfaLocalSecretParserRemovalDecision(
                key="execution",
                status="review-only",
                summary="esta wave não remove parser; apenas prepara a execution review",
            ),
        )

    def _parser_surfaces(self) -> tuple[str, ...]:
        return (
            "accounts.application.owner_mfa_secret_storage.LOCAL_PREFIX",
            "OwnerMfaSecretStorageResolver.resolve branch local/plain",
            "OwnerMfaSecretStorageResolver.can_accept_local_plain",
            "owner_mfa_secret_storage_readiness local-secret-disabled",
            "migration/execution tests que criam plain: como fonte de migração",
        )

    def _removal_plan(self) -> tuple[str, ...]:
        return (
            "remover aceitação de valor sem ref: no resolver ou reclassificar como unsupported-local",
            "manter apenas ref:<path> e missing como modos válidos para TOTP ativo",
            "ajustar migration plan para apontar unsupported-local como blocker/cleanup, não segredo migrável",
            "atualizar testes legados para fixtures externas ou testes de unsupported-local",
            "rodar sweep global novamente após patch",
        )

    def _rollback(self) -> tuple[str, ...]:
        return (
            "reverter deploy que removeu parser local",
            "restaurar OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=1 apenas após revert de código",
            "rodar owner_mfa_secret_storage_readiness e provider health para o tenant afetado",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "Owner MFA Local Secret Parser Removal Execution Review",
                "Owner MFA Vault/KMS Provider Review",
            )
        return (
            "Owner MFA Tenant Legacy Cleanup Plan",
            "Owner MFA Legacy Data Global Sweep Review",
        )


owner_mfa_local_secret_parser_removal_queries = OwnerMfaLocalSecretParserRemovalQueryService()
