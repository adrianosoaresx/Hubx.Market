from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.owner_mfa_local_secret_retirement_queries import owner_mfa_local_secret_retirement_queries


def _phase(value: object) -> str:
    normalized = str(value or "").strip().lower().replace("_", "-")
    if normalized in {"after", "post", "post-activation"}:
        return "after"
    return "before"


@dataclass
class OwnerMfaLocalSecretRetirementExecutionQueryService:
    def get_evidence(self, *, tenant_id: int | str | None, phase: object = "before") -> dict[str, object]:
        normalized_phase = _phase(phase)
        readiness = owner_mfa_local_secret_retirement_queries.get_readiness(tenant_id=tenant_id)
        blockers = list(readiness.get("blockers", ()))
        allow_local_plain = bool(readiness.get("allow_local_plain", True))
        if normalized_phase == "after" and allow_local_plain:
            blockers.append("local-secret-setting-still-enabled")
        unique_blockers = tuple(dict.fromkeys(blockers))
        return {
            "result": self._result(phase=normalized_phase, blockers=unique_blockers),
            "ready": not unique_blockers,
            "phase": normalized_phase,
            "retirement_result": readiness.get("result"),
            "allow_local_plain": allow_local_plain,
            "setting_current": f"OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET={'True' if allow_local_plain else 'False'}",
            "setting_expected": "OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False" if normalized_phase == "after" else "OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=True ou False",
            "local_plain_count": readiness.get("local_plain_count", 0),
            "external_reference_count": readiness.get("external_reference_count", 0),
            "missing_count": readiness.get("missing_count", 0),
            "items": readiness.get("items", ()),
            "blockers": unique_blockers,
            "evidence": self._evidence_steps(normalized_phase),
            "rollback": (
                "restaurar OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=True no ambiente",
                "reexecutar owner_mfa_secret_storage_readiness",
                "confirmar login/challenge MFA owner/admin",
            ),
            "next_tracks": (
                "Owner MFA Provider Health Monitoring Review",
                "Owner MFA Local Secret Code Retirement Review",
            ),
        }

    def _result(self, *, phase: str, blockers: tuple[str, ...]) -> str:
        if blockers:
            return f"owner-mfa-local-secret-retirement-{phase}-blocked"
        return f"owner-mfa-local-secret-retirement-{phase}-ready"

    def _evidence_steps(self, phase: str) -> tuple[str, ...]:
        if phase == "after":
            return (
                "capturar output pós-ativação deste comando",
                "capturar output de owner_mfa_secret_storage_readiness",
                "capturar login/challenge MFA amostral com provider externo",
                "capturar ausência de blockers local-secret-setting-still-enabled",
            )
        return (
            "capturar output pré-ativação deste comando",
            "capturar local_plain_count=0",
            "capturar external_reference_count esperado",
            "aplicar OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False fora do app",
        )


owner_mfa_local_secret_retirement_execution_queries = OwnerMfaLocalSecretRetirementExecutionQueryService()
