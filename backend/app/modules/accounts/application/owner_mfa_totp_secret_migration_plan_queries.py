from __future__ import annotations

from dataclasses import dataclass

from django.db import DatabaseError

from app.modules.accounts.application.owner_mfa_secret_storage import owner_mfa_secret_storage
from app.modules.accounts.models import OwnerMfaFactor


@dataclass(frozen=True)
class OwnerMfaTotpSecretMigrationCandidate:
    factor_id: int
    owner_id: int
    owner_email: str
    current_storage_mode: str
    target_reference: str
    action: str
    blocker: str


@dataclass
class OwnerMfaTotpSecretMigrationPlanQueryService:
    def get_plan(self, *, tenant_id: int | str | None, reference_prefix: object = "owners") -> dict[str, object]:
        normalized_tenant_id = str(tenant_id or "").strip()
        normalized_prefix = self._reference_prefix(reference_prefix)
        if not normalized_tenant_id:
            return {
                "result": "owner-mfa-totp-secret-migration-tenant-required",
                "ready": False,
                "candidates": (),
                "blockers": ("tenant-required",),
                "runbook": (),
                "rollback": (),
            }
        try:
            factors = tuple(
                OwnerMfaFactor.objects.filter(
                    tenant_id=normalized_tenant_id,
                    factor_type=OwnerMfaFactor.FactorType.TOTP,
                    is_active=True,
                )
                .select_related("owner")
                .order_by("owner__email", "id")
            )
        except DatabaseError:
            return {
                "result": "owner-mfa-totp-secret-migration-db-unavailable",
                "ready": False,
                "candidates": (),
                "blockers": ("database-unavailable",),
                "runbook": ("rodar migrations de accounts antes do plano de migração",),
                "rollback": (),
            }
        candidates = tuple(self._candidate(factor=factor, reference_prefix=normalized_prefix) for factor in factors)
        blockers = tuple(candidate.blocker for candidate in candidates if candidate.blocker)
        migrate_count = sum(1 for candidate in candidates if candidate.action == "migrate-local-to-ref")
        already_external_count = sum(1 for candidate in candidates if candidate.action == "already-external")
        return {
            "result": "owner-mfa-totp-secret-migration-ready" if not blockers else "owner-mfa-totp-secret-migration-blocked",
            "ready": not blockers,
            "reference_prefix": normalized_prefix,
            "candidates": candidates,
            "migrate_count": migrate_count,
            "already_external_count": already_external_count,
            "missing_count": sum(1 for candidate in candidates if candidate.current_storage_mode == "missing"),
            "blockers": blockers,
            "runbook": (
                "1. exportar o segredo TOTP atual para o provider externo escolhido fora do app",
                "2. gravar o segredo no provider usando target_reference",
                "3. validar owner_mfa_secret_storage_readiness com OWNER_MFA_SECRET_PROVIDER configurado",
                "4. atualizar secret_reference para ref:<target_reference> em janela controlada",
                "5. testar login MFA do owner migrado",
                "6. só depois considerar OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=0",
            ),
            "rollback": (
                "restaurar secret_reference anterior plain:<secret> ou valor legado a partir do cofre de mudança",
                "manter OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=1 até validação completa",
            ),
        }

    def _candidate(self, *, factor: OwnerMfaFactor, reference_prefix: str) -> OwnerMfaTotpSecretMigrationCandidate:
        resolution = owner_mfa_secret_storage.resolve(factor.secret_reference)
        target_reference = f"{reference_prefix}/tenant-{factor.tenant_id}/owner-{factor.owner_id}/totp-{factor.id}"
        if resolution.storage_mode == "local-plain":
            return OwnerMfaTotpSecretMigrationCandidate(
                factor_id=factor.id,
                owner_id=factor.owner_id,
                owner_email=factor.owner.email,
                current_storage_mode=resolution.storage_mode,
                target_reference=target_reference,
                action="migrate-local-to-ref",
                blocker="",
            )
        if resolution.storage_mode == "unsupported-local":
            return OwnerMfaTotpSecretMigrationCandidate(
                factor_id=factor.id,
                owner_id=factor.owner_id,
                owner_email=factor.owner.email,
                current_storage_mode=resolution.storage_mode,
                target_reference=target_reference,
                action="blocked",
                blocker=f"factor-{factor.id}:local-secret-unsupported",
            )
        if resolution.storage_mode == "external-reference":
            return OwnerMfaTotpSecretMigrationCandidate(
                factor_id=factor.id,
                owner_id=factor.owner_id,
                owner_email=factor.owner.email,
                current_storage_mode=resolution.storage_mode,
                target_reference=resolution.reference,
                action="already-external",
                blocker="" if resolution.ready else f"factor-{factor.id}:external-secret-unresolved",
            )
        return OwnerMfaTotpSecretMigrationCandidate(
            factor_id=factor.id,
            owner_id=factor.owner_id,
            owner_email=factor.owner.email,
            current_storage_mode=resolution.storage_mode,
            target_reference=target_reference,
            action="blocked",
            blocker=f"factor-{factor.id}:secret-missing",
        )

    def _reference_prefix(self, reference_prefix: object) -> str:
        normalized = str(reference_prefix or "").strip().strip("/")
        return normalized or "owners"


owner_mfa_totp_secret_migration_plan_queries = OwnerMfaTotpSecretMigrationPlanQueryService()
