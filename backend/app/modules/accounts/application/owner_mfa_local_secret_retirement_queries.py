from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.owner_mfa_secret_storage_readiness_queries import owner_mfa_secret_storage_readiness_queries


@dataclass
class OwnerMfaLocalSecretRetirementQueryService:
    def get_readiness(self, *, tenant_id: int | str | None) -> dict[str, object]:
        storage = owner_mfa_secret_storage_readiness_queries.get_readiness(tenant_id=tenant_id)
        blockers = list(storage.get("blockers", ()))
        local_plain_count = int(storage.get("local_plain_count", 0))
        external_reference_count = int(storage.get("external_reference_count", 0))
        missing_count = int(storage.get("missing_count", 0))
        if local_plain_count:
            blockers.append("local-plain-factors-present")
        if missing_count:
            blockers.append("missing-secret-factors-present")
        if not storage.get("ready"):
            blockers.append("secret-storage-readiness-blocked")
        unique_blockers = tuple(dict.fromkeys(blockers))
        return {
            "result": "owner-mfa-local-secret-retirement-ready" if not unique_blockers else "owner-mfa-local-secret-retirement-blocked",
            "ready": not unique_blockers,
            "storage_result": storage.get("result"),
            "allow_local_plain": storage.get("allow_local_plain"),
            "local_plain_count": local_plain_count,
            "external_reference_count": external_reference_count,
            "missing_count": missing_count,
            "items": storage.get("items", ()),
            "blockers": unique_blockers,
            "setting_target": "OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False",
            "runbook": (
                "1. confirmar que local_plain_count=0 para o tenant",
                "2. confirmar que external_reference_count cobre os fatores TOTP ativos esperados",
                "3. rodar challenge/login MFA amostral com provider externo ativo",
                "4. aplicar OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False no ambiente",
                "5. rodar owner_mfa_secret_storage_readiness novamente",
                "6. monitorar falhas de login/challenge MFA owner/admin",
            ),
            "rollback": (
                "restaurar OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=True",
                "manter secret_reference em ref:<path> quando provider estiver saudável",
                "reabrir migração TOTP se algum fator local reaparecer",
            ),
            "next_tracks": (
                "Owner MFA Local Secret Retirement Execution Review",
                "Owner MFA Provider Health Monitoring Review",
            ),
        }


owner_mfa_local_secret_retirement_queries = OwnerMfaLocalSecretRetirementQueryService()
