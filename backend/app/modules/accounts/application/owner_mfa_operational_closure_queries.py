from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.owner_mfa_login_enforcement_readiness_queries import owner_mfa_login_enforcement_readiness_queries


@dataclass
class OwnerMfaOperationalClosureQueryService:
    def get_closure(self, *, tenant_id: int | str | None) -> dict[str, object]:
        enforcement = owner_mfa_login_enforcement_readiness_queries.get_readiness(tenant_id=tenant_id)
        decisions = (
            {"key": "admin-surface", "status": "ready", "summary": "/ops/owners/mfa/ lista, verifica e desativa fatores"},
            {"key": "break-glass-readiness", "status": "ready" if enforcement["break_glass"].get("ready") else "blocked", "summary": "break-glass possui contrato de settings e owners ativos"},
            {"key": "login-enforcement-readiness", "status": "ready" if enforcement.get("ready") else "blocked", "summary": "enforcement depende de OWNER_MFA_REQUIRED, enrollment e break-glass"},
            {"key": "login-enforcement-execution", "status": "ready", "summary": "login exige challenge MFA antes da sessão quando OWNER_MFA_REQUIRED=True"},
        )
        blockers = tuple(enforcement.get("blockers", ()))
        return {
            "result": "owner-mfa-operational-closure-ready" if not blockers else "owner-mfa-operational-closure-blocked",
            "ready": not blockers,
            "decisions": decisions,
            "blockers": blockers,
            "residual_risks": (
                "ambiente pode manter enforcement desligado via OWNER_MFA_REQUIRED=0 para rollback",
                "surface admin ainda não registra fator/QR code pelo browser",
                "segredo TOTP ainda não usa vault/provider externo",
                "recovery codes são exibidos apenas uma vez e exigem captura operacional segura",
            ),
            "next_tracks": (
                "Owner MFA Secret Storage Hardening Review",
                "Owner MFA Break-Glass Bypass Execution Review",
                "Owner MFA Recovery Codes Admin Surface Review",
            ),
        }


owner_mfa_operational_closure_queries = OwnerMfaOperationalClosureQueryService()
