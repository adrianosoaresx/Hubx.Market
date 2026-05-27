from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.owner_mfa_sso_readiness_queries import owner_mfa_sso_readiness_queries


@dataclass(frozen=True)
class OwnerMfaEnrollmentClosureDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaEnrollmentClosureQueryService:
    def get_closure(self) -> dict[str, object]:
        mfa_sso = owner_mfa_sso_readiness_queries.get_readiness()
        decisions = (
            OwnerMfaEnrollmentClosureDecision(
                key="mfa-factor-model",
                status="ready",
                summary="OwnerMfaFactor persiste enrollment tenant-scoped por OwnerUser",
            ),
            OwnerMfaEnrollmentClosureDecision(
                key="mfa-enrollment-readiness",
                status="ready",
                summary="owner_mfa_enrollment_readiness lista owners ativos com fator ativo/verificado",
            ),
            OwnerMfaEnrollmentClosureDecision(
                key="mfa-enrollment-commands",
                status="ready",
                summary="owner_mfa_factor registra/verifica/desativa fator de forma auditável",
            ),
            OwnerMfaEnrollmentClosureDecision(
                key="mfa-challenge-verification",
                status="ready",
                summary="TOTP interno valida challenge e marca fator ativo como verificado",
            ),
            OwnerMfaEnrollmentClosureDecision(
                key="mfa-login-enforcement",
                status="out-of-scope",
                summary="login owner/admin ainda não exige MFA",
            ),
        )
        return {
            "result": "owner-mfa-enrollment-closure-ready",
            "ready": True,
            "mfa_sso_mode": mfa_sso["mode"],
            "decisions": decisions,
            "residual_risks": self._residual_risks(),
            "next_tracks": self._next_tracks(),
        }

    def _residual_risks(self) -> tuple[str, ...]:
        return (
            "não há UI admin dedicada para enrollment MFA",
            "não há recovery codes reais nem rotação de segredo",
            "login ainda não aplica enforcement MFA",
            "segredo TOTP ainda usa secret_reference local sem vault/provider externo",
        )

    def _next_tracks(self) -> tuple[str, ...]:
        return (
            "Owner MFA Admin Surface Review",
            "Owner Break-Glass Access Review",
            "Owner MFA Login Enforcement Review",
        )


owner_mfa_enrollment_closure_queries = OwnerMfaEnrollmentClosureQueryService()
