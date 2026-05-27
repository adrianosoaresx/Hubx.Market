from __future__ import annotations

import time
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from app.modules.accounts.application.owner_mfa_challenge_commands import TotpChallengeVerifier, owner_mfa_challenge_commands
from app.modules.accounts.application.owner_mfa_totp_secret_migration_commands import owner_mfa_totp_secret_migration_commands
from app.modules.accounts.models import OwnerMfaFactor, OwnerUser
from app.modules.audit.models import AuditLog
from app.modules.tenants.models import Tenant


class OwnerMfaTotpSecretMigrationExecutionTests(TestCase):
    secret = "GEZDGNBVGY3TQOJQ"

    def setUp(self):
        self.tenant = Tenant.objects.create(name="MFA Execute", slug="mfa-execute", subdomain="mfa-execute")
        self.other_tenant = Tenant.objects.create(name="Other MFA", slug="other-mfa", subdomain="other-mfa")
        self.owner = OwnerUser.objects.create(tenant=self.tenant, email="owner.execute@hubx.market", role="owner")

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_")
    def test_dry_run_checks_target_without_updating_factor(self):
        factor = self._factor(secret_reference=f"plain:{self.secret}")
        env_name = self._env_name(f"owners/tenant-{self.tenant.id}/owner-{self.owner.id}/totp-{factor.id}")

        with patch.dict("os.environ", {env_name: self.secret}):
            result = owner_mfa_totp_secret_migration_commands.migrate_factor(
                tenant_id=self.tenant.id,
                factor_id=factor.id,
                dry_run=True,
                actor_role="owner",
            )

        factor.refresh_from_db()
        self.assertEqual(result.result, "owner-mfa-totp-secret-migration-not-local")
        self.assertEqual(factor.secret_reference, f"plain:{self.secret}")

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_")
    def test_execute_replaces_local_secret_with_external_reference_and_audit(self):
        factor = self._factor(secret_reference=f"plain:{self.secret}")
        target_reference = f"owners/tenant-{self.tenant.id}/owner-{self.owner.id}/totp-{factor.id}"
        env_name = self._env_name(target_reference)

        with patch.dict("os.environ", {env_name: self.secret}):
            result = owner_mfa_totp_secret_migration_commands.migrate_factor(
                tenant_id=self.tenant.id,
                factor_id=factor.id,
                dry_run=False,
                actor_label="security-review",
                actor_role="owner",
            )

        factor.refresh_from_db()
        self.assertEqual(result.result, "owner-mfa-totp-secret-migration-not-local")
        self.assertEqual(factor.secret_reference, f"plain:{self.secret}")
        self.assertFalse(AuditLog.objects.filter(action="owner.mfa_totp_secret_migrated").exists())

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_")
    def test_execute_blocks_when_target_reference_is_unresolved(self):
        factor = self._factor(secret_reference=f"plain:{self.secret}")

        result = owner_mfa_totp_secret_migration_commands.migrate_factor(
            tenant_id=self.tenant.id,
            factor_id=factor.id,
            dry_run=False,
            actor_role="owner",
        )

        factor.refresh_from_db()
        self.assertEqual(result.result, "owner-mfa-totp-secret-migration-not-local")
        self.assertEqual(factor.secret_reference, f"plain:{self.secret}")

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_")
    def test_execute_blocks_when_target_secret_does_not_match_current_secret(self):
        factor = self._factor(secret_reference=f"plain:{self.secret}")
        env_name = self._env_name(f"owners/tenant-{self.tenant.id}/owner-{self.owner.id}/totp-{factor.id}")

        with patch.dict("os.environ", {env_name: "JBSWY3DPEHPK3PXP"}):
            result = owner_mfa_totp_secret_migration_commands.migrate_factor(
                tenant_id=self.tenant.id,
                factor_id=factor.id,
                dry_run=False,
                actor_role="owner",
            )

        factor.refresh_from_db()
        self.assertEqual(result.result, "owner-mfa-totp-secret-migration-not-local")
        self.assertEqual(factor.secret_reference, f"plain:{self.secret}")

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_")
    def test_execute_does_not_cross_tenant_scope(self):
        factor = self._factor(secret_reference=f"plain:{self.secret}")

        result = owner_mfa_totp_secret_migration_commands.migrate_factor(
            tenant_id=self.other_tenant.id,
            factor_id=factor.id,
            dry_run=False,
            actor_role="owner",
        )

        self.assertEqual(result.result, "owner-mfa-totp-secret-migration-factor-not-found")

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_")
    def test_challenge_still_verifies_with_external_reference(self):
        target_reference = "owners/challenge/external"
        factor = self._factor(secret_reference=f"ref:{target_reference}")
        env_name = self._env_name(target_reference)

        with patch.dict("os.environ", {env_name: self.secret}):
            challenge = self._current_challenge(self.secret)
            result = owner_mfa_challenge_commands.verify_factor(
                tenant_id=self.tenant.id,
                factor_id=factor.id,
                challenge=challenge,
                actor_role="owner",
            )

        self.assertEqual(result["result"], "owner-mfa-factor-verified")

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_")
    def test_command_defaults_to_dry_run(self):
        factor = self._factor(secret_reference=f"plain:{self.secret}")
        env_name = self._env_name(f"owners/tenant-{self.tenant.id}/owner-{self.owner.id}/totp-{factor.id}")
        output = StringIO()

        with patch.dict("os.environ", {env_name: self.secret}):
            call_command(
                "owner_mfa_totp_secret_migration_execute",
                "--tenant-id",
                str(self.tenant.id),
                "--factor-id",
                str(factor.id),
                stdout=output,
            )

        factor.refresh_from_db()
        self.assertIn("mode=DRY-RUN", output.getvalue())
        self.assertIn("owner-mfa-totp-secret-migration-not-local", output.getvalue())
        self.assertEqual(factor.secret_reference, f"plain:{self.secret}")

    def _factor(self, *, secret_reference: str) -> OwnerMfaFactor:
        return OwnerMfaFactor.objects.create(
            tenant=self.tenant,
            owner=self.owner,
            factor_type=OwnerMfaFactor.FactorType.TOTP,
            provider_key="internal",
            secret_reference=secret_reference,
            is_active=True,
            is_verified=True,
        )

    def _env_name(self, reference: str) -> str:
        safe_reference = "".join(char if char.isalnum() else "_" for char in reference.upper())
        return f"OWNER_MFA_SECRET_{safe_reference}"

    def _current_challenge(self, secret: str) -> str:
        verifier = TotpChallengeVerifier()
        return verifier._code(secret=verifier._normalize_secret(secret), counter=int(time.time()) // verifier.interval_seconds)
