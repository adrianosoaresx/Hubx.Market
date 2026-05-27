from __future__ import annotations

from dataclasses import dataclass

from django.db import DatabaseError, transaction

from app.modules.accounts.application.admin_permissions import PERMISSION_OWNERS_MANAGE, admin_permissions
from app.modules.accounts.application.owner_mfa_secret_storage import REFERENCE_PREFIX, owner_mfa_secret_storage
from app.modules.accounts.models import OwnerMfaFactor
from app.modules.audit.application.audit_log_commands import audit_log_commands


def _string(value: object, *, limit: int = 180) -> str:
    return str(value or "").strip()[:limit]


@dataclass(frozen=True)
class OwnerMfaTotpSecretMigrationResult:
    result: str
    factor_id: int | None
    owner_id: int | None
    owner_email: str
    current_storage_mode: str
    target_reference: str
    dry_run: bool
    errors: dict[str, str]


@dataclass
class OwnerMfaTotpSecretMigrationCommandService:
    def migrate_factor(
        self,
        *,
        tenant_id: int | str | None,
        factor_id: int | str | None,
        reference_prefix: object = "owners",
        dry_run: bool = True,
        actor_label: object = "",
        actor_role: object = "",
    ) -> OwnerMfaTotpSecretMigrationResult:
        permission = admin_permissions.check(role=actor_role, permission=PERMISSION_OWNERS_MANAGE)
        if not permission.allowed:
            return self._result(
                result="owner-mfa-totp-secret-migration-permission-denied",
                dry_run=dry_run,
                errors={"__all__": "Permissão insuficiente para migrar segredo TOTP MFA."},
            )
        normalized_tenant_id = _string(tenant_id, limit=32)
        normalized_factor_id = _string(factor_id, limit=32)
        if not normalized_tenant_id:
            return self._result(result="owner-mfa-totp-secret-migration-tenant-required", dry_run=dry_run, errors={"tenant_id": "Tenant obrigatório."})
        if not normalized_factor_id:
            return self._result(result="owner-mfa-totp-secret-migration-factor-required", dry_run=dry_run, errors={"factor_id": "Fator obrigatório."})
        try:
            factor = (
                OwnerMfaFactor.objects.filter(
                    tenant_id=normalized_tenant_id,
                    id=normalized_factor_id,
                    factor_type=OwnerMfaFactor.FactorType.TOTP,
                    is_active=True,
                )
                .select_related("owner")
                .first()
            )
        except DatabaseError:
            return self._result(
                result="owner-mfa-totp-secret-migration-db-unavailable",
                dry_run=dry_run,
                errors={"__all__": "Banco indisponível para migrar segredo TOTP."},
            )
        if factor is None:
            return self._result(
                result="owner-mfa-totp-secret-migration-factor-not-found",
                dry_run=dry_run,
                errors={"factor_id": "Fator TOTP ativo não encontrado neste tenant."},
            )
        current_resolution = owner_mfa_secret_storage.resolve(factor.secret_reference)
        target_reference = self._target_reference(factor=factor, reference_prefix=reference_prefix)
        if current_resolution.storage_mode != "local-plain" or not current_resolution.ready:
            return self._result(
                result="owner-mfa-totp-secret-migration-not-local",
                factor=factor,
                current_storage_mode=current_resolution.storage_mode,
                target_reference=target_reference,
                dry_run=dry_run,
                errors={"secret_reference": "Somente segredo local/plain ativo pode ser migrado por este comando."},
            )
        target_resolution = owner_mfa_secret_storage.resolve(f"{REFERENCE_PREFIX}{target_reference}")
        if not target_resolution.ready:
            return self._result(
                result="owner-mfa-totp-secret-migration-target-unresolved",
                factor=factor,
                current_storage_mode=current_resolution.storage_mode,
                target_reference=target_reference,
                dry_run=dry_run,
                errors={"target_reference": "Referência externa alvo ainda não resolve no provider configurado."},
            )
        if target_resolution.secret != current_resolution.secret:
            return self._result(
                result="owner-mfa-totp-secret-migration-target-mismatch",
                factor=factor,
                current_storage_mode=current_resolution.storage_mode,
                target_reference=target_reference,
                dry_run=dry_run,
                errors={"target_reference": "Segredo externo alvo não confere com o segredo local atual."},
            )
        if dry_run:
            return self._result(
                result="owner-mfa-totp-secret-migration-dry-run",
                factor=factor,
                current_storage_mode=current_resolution.storage_mode,
                target_reference=target_reference,
                dry_run=True,
            )
        with transaction.atomic():
            factor.secret_reference = f"{REFERENCE_PREFIX}{target_reference}"
            factor.save(update_fields=("secret_reference", "updated_at"))
            self._record_migration_event(factor=factor, target_reference=target_reference, actor_label=_string(actor_label))
        return self._result(
            result="owner-mfa-totp-secret-migrated",
            factor=factor,
            current_storage_mode=current_resolution.storage_mode,
            target_reference=target_reference,
            dry_run=False,
        )

    def _target_reference(self, *, factor: OwnerMfaFactor, reference_prefix: object) -> str:
        normalized_prefix = _string(reference_prefix, limit=120).strip("/")
        if not normalized_prefix:
            normalized_prefix = "owners"
        return f"{normalized_prefix}/tenant-{factor.tenant_id}/owner-{factor.owner_id}/totp-{factor.id}"

    def _record_migration_event(self, *, factor: OwnerMfaFactor, target_reference: str, actor_label: str) -> None:
        audit_log_commands.record_event(
            tenant_id=factor.tenant_id,
            module="accounts",
            action="owner.mfa_totp_secret_migrated",
            entity_type="OwnerMfaFactor",
            entity_id=str(factor.id),
            actor_label=actor_label,
            summary=f"Segredo TOTP MFA migrado para referência externa para owner {factor.owner.email}.",
            metadata={
                "owner_id": factor.owner_id,
                "owner_email": factor.owner.email,
                "factor_type": factor.factor_type,
                "provider_key": factor.provider_key,
                "target_reference": target_reference,
                "storage_mode": "external-reference",
            },
        )

    def _result(
        self,
        *,
        result: str,
        factor: OwnerMfaFactor | None = None,
        current_storage_mode: str = "",
        target_reference: str = "",
        dry_run: bool,
        errors: dict[str, str] | None = None,
    ) -> OwnerMfaTotpSecretMigrationResult:
        return OwnerMfaTotpSecretMigrationResult(
            result=result,
            factor_id=factor.id if factor else None,
            owner_id=factor.owner_id if factor else None,
            owner_email=factor.owner.email if factor else "",
            current_storage_mode=current_storage_mode,
            target_reference=target_reference,
            dry_run=dry_run,
            errors=errors or {},
        )


owner_mfa_totp_secret_migration_commands = OwnerMfaTotpSecretMigrationCommandService()
